"""Linear Brute-Force Beam Sweep Algorithm

Tests all beam angles across the field of view in equal steps.
Single-phase exhaustive search - simple and straightforward.
Uses specular reflection reference angle for physically correct RIS beam steering.

This is the simplest sweep algorithm: test all angles at specified resolution,
find the best. No two-phase complexity needed for exhaustive search.
"""

import numpy as np
from typing import Dict
from .base import SweepAlgorithmBase


class LinearBruteForceSweep(SweepAlgorithmBase):
    """Linear brute-force beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Linear Brute-Force Sweep"

    @property
    def description(self) -> str:
        return "Simple exhaustive search: tests all beam angles across FOV at specified resolution."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 1.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3) -> Dict:
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
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # Calculate specular reflection angle
        incident_vec = ap.pos - ris.pos
        reflected_vec = -incident_vec
        specular_angle = np.degrees(np.arctan2(reflected_vec[1], reflected_vec[0]))

        # Single phase: test all angles from -FOV to +FOV at specified resolution
        angles = np.arange(-fov, fov + step, step)
        abs_angles = specular_angle + angles

        snr_values = []
        power_values = []
        feedback_details = [] if enable_feedback else None

        # Test each angle
        for i, abs_a in enumerate(abs_angles):
            res = self.network.connect(ap_name, ris_name, ue_name,
                                      beam_angle_deg=abs_a, seed=seed,
                                      enable_feedback=enable_feedback,
                                      max_feedback_iterations=max_feedback_iterations)
            snr_values.append(res['snr_dB'])
            power_values.append(res['pwr_dBm'])

            # Store feedback details if enabled
            if enable_feedback and 'feedback_info' in res:
                feedback_details.append({
                    'angle': float(abs_a),
                    'local_angle': float(angles[i]),
                    'feedback_info': res['feedback_info']
                })

        # Find best angle
        best_idx = int(np.argmax(snr_values))
        best_angle = angles[best_idx]
        best_snr = snr_values[best_idx]
        best_power = power_values[best_idx]

        return {
            'angles': angles.tolist(),
            'snr': np.array(snr_values).tolist(),
            'power': np.array(power_values).tolist(),
            'best_angle': float(best_angle),
            'best_snr': float(best_snr),
            'best_power': float(best_power),
            'specular_angle': float(specular_angle),
            'num_angles_tested': len(angles),
            'feedback_enabled': enable_feedback,
            'feedback_details': feedback_details,
            # Keep legacy keys for backward compatibility with adaptive algorithm output
            'local_coarse': angles.tolist(),
            'snr_coarse': np.array(snr_values).tolist(),
            'pwr_coarse': np.array(power_values).tolist(),
            'local_fine': [],
            'snr_fine': [],
            'best_local_fine': float(best_angle),
            'best_snr_fine': float(best_snr)
        }
