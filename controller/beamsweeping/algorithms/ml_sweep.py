"""ML-Guided Beam Sweep Algorithm

Uses machine learning to predict promising beam angles, then performs
intelligent sweep around those predictions with optional fine-phase refinement.

Strategy:
- Phase 1: Use ML predictor to identify top-k candidate angles
- Phase 2: Perform coarse sweep around ML suggestions
- Phase 3: Fine refinement around the best angle found

Supports real signal-level emulation via use_waveform parameter.
"""
import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..ml import MLPredictorLoader
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


@register_algorithm("ml-guided")
class MLGuidedSweep(SweepAlgorithmBase):
    """ML-guided beam sweep algorithm"""

    @property
    def name(self) -> str:
        return "ML-Guided Beam Sweep"

    @property
    def description(self) -> str:
        return "Uses ML predictor to identify promising angles, then sweeps with adaptive refinement."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              fine_span: float = 10.0, fine_res: float = 1.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_predictor: str = 'xgb', top_k: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000) -> Dict:
        """Execute ML-guided sweep with optional closed-loop feedback

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (default: 60)
            step: Coarse step size in degrees (default: 10)
            fine_span: Fine search span around best angle (default: 10)
            fine_res: Fine resolution in degrees (default: 1)
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback (default: True)
            max_feedback_iterations: Max iterations for feedback loop (default: 3)
            ml_predictor: ML predictor name (default: 'xgb')
            top_k: Number of top predictions to use (default: 3)
            use_waveform: If True, simulate real signal-level SNR/SER (default: False)
            modulation: Modulation type: QPSK, 16QAM, or 64QAM (default: QPSK)
            num_symbols: Number of symbols per measurement (default: 1000)

        Returns:
            Dictionary with sweep results including ML predictions and optional SER
        """
        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Load ML predictor
        try:
            predictor = MLPredictorLoader.get_predictor(ml_predictor, self.network)
        except ValueError as e:
            raise ValueError(f"Failed to load ML predictor: {e}")

        # Get ML predictions with metrics
        ml_suggestions, ml_metrics = predictor.predict_with_metrics(
            ap_name, ris_name, ue_name, fov, top_k=top_k
        )

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

        # Set specular_angle for result reporting (incident direction)
        specular_angle = ap_angle

        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        # Phase 1: Test ML-suggested angles first
        ml_results = []
        snr_ml = []
        ser_ml = [] if use_waveform else None
        tested_angles = set()

        for i, ml_angle in enumerate(ml_suggestions):
            # Convert deflection angle to absolute beam angle
            if angle_diff > 0:
                abs_angle = ap_angle + ml_angle
            else:
                abs_angle = ap_angle - ml_angle
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angle, seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False  # Don't store intermediate measurements
                )
            snr_val, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=seed + i if seed else None,
            )
            snr_ml.append(snr_val)
            if ser_ml is not None:
                ser_ml.append(ser_val)

            ml_results.append({
                'local_angle': float(ml_angle),
                'abs_angle': float(abs_angle),
                'snr_dB': float(res['snr_dB']),
                'pwr_dBm': float(res['pwr_dBm']),
                'ser_percent': ser_val
            })
            tested_angles.add(round(ml_angle, 2))

        # Phase 2: Coarse sweep (adaptive center-out from specular)
        local_coarse, num_coarse = generate_codebook(fov, step)

        # Clamp local deflection angles to RIS FOV constraint
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_local_coarse = clamp_local_deflection_to_ris_fov(local_coarse, ris_max_angle)

        # Convert deflection angles to absolute beam angles
        if angle_diff > 0:
            # UE is counterclockwise from AP, so add deflection to AP angle
            abs_angles = ap_angle + clamped_local_coarse
        else:
            # UE is clockwise from AP, so subtract deflection from AP angle
            abs_angles = ap_angle - clamped_local_coarse

        snr_array = np.full(num_coarse, np.nan)
        pwr_array = np.full(num_coarse, np.nan)
        ser_coarse = [None] * num_coarse if use_waveform else None

        # Prioritize center and ML suggestions
        center_idx = len(local_coarse) // 2
        test_order = [center_idx]

        # Add ML-suggested indices
        for angle in ml_suggestions:
            idx = local_angle_to_index(angle, fov, step, num_coarse)
            if 0 <= idx < num_coarse and idx not in test_order:
                test_order.append(idx)

        # Add center-out expansion
        for offset in range(1, len(local_coarse)):
            if center_idx - offset >= 0 and (center_idx - offset) not in test_order:
                test_order.append(center_idx - offset)
            if center_idx + offset < len(local_coarse) and (center_idx + offset) not in test_order:
                test_order.append(center_idx + offset)

        # Test angles in prioritized order
        def measure_idx(idx: int):
            if not np.isnan(snr_array[idx]):
                return
            abs_a = abs_angles[idx]
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_a, seed=seed,
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

        for idx in test_order:
            measure_idx(idx)

        snr_coarse = snr_array.tolist()
        pwr_coarse = pwr_array.tolist()

        # Find best coarse angle
        best_idx = int(np.argmax(snr_array))
        best_local = local_coarse[best_idx]

        # Phase 3: Fine sweep (constrained within FOV)
        fine_start = max(best_local - fine_span, -fov)
        fine_end = min(best_local + fine_span, fov)
        local_fine = np.arange(fine_start, fine_end + fine_res, fine_res)

        # Convert fine phase deflection angles to absolute beam angles
        if angle_diff > 0:
            abs_angles_fine = ap_angle + local_fine
        else:
            abs_angles_fine = ap_angle - local_fine

        snr_fine = []
        num_fine = len(local_fine)
        ser_fine = [None] * num_fine if use_waveform else None

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

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        result = {
            'ml_predictor': ml_predictor,
            'ml_suggestions': ml_suggestions,
            'ml_results': ml_results,
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': snr_coarse,
            'pwr_coarse': pwr_coarse,
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine)),
            'specular_angle': float(specular_angle),
            'ml_metrics': ml_metrics,
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_coarse:
            result['ser_coarse'] = ser_coarse
            result['ser_fine'] = ser_fine if ser_fine else []
            result['ser_ml'] = ser_ml if ser_ml else []

        return result
