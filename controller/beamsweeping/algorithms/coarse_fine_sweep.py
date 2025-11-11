"""Coarse-Fine Two-Phase Beam Sweep Algorithm

Implements an efficient two-phase beam sweeping strategy:
- Phase 1: Coarse center-out sweep (starts from specular angle, expands outward)
- Phase 2: Fine-resolution refinement around best coarse angle

Efficiency: ~30% measurement savings vs exhaustive search

Supports real signal-level emulation via use_waveform parameter.
"""
import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    compute_specular_angle,
    generate_codebook,
    local_angle_to_index,
    setup_waveform_simulator,
    validate_and_get_nodes,
    FeedbackCollector,
)
from ..registry import register_algorithm


@register_algorithm(
    "coarse-fine",
    aliases=("two-phase", "center-out", "adaptive"),
)
class CoarseFineSweep(SweepAlgorithmBase):
    """Coarse-fine two-phase beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "Coarse-Fine Two-Phase Sweep"

    @property
    def description(self) -> str:
        return "Two-phase beam steering: coarse center-out search, then fine refinement. ~30% more efficient."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000) -> Dict:
        """Execute coarse-fine two-phase sweep with optional closed-loop feedback

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Coarse step size in degrees (default: 10)
            fine_span: Fine search span around best coarse angle (default: 10)
            fine_res: Fine resolution in degrees (default: 1)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback for each angle (default: False)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)
            use_waveform: If True, simulate real signal-level SNR/SER (default: False)
            modulation: Modulation type: QPSK, 16QAM, or 64QAM (default: QPSK)
            num_symbols: Number of symbols per measurement (default: 1000)

        Returns:
            Dictionary with sweep results including optional 'ser_coarse' and 'ser_fine' keys
        """
        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Use UE direction as the reference (same baseline as linear sweep/connect)
        specular_angle = compute_specular_angle(ris, ue)

        # Generate codebook centered on specular angle
        local_coarse, num_coarse = generate_codebook(fov, step)
        abs_angles = specular_angle + local_coarse

        snr_coarse = []
        pwr_coarse = []
        ser_coarse = [None] * num_coarse if use_waveform else None
        feedback_collector = FeedbackCollector(enable_feedback)

        # Setup signal simulator if waveform mode is enabled
        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        # Coarse phase: test center first, then expand
        center_idx = len(local_coarse) // 2
        test_order = [center_idx]

        # Add indices in expanding pattern from center
        for offset in range(1, len(local_coarse)):
            if center_idx - offset >= 0:
                test_order.append(center_idx - offset)
            if center_idx + offset < len(local_coarse):
                test_order.append(center_idx + offset)

        # Test angles in center-out order
        snr_array = np.full(num_coarse, np.nan)
        pwr_array = np.full(num_coarse, np.nan)

        def measure_idx(idx: int):
            if not np.isnan(snr_array[idx]):
                return
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angles[idx], seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False  # Don't store intermediate measurements
                )
            snr_val, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=seed + idx if seed else None,
            )
            snr_array[idx] = snr_val
            pwr_array[idx] = res['pwr_dBm']
            if ser_coarse is not None:
                ser_coarse[idx] = ser_val

            if enable_feedback and 'feedback_info' in res:
                feedback_collector.add(float(abs_angles[idx]), float(local_coarse[idx]), res['feedback_info'], phase='coarse')

        # Measure ML suggestions ahead of center-out traversal
        if ml_angles:
            for suggested in ml_angles:
                idx = local_angle_to_index(float(suggested), fov, step, num_coarse)
                measure_idx(idx)

        for idx in test_order:
            measure_idx(idx)

        snr_coarse = snr_array.tolist()
        pwr_coarse = pwr_array.tolist()

        # Find best coarse angle
        best_idx = int(np.argmax(snr_array))
        best_local = local_coarse[best_idx]

        # Phase 2: Fine sweep (constrained within original FOV)
        fine_start = max(best_local - fine_span, -fov)
        fine_end = min(best_local + fine_span, fov)
        local_fine = np.arange(fine_start, fine_end + fine_res, fine_res)
        abs_angles_fine = specular_angle + local_fine
        snr_fine = []
        ser_fine = [None] * len(local_fine) if use_waveform else None

        for i, abs_a in enumerate(abs_angles_fine):
            with self._ap_state_guard(ap):
                r = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_a, seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False  # Don't store intermediate measurements
                )
            snr_val, ser_val = apply_waveform_realism(
                r,
                link_simulator,
                seed=seed + i if seed else None,
            )
            snr_fine.append(snr_val)
            if ser_fine is not None:
                ser_fine[i] = ser_val

            # Store feedback details if enabled
            if enable_feedback and 'feedback_info' in r:
                feedback_collector.add(float(abs_a), float(local_fine[i]), r['feedback_info'], phase='fine')

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        result = {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': snr_coarse,
            'pwr_coarse': pwr_coarse,
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
            'specular_angle': float(specular_angle),
            'feedback_enabled': enable_feedback,
            'feedback_details': feedback_collector.get_details()
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_coarse:
            result['ser_coarse'] = ser_coarse
            result['ser_fine'] = ser_fine if ser_fine else []

        return result
