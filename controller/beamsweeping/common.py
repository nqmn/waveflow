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


@dataclass(frozen=True)
class WaveformSettings:
    """Configuration for optional waveform realism."""

    modulation: str = "QPSK"
    symbol_rate: float = 1e6
    sample_rate: float = 10e6
    num_symbols: int = 1000
    pilot_ratio: Optional[float] = None


def compute_specular_angle(ris, ue) -> float:
    """Return the specular UE direction relative to the RIS."""
    ue_vec = ue.pos - ris.pos
    return float(np.degrees(np.arctan2(ue_vec[1], ue_vec[0])))


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
