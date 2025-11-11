"""[TEMPLATE] Standard Beam Sweep Algorithm Implementation

INSTRUCTIONS:
1. Copy this file to `controller/beamsweeping/algorithms/my_algorithm.py`
2. Replace all [TEMPLATE] markers with your implementation
3. Update class name and algorithm name
4. Implement Phase 1 and Phase 2 sweep logic
5. Decorate your class with @register_algorithm("my-algo", aliases=(...))
6. Test using: sweep AP1 R1 UE1 60 10 --algo my-algo

ALGORITHM DESCRIPTION:
[TEMPLATE: Describe your algorithm here]
- Phase 1: [Describe coarse search strategy]
- Phase 2: [Describe fine refinement strategy]
- Efficiency: [Estimate measurement savings vs exhaustive]
"""

import numpy as np
from typing import Dict
from .base import SweepAlgorithmBase  # When moved under algorithms/, change to `from ..base import ...`


class [TEMPLATE_CLASS_NAME](SweepAlgorithmBase):
    """[TEMPLATE: Descriptive class docstring]"""

    @property
    def name(self) -> str:
        """Return algorithm name (displayed to users)

        Returns:
            str: Human-readable algorithm name
        """
        return "[TEMPLATE: Algorithm Display Name]"

    @property
    def description(self) -> str:
        """Return algorithm description (displayed to users)

        Returns:
            str: Brief description of algorithm and its benefits
        """
        return "[TEMPLATE: Brief description of how the algorithm works]"

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42, ml_angles=None) -> Dict:
        """Execute beam sweep

        This method implements the core sweep algorithm in two phases:
        - Phase 1: Coarse search across FOV
        - Phase 2: Fine refinement around best angle

        Args:
            ap_name (str): Access Point name (must exist in network)
            ris_name (str): RIS node name (must exist in network)
            ue_name (str): User Equipment name (must exist in network)
            fov (float): Field of view in degrees (default: 60)
                Range: typically 30-120 degrees
            step (float): Coarse step size in degrees (default: 10)
                Smaller = more measurements, better accuracy
            fine_span (float): Fine search span around best coarse angle (default: 10)
                Typical: 5-15 degrees around best coarse angle
            fine_res (float): Fine resolution in degrees (default: 1)
                Smaller = more measurements, higher resolution
            seed (int): Random seed for reproducibility (default: 42)
                Use in self.network.connect() calls

        Returns:
            Dict: Dictionary with sweep results. REQUIRED keys:
                local_coarse (list): Local angles tested in coarse phase [degrees]
                snr_coarse (list): SNR values for coarse angles [dB]
                pwr_coarse (list): Power values for coarse angles [dBm]
                local_fine (list): Local angles tested in fine phase [degrees]
                snr_fine (list): SNR values for fine angles [dB]
                best_local_fine (float): Best angle found (local/relative) [degrees]
                best_snr_fine (float): Best SNR found [dB]

                Optional keys:
                specular_angle (float): Reference angle used [degrees]
                algorithm_metadata (dict): Algorithm-specific data
                measurement_count (int): Total measurements performed
                efficiency_ratio (float): Measurement efficiency

        Raises:
            ValueError: If any node name is invalid
        """

        # SECTION 1: INPUT VALIDATION
        # =============================
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError(
                f"Invalid node names: AP={ap_name}, RIS={ris_name}, UE={ue_name}"
            )

        # SECTION 2: REFERENCE ANGLE CALCULATION
        # ========================================
        # [TEMPLATE: Calculate reference angle for your algorithm]
        # Common approaches:
        # - Geometric direction from RIS to UE
        # - Specular reflection angle (AP-RIS-UE)
        # - Midpoint angle between multiple candidates

        vec = ue.pos - ris.pos
        base_dir = np.degrees(np.arctan2(vec[1], vec[0]))

        # SECTION 3: PHASE 1 - COARSE SEARCH
        # ===================================
        # [TEMPLATE: Implement coarse search strategy]
        # This phase should:
        # 1. Generate angles to test (local_coarse)
        # 2. Test each angle using self.network.connect()
        # 3. Collect SNR and power measurements
        # 4. Find best angle
        #
        # Example implementation:
        # - Linear sweep: test all angles in FOV with step size
        # - Adaptive: test center-out, stop when SNR declines
        # - Random: randomly sample subset of angles
        # - Quadrant: test quadrants, then best one

        # Generate coarse angles (relative to base_dir)
        local_coarse = np.arange(-fov, fov + 1, step)

        # Convert to absolute angles
        abs_angles = base_dir + local_coarse

        # Test each angle
        snr_coarse = []
        pwr_coarse = []

        for abs_a in abs_angles:
            res = self.network.connect(
                ap_name, ris_name, ue_name,
                beam_angle_deg=abs_a,
                seed=seed
            )
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        # Find best coarse angle
        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # SECTION 4: PHASE 2 - FINE REFINEMENT
        # =====================================
        # [TEMPLATE: Implement fine refinement strategy]
        # This phase should:
        # 1. Generate finer angles around best coarse angle
        # 2. Test each angle
        # 3. Find best angle with higher resolution
        #
        # Example implementation:
        # - Linear refinement: uniform fine steps
        # - Adaptive refinement: variable resolution
        # - Multi-scale: multiple refinement iterations
        # - Directional: higher resolution in likely direction

        # Generate fine angles around best coarse angle
        local_fine = np.arange(
            best_local - fine_span,
            best_local + fine_span + fine_res,
            fine_res
        )

        # Convert to absolute angles
        abs_angles_fine = base_dir + local_fine

        # Test each fine angle
        snr_fine = []

        for abs_a in abs_angles_fine:
            r = self.network.connect(
                ap_name, ris_name, ue_name,
                beam_angle_deg=abs_a,
                seed=seed
            )
            snr_fine.append(r['snr_dB'])

        # Find best fine angle
        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        # SECTION 5: RESULT PREPARATION
        # ==============================
        # [TEMPLATE: Add optional metadata if needed]
        # Consider including:
        # - Algorithm-specific metrics
        # - Intermediate results
        # - Performance statistics
        # - Convergence information

        return {
            # REQUIRED KEYS - DO NOT MODIFY
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': np.array(snr_coarse).tolist(),
            'pwr_coarse': np.array(pwr_coarse).tolist(),
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),

            # OPTIONAL KEYS - Add as needed
            # 'specular_angle': float(base_dir),
            # 'measurement_count': len(local_coarse) + len(local_fine),
            # 'efficiency_ratio': 1.0,  # measurements / total possible
            # 'algorithm_metadata': {...}
        }


