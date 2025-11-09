"""Linear Brute-Force Beam Sweep Algorithm

Tests all beam angles across the field of view in equal steps.
Uses specular reflection reference angle (same as adaptive) for physically
correct RIS beam steering. Differs from adaptive only in search strategy
(linear vs. center-out), not in reference frame.

Note: Adaptive algorithm is the reference implementation for RIS physics.
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
        return "Tests all beam angles across FOV in equal steps. Two-phase: coarse + fine refinement."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42) -> Dict:
        """Execute linear brute-force sweep

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Coarse step size in degrees (default: 10)
            fine_span: Fine search span around best coarse angle (default: 10)
            fine_res: Fine resolution in degrees (default: 1)
            seed: Random seed for reproducibility

        Returns:
            Dictionary with sweep results:
                - local_coarse: Local angles tested in coarse phase
                - snr_coarse: SNR values for coarse angles
                - pwr_coarse: Power values for coarse angles
                - local_fine: Local angles tested in fine phase
                - snr_fine: SNR values for fine angles
                - best_local_fine: Best local angle
                - best_snr_fine: Best SNR in dB
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # Calculate specular reflection angle (same as adaptive for consistent reference)
        incident_vec = ap.pos - ris.pos
        incident_angle = np.degrees(np.arctan2(incident_vec[1], incident_vec[0]))

        # Specular reflection: mirror the incident ray
        reflected_vec = -incident_vec
        specular_angle = np.degrees(np.arctan2(reflected_vec[1], reflected_vec[0]))

        # Phase 1: Coarse sweep
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = specular_angle + local_coarse

        snr_coarse = []
        pwr_coarse = []

        # Test each coarse angle
        for abs_a in abs_angles:
            res = self.network.connect(ap_name, ris_name, ue_name,
                                      beam_angle_deg=abs_a, seed=seed)
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        # Find best coarse angle
        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # Phase 2: Fine sweep around best coarse angle (constrained within original FOV)
        fine_start = max(best_local - fine_span, -fov)
        fine_end = min(best_local + fine_span, fov)
        local_fine = np.arange(fine_start, fine_end + fine_res, fine_res)
        abs_angles_fine = specular_angle + local_fine
        snr_fine = []

        for abs_a in abs_angles_fine:
            r = self.network.connect(ap_name, ris_name, ue_name,
                                    beam_angle_deg=abs_a, seed=seed)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        return {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': np.array(snr_coarse).tolist(),
            'pwr_coarse': np.array(pwr_coarse).tolist(),
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
            'specular_angle': float(specular_angle)
        }
