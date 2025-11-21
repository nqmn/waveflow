"""Edge-Center Beam Sweep Algorithm

Single-phase alternating sweep that tests angles in an edge-to-center pattern:
0°, ±60°, ±10°, ±50°, ±20°, ±40°, ±30°

This pattern probes the full field of view early while being efficient, testing
edges first then progressively filling in toward center. Finds optimal beam angle
with fewer measurements than exhaustive linear sweep.
"""
import numpy as np
from typing import Dict, List, Tuple
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    generate_codebook,
    setup_waveform_simulator,
    validate_and_get_nodes,
    clamp_to_ris_fov,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm


@register_algorithm(
    "edge",
    aliases=("edge-center", "directional-search", "exhaustive"),
)
class EdgeCenterSweep(SweepAlgorithmBase):
    """Edge-Center single-phase beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Edge-Center Sweep"

    @property
    def description(self) -> str:
        return "Single-phase alternating sweep: tests edges first, then progressively toward center. Efficient alternative to exhaustive linear search."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, early_stop_patience: int = 6, **kwargs) -> Dict:
        """Execute edge-center sweep with early termination

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Codebook step size in degrees (default: 10)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback (default: True)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)
            use_waveform: If True, simulate real signal-level SNR/SER (default: False)
            modulation: Modulation type: QPSK, 16QAM, or 64QAM (default: QPSK)
            num_symbols: Number of symbols per measurement (default: 1000)
            early_stop_patience: Stop after N consecutive measurements without SNR improvement (default: 6)

        Returns:
            Dictionary with sweep results
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

        # Base angle (incident direction)
        base_angle = ap_angle

        # Generate codebook
        codebook_local, num_codebook = generate_codebook(fov, step)

        # Clamp local deflection angles to RIS FOV constraint
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_codebook_local = clamp_local_deflection_to_ris_fov(codebook_local, ris_max_angle)

        # Convert deflection angles to absolute beam angles
        if angle_diff > 0:
            codebook_absolute = ap_angle + clamped_codebook_local
        else:
            codebook_absolute = ap_angle - clamped_codebook_local

        # Setup waveform simulator if requested
        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        snr_measurements = []
        ser_measurements = [] if use_waveform else None
        pwr_measurements = []
        angle_measurements = []  # Track which angle each measurement corresponds to
        best_snr_found = -np.inf
        best_measurement_idx = -1
        tested_indices = set()

        # Generate alternating edge-center test sequence
        # Pattern: 0, -60, 60, -10, 10, -50, 50, -20, 20, -40, 40, -30, 30
        test_sequence = [0]  # Start at center
        edge_offsets = []
        center_offsets = []

        for offset in range(int(step), int(fov) + int(step), int(step)):
            if offset == int(fov):
                edge_offsets.append(offset)
            else:
                center_offsets.append(offset)

        # Interleave: edge, center, edge, center, ...
        for i in range(max(len(edge_offsets), len(center_offsets))):
            if i < len(edge_offsets):
                test_sequence.append(-edge_offsets[i])
                test_sequence.append(edge_offsets[i])
            if i < len(center_offsets):
                test_sequence.append(-center_offsets[i])
                test_sequence.append(center_offsets[i])

        measurement_idx = 0
        no_improvement_count = 0
        for test_deflection in test_sequence:
            # Find closest angle in codebook to this deflection
            diffs = np.abs(clamped_codebook_local - test_deflection)
            codebook_idx = int(np.argmin(diffs))

            if codebook_idx in tested_indices:
                continue

            tested_indices.add(codebook_idx)
            test_angle = codebook_absolute[codebook_idx]
            local_angle = clamped_codebook_local[codebook_idx]

            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=test_angle,
                    seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,
                    use_get_snr=self._should_use_get_snr()
                )

            current_snr, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=seed + measurement_idx if seed else None,
            )
            current_pwr = res['pwr_dBm']
            snr_measurements.append(current_snr)
            pwr_measurements.append(current_pwr)
            angle_measurements.append(float(local_angle))

            # Track the best result found so far
            if metric_selector is None:
                # Default: use SNR
                if current_snr > best_snr_found:
                    best_snr_found = current_snr
                    best_measurement_idx = measurement_idx
                    no_improvement_count = 0  # Reset counter on improvement
                else:
                    no_improvement_count += 1
                    # Early stop if no improvement for patience iterations
                    if no_improvement_count >= early_stop_patience and measurement_idx > 3:
                        break

            if ser_measurements is not None:
                ser_measurements.append(ser_val)

            measurement_idx += 1

        # Apply metric selector if provided
        if metric_selector is not None:
            best_measurement_idx = metric_selector.find_best_index(snr_measurements)
            best_snr_found = snr_measurements[best_measurement_idx]

        # Get best angle and values from the measurement
        best_angle = angle_measurements[best_measurement_idx]
        best_power = pwr_measurements[best_measurement_idx]

        result = {
            'angles': angle_measurements,
            'snr': snr_measurements,
            'power': pwr_measurements,
            'best_angle': float(best_angle),
            'best_snr': float(best_snr_found),
            'best_power': float(best_power),
            'base_angle': float(base_angle),
            'num_angles_tested': len(tested_indices),
            # Keep legacy keys for backward compatibility
            'local_coarse': angle_measurements,
            'snr_coarse': snr_measurements,
            'pwr_coarse': pwr_measurements,
            'local_fine': [],
            'snr_fine': [],
            'best_local_fine': float(best_angle),
            'best_snr_fine': float(best_snr_found)
        }

        # Add SER values if waveform simulation was used
        if use_waveform and ser_measurements:
            result['ser_coarse'] = ser_measurements
            result['ser_fine'] = []

        return result
