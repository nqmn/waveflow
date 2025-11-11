"""Shared helpers for beam sweep algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:  # Centralize waveform availability handling
    from core.signal_processor import (
        SignalConfig,
        SignalLevelLink,
        apply_signal_level_realism,
    )

    WAVEFORM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    SignalConfig = SignalLevelLink = apply_signal_level_realism = None  # type: ignore
    WAVEFORM_AVAILABLE = False

# Import standardized angle utilities
try:
    from core.angle_utils import (
        normalize_angle_to_pm180,
        compute_offset_from_normal,
        is_within_fov,
        clamp_offset_to_fov,
        compute_absolute_angle_from_offset,
        compute_optimal_ris_normal
    )
except ImportError:
    # Fallback: define locally if core module not available
    def normalize_angle_to_pm180(angle: float) -> float:
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle

    def compute_offset_from_normal(target_angle: float, normal_angle: float) -> float:
        offset = target_angle - normal_angle
        return normalize_angle_to_pm180(offset)

    def is_within_fov(offset_angle: float, max_angle: float, tolerance_deg: float = 0.01) -> bool:
        return abs(offset_angle) <= (max_angle + tolerance_deg)

    def clamp_offset_to_fov(offset_angle: float, max_angle: float) -> float:
        return float(np.clip(offset_angle, -max_angle, max_angle))

    def compute_absolute_angle_from_offset(normal_angle: float, offset_angle: float) -> float:
        absolute = normal_angle + offset_angle
        while absolute < 0:
            absolute += 360
        while absolute >= 360:
            absolute -= 360
        return absolute


@dataclass(frozen=True)
class WaveformSettings:
    """Configuration for optional waveform realism."""

    modulation: str = "QPSK"
    symbol_rate: float = 1e6
    sample_rate: float = 10e6
    num_symbols: int = 1000
    pilot_ratio: Optional[float] = None


def normalize_angle_to_pm180(angle: float) -> float:
    """Normalize angle to [-180, 180] range.

    Args:
        angle: Angle in degrees (any range)

    Returns:
        Normalized angle in [-180, 180] degrees
    """
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def compute_offset_from_normal(target_angle: float, normal_angle: float) -> float:
    """Compute offset angle relative to a normal direction.

    This computes the signed offset from a normal direction (boresight) to a target
    direction, properly normalized to [-180, 180] range.

    Args:
        target_angle: Target direction in absolute degrees [0, 360)
        normal_angle: Reference/normal direction in absolute degrees [0, 360)

    Returns:
        Offset angle in [-180, 180] degrees
        Positive = clockwise from normal (increasing angle)
        Negative = counter-clockwise from normal (decreasing angle)
    """
    offset = target_angle - normal_angle
    return normalize_angle_to_pm180(offset)


def is_within_fov(offset_angle: float, max_angle: float, tolerance_deg: float = 0.01) -> bool:
    """Check if an offset angle is within field of view limits.

    Args:
        offset_angle: Angle offset from normal, in [-180, 180] range
        max_angle: Maximum FOV half-angle (±max_angle_deg)
        tolerance_deg: Numerical tolerance (default 0.01°)

    Returns:
        True if |offset_angle| <= max_angle (within tolerance)
    """
    return abs(offset_angle) <= (max_angle + tolerance_deg)


def clamp_offset_to_fov(offset_angle: float, max_angle: float) -> float:
    """Clamp an offset angle to stay within FOV limits.

    Args:
        offset_angle: Offset angle in degrees (any range, but typically [-180, 180])
        max_angle: Maximum FOV half-angle (±max_angle_deg)

    Returns:
        Clamped offset angle in [-max_angle, +max_angle] range
    """
    return float(np.clip(offset_angle, -max_angle, max_angle))


def compute_absolute_angle_from_offset(normal_angle: float, offset_angle: float) -> float:
    """Compute absolute angle from normal and offset.

    Args:
        normal_angle: Normal/boresight direction in degrees
        offset_angle: Offset from normal in degrees

    Returns:
        Absolute angle in [0, 360) range
    """
    absolute = normal_angle + offset_angle
    # Normalize to [0, 360)
    while absolute < 0:
        absolute += 360
    while absolute >= 360:
        absolute -= 360
    return absolute


def compute_specular_angle(ris, ue) -> float:
    """Return the specular UE direction relative to the RIS.

    DEPRECATED: For new sweep algorithms, use compute_ris_normal_for_sweep() instead.
    This function returns only the UE direction and doesn't account for AP direction,
    which can result in AP being outside RIS FOV in some geometries.
    """
    ue_vec = ue.pos - ris.pos
    return float(np.degrees(np.arctan2(ue_vec[1], ue_vec[0])))


def compute_ris_normal_for_sweep(ap, ris, ue) -> float:
    """Compute optimal RIS normal for beam sweep that serves both AP and UE.

    For a cascaded AP→RIS→UE link, the RIS must simultaneously:
    - Receive signals from AP
    - Transmit signals toward UE

    With a phased array RIS having limited FOV (typically ±60°), the optimal
    RIS normal is the bisector between AP and UE directions. This minimizes the
    maximum offset angle to either AP or UE, ensuring both stay within FOV.

    This function ensures all sweep algorithms use the same RIS normal calculation
    as the single connect command, providing consistent angle measurements.

    Args:
        ap: Access Point node
        ris: RIS node
        ue: User Equipment node

    Returns:
        Optimal RIS normal angle in degrees [0, 360)

    Example:
        >>> ris_normal = compute_ris_normal_for_sweep(ap, ris, ue)
        >>> # Returns: 157.54° (bisector between AP and UE)
        >>> # AP offset: 22.46° ✓ (within ±60° FOV)
        >>> # UE offset: -22.46° ✓ (within ±60° FOV)
    """
    # Compute angles from RIS perspective
    ap_vec = ap.pos - ris.pos
    ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

    ue_vec = ue.pos - ris.pos
    ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

    # Use global helper to compute bisector (optimal RIS normal)
    # This ensures consistency with single connect command
    return compute_optimal_ris_normal(ap_angle, ue_angle)


def clamp_to_ris_fov(angles: np.ndarray, ris_max_angle: float) -> np.ndarray:
    """Clamp absolute beam angles to RIS field of view constraint.

    Args:
        angles: Array of absolute beam angles in degrees
        ris_max_angle: RIS maximum steering angle (±max_angle_deg)

    Returns:
        Clamped angles array where each angle is within [-ris_max_angle, +ris_max_angle]
    """
    return np.clip(angles, -ris_max_angle, ris_max_angle)


def clamp_local_deflection_to_ris_fov(
    local_deflections: np.ndarray, ris_max_angle: float
) -> np.ndarray:
    """Clamp local beam deflections to RIS field of view constraint.

    Clamps the local deflection angle (relative to RIS normal) to stay within
    the RIS maximum steering angle, ensuring the beam stays within the RIS FOV.

    Args:
        local_deflections: Array of local deflection angles in degrees
                          (relative to RIS normal)
        ris_max_angle: RIS maximum steering angle (±max_angle_deg)

    Returns:
        Clamped local deflections array where each deflection is within
        [-ris_max_angle, +ris_max_angle]

    Example:
        If RIS normal is 170° and max_angle is 60°, then valid beam angles
        are [110°, 230°]. A local deflection of -80° would be clamped to -60°,
        resulting in a final beam angle of 170° - 60° = 110°.
    """
    return np.clip(local_deflections, -ris_max_angle, ris_max_angle)


def create_waveform_link(
    enable_waveform: bool, settings: WaveformSettings
) -> Optional["SignalLevelLink"]:
    """Create a waveform simulator instance when the dependency is available."""
    if not enable_waveform or not WAVEFORM_AVAILABLE:
        return None

    config_kwargs = {
        "modulation": settings.modulation,
        "symbol_rate": settings.symbol_rate,
        "sample_rate": settings.sample_rate,
        "num_symbols": settings.num_symbols,
    }
    if settings.pilot_ratio is not None:
        config_kwargs["pilot_ratio"] = settings.pilot_ratio

    return SignalLevelLink(SignalConfig(**config_kwargs))


def apply_waveform_realism(
    measurement: Dict,
    link_simulator: Optional["SignalLevelLink"],
    *,
    seed: Optional[int] = None,
) -> Tuple[float, Optional[float]]:
    """Convert physics-level measurement into signal-level SNR/SER."""
    if not link_simulator or not apply_signal_level_realism:
        return float(measurement["snr_dB"]), None

    signal_result = apply_signal_level_realism(
        measurement,
        link_simulator,
        seed=seed,
    )
    return float(signal_result["snr_dB"]), signal_result.get("ser_percent")


def validate_and_get_nodes(network, ap_name: str, ris_name: str, ue_name: str) -> Tuple[Any, Any, Any]:
    """Validate and retrieve nodes from network.

    Args:
        network: RISNetwork object
        ap_name: Access Point name
        ris_name: RIS name
        ue_name: User Equipment name

    Returns:
        Tuple of (ap, ris, ue) nodes

    Raises:
        ValueError: If any node is invalid
    """
    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    if ap is None or ris is None or ue is None:
        raise ValueError("Invalid node name in sweep")

    return ap, ris, ue


def local_angle_to_index(local_angle: float, fov: float, step: float, num_angles: int) -> int:
    """Convert local angle to array index.

    Args:
        local_angle: Local angle in degrees
        fov: Field of view in degrees
        step: Step size in degrees
        num_angles: Total number of angles in the array

    Returns:
        Index in the angle array (clamped to valid range)
    """
    clamped = max(-fov, min(fov, local_angle))
    rel = (clamped + fov) / step
    idx = int(round(rel))
    idx = max(0, min(num_angles - 1, idx))
    return idx


def generate_codebook(fov: float, step: float) -> Tuple[np.ndarray, int]:
    """Generate angle codebook from -FOV to +FOV.

    Args:
        fov: Field of view in degrees (±fov)
        step: Step size in degrees

    Returns:
        Tuple of (local_angles, num_angles) where local_angles is array from -fov to +fov
    """
    local_angles = np.arange(-fov, fov + step, step)
    return local_angles, len(local_angles)


def setup_waveform_simulator(
    use_waveform: bool,
    modulation: str = "QPSK",
    num_symbols: int = 1000,
    pilot_ratio: Optional[float] = None,
) -> Optional["SignalLevelLink"]:
    """Setup waveform simulator with standard settings.

    Args:
        use_waveform: Enable waveform simulation
        modulation: Modulation type (QPSK, 16QAM, 64QAM)
        num_symbols: Number of symbols to simulate
        pilot_ratio: Optional pilot ratio for signal config

    Returns:
        SignalLevelLink instance or None if disabled
    """
    waveform_settings = WaveformSettings(
        modulation=modulation,
        num_symbols=num_symbols,
        pilot_ratio=pilot_ratio,
    )
    return create_waveform_link(use_waveform, waveform_settings)


class FeedbackCollector:
    """Helper class to collect feedback details during measurements."""

    def __init__(self, enable_feedback: bool):
        """Initialize feedback collector.

        Args:
            enable_feedback: Whether to collect feedback details
        """
        self.enabled = enable_feedback
        self.details = [] if enable_feedback else None

    def add(self, angle: float, local_angle: float, feedback_info: Dict, phase: str = "coarse") -> None:
        """Add a feedback measurement.

        Args:
            angle: Absolute angle (degrees)
            local_angle: Local angle relative to specular (degrees)
            feedback_info: Feedback dictionary from network.connect()
            phase: Phase name (e.g., "coarse", "fine")
        """
        if self.enabled and self.details is not None:
            self.details.append({
                'angle': float(angle),
                'local_angle': float(local_angle),
                'phase': phase,
                'feedback_info': feedback_info
            })

    def get_details(self) -> Optional[List[Dict]]:
        """Get collected feedback details or None if not enabled."""
        return self.details