# SECTION 6: REGISTRATION INSTRUCTIONS
# =====================================
# To use this algorithm, add to controller/beamsweeping/__init__.py:
#
# from .template_algorithm import [TEMPLATE_CLASS_NAME]
#
# class SweepAlgorithmLoader:
#     ALGORITHMS = {
#         'linear': LinearBruteForceSweep,
#         'adaptive': AdaptiveCenterOutSweep,
#         '[TEMPLATE_ALIAS]': [TEMPLATE_CLASS_NAME],  # ADD THIS LINE
#     }
#
# Then use: sweep AP1 R1 UE1 60 10 --algo [TEMPLATE_ALIAS]


# SECTION 7: TESTING TEMPLATE
# =============================
# Uncomment and run to test your algorithm:
#
# if __name__ == '__main__':
#     from core import RISNetwork
#
#     net = RISNetwork()
#     net.add_ap('AP1', 0, 0, 0)
#     net.add_ris('R1', 5, 5, 0, N=16, bits=2)
#     net.add_ue('UE1', 10, 10, 0)
#
#     algo = [TEMPLATE_CLASS_NAME](net)
#     print(f"Algorithm: {algo.name}")
#     print(f"Description: {algo.description}")
#
#     result = algo.sweep('AP1', 'R1', 'UE1', fov=60, step=10)
#
#     print(f"\nResults:")
#     print(f"  Best SNR: {result['best_snr_fine']:.2f} dB")
#     print(f"  Best angle: {result['best_local_fine']:.2f}°")
#     print(f"  Coarse angles tested: {len(result['local_coarse'])}")
#     print(f"  Fine angles tested: {len(result['local_fine'])}")
#     print(f"  Total: {len(result['local_coarse']) + len(result['local_fine'])} angles")
