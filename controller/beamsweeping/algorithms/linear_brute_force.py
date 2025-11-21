"""Linear Brute-Force Beam Sweep Algorithm

Tests all beam angles across the field of view in equal steps.
Single-phase exhaustive search - simple and straightforward.
Uses specular reflection reference angle for physically correct RIS beam steering.

This is the simplest sweep algorithm: test all angles at specified resolution,
find the best. No two-phase complexity needed for exhaustive search.
"""

import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    generate_codebook,
    local_angle_to_index,
    setup_waveform_simulator,
    validate_and_get_nodes,
    FeedbackCollector,
    clamp_to_ris_fov,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm


@register_algorithm("linear", aliases=("brute-force",))
class LinearBruteForceSweep(SweepAlgorithmBase):
    """Linear brute-force beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Linear Brute-Force Sweep"

    @property
    def description(self) -> str:
        return "Simple exhaustive search: tests all beam angles across FOV at specified resolution."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, **kwargs) -> Dict:
        """Execute linear brute-force sweep with optional closed-loop feedback

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Angle step size in degrees (default: 1)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback for each angle (default: False)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)

        Returns:
            Dictionary with sweep results:
                - angles: Local angles tested
                - snr: SNR values for each angle
                - power: Power values for each angle
                - best_angle: Best local angle
                - best_snr: Best SNR in dB
                - best_power: Power at best angle
                - specular_angle: Reference specular angle
                - num_angles_tested: Total angles tested
                - feedback_enabled: Whether feedback was used
                - feedback_details: List of feedback iteration results (if enabled)
        """
        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Calculate incident and reflected azimuths from 3D coordinates
        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        ue_vec = ue.pos - ris.pos
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Deflection angle is the magnitude of azimuth difference
        angle_diff = ue_angle - ap_angle
        # Wrap to [-180, 180]
        while angle_diff > 180:
            angle_diff -= 360
        while angle_diff < -180:
            angle_diff += 360

        # Base deflection angle magnitude
        base_deflection_angle = abs(angle_diff)

        # Also set base_angle for compatibility (incident direction)
        base_angle = ap_angle

        # CRITICAL FIX: Calculate optimal RIS normal ONCE for sweep consistency
        # This ensures all beam angle measurements use the same RIS normal reference
        from core.angle_utils import compute_optimal_ris_normal
        fixed_ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)

        # Generate GEOMETRIC DEFLECTION angles to test (the codebook)
        # These are the deflection magnitudes between incident and reflected rays
        angles, num_angles = generate_codebook(fov, step)

        # Clamp deflection angles to RIS FOV constraint
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_angles = clamp_local_deflection_to_ris_fov(angles, ris_max_angle)

        # Convert GEOMETRIC DEFLECTION angles to absolute beam angles
        # The codebook contains deflection angles from the incident direction (AP).
        # For deflection θ:
        #   - θ < 0: beam deflects clockwise from incident direction
        #   - θ > 0: beam deflects counter-clockwise from incident direction
        #   - Absolute beam angle = incident_angle + θ
        #
        # This ensures codebook angle directly represents the deflection magnitude.
        # For example, 44.92° deflection → codebook ≈ ±45° (rounded to step size)
        abs_angles = ap_angle + clamped_angles  # Add deflection to incident direction

        snr_values = [None] * num_angles
        power_values = [None] * num_angles
        ser_values = [None] * num_angles if use_waveform else None
        feedback_collector = FeedbackCollector(enable_feedback)

        # Setup waveform simulator if requested
        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols)

        def measure_index(idx: int):
            if snr_values[idx] is not None:
                return
            abs_a = abs_angles[idx]
            tapering = kwargs.get('tapering', 'uniform')
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_a, seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,  # Don't store intermediate measurements
                    use_get_snr=self._should_use_get_snr(),  # Use get_snr() if enabled
                    tapering=tapering,
                    fixed_ris_normal=fixed_ris_normal  # Critical: use same RIS normal for all measurements
                )

            snr_val, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=seed + idx if seed else None,
            )
            snr_values[idx] = snr_val
            if ser_values is not None:
                ser_values[idx] = ser_val

            power_values[idx] = res['pwr_dBm']

            if enable_feedback and 'feedback_info' in res:
                feedback_collector.add(float(abs_a), float(angles[idx]), res['feedback_info'])

        # Measure ML-suggested angles first (if provided)
        if ml_angles:
            for suggested in ml_angles:
                idx = local_angle_to_index(float(suggested), fov, step, num_angles)
                measure_index(idx)

        # Test each angle
        for idx in range(len(angles)):
            measure_index(idx)

        # Find best angle using SNR
        # NOTE: metric_selector is no longer passed to sweep algorithms
        # Post-processing in connection_handler will override using correct metric
        # (after CSI/RSSI values are computed)
        best_idx = int(np.argmax(snr_values))

        best_angle = angles[best_idx]
        best_snr = snr_values[best_idx]
        best_power = power_values[best_idx]

        result = {
            'angles': angles.tolist(),
            'snr': np.array(snr_values).tolist(),
            'power': np.array(power_values).tolist(),
            'best_angle': float(best_angle),
            'best_snr': float(best_snr),
            'best_power': float(best_power),
            'base_angle': float(base_angle),
            'num_angles_tested': num_angles,
            'feedback_enabled': enable_feedback,
            'feedback_details': feedback_collector.get_details(),
            # Keep legacy keys for backward compatibility with adaptive algorithm output
            'local_coarse': angles.tolist(),
            'snr_coarse': np.array(snr_values).tolist(),
            'pwr_coarse': np.array(power_values).tolist(),
            'local_fine': [],
            'snr_fine': [],
            'best_local_fine': float(best_angle),
            'best_snr_fine': float(best_snr)
        }

        # Add SER values if waveform simulation was used
        if use_waveform and ser_values:
            result['ser_coarse'] = ser_values
            result['ser_fine'] = []

        return result
