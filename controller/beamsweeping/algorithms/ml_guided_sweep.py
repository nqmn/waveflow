"""ML-Guided Beam Sweep Algorithm (1-Phase)

Uses machine learning predictions to identify candidate angles, then validates
them through actual measurements to find the best performer.

This is a smart ML-guided validation approach:
- ML predictor identifies top-K promising angles
- Test all predicted angles to validate performance
- Return the best result found through measurement
- Balances prediction efficiency with measurement accuracy
"""
import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..ml import MLPredictorLoader
from ..common import (
    apply_waveform_realism,
    setup_waveform_simulator,
    validate_and_get_nodes,
    clamp_to_ris_fov,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm


@register_algorithm("ml", aliases=("ml-guided",))
class MLGuidedSweep(SweepAlgorithmBase):
    """ML-guided beam sweep algorithm with validation (1-phase)"""

    @property
    def name(self) -> str:
        return "ML-Guided Beam Sweep"

    @property
    def description(self) -> str:
        return "ML-guided beam sweep: validates top ML-predicted angles through measurement."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_predictor: str = 'xgb', top_k: int = 5,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000) -> Dict:
        """Execute ML-guided beam sweep with validation (single phase)

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (for ML context)
            step: Not used in ML-guided mode
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback
            max_feedback_iterations: Max iterations for feedback loop
            ml_predictor: ML predictor name (default: 'xgb')
            top_k: Number of top angles to test (default: 5)
            use_waveform: If True, simulate real signal-level SNR/SER
            modulation: Modulation type: QPSK, 16QAM, or 64QAM
            num_symbols: Number of symbols per measurement

        Returns:
            Dictionary with ML predictions, test results, and best angle found
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

        # Clamp ML-suggested angles to RIS FOV constraint (native RIS capability)
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_ml_suggestions = clamp_local_deflection_to_ris_fov(
            np.array(ml_suggestions), ris_max_angle
        ).tolist()

        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        # PHASE 1: Test ML-suggested angles (clamped to RIS FOV)
        print(f"\n[ML-GUIDED SWEEP]")
        print(f"ML Predictor: {ml_predictor}")
        print(f"Validating {len(clamped_ml_suggestions)} ML-predicted angles (top_k={top_k})")

        ml_results = []
        local_angles = []
        snr_values = []
        ser_values = [] if use_waveform else None

        for i, ml_angle in enumerate(clamped_ml_suggestions):
            # Convert deflection angle to absolute beam angle
            if angle_diff > 0:
                abs_angle = ap_angle + ml_angle
            else:
                abs_angle = ap_angle - ml_angle
            local_angles.append(ml_angle)

            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angle, seed=seed,
                    enable_feedback=enable_feedback,
                    max_feedback_iterations=max_feedback_iterations,
                    store_in_active_links=False,  # Don't store intermediate measurements
                    use_get_snr=self._should_use_get_snr()  # Use get_snr() if enabled
                )

            snr_val, ser_val = apply_waveform_realism(
                res,
                link_simulator,
                seed=seed + i if seed else None,
            )
            snr_values.append(snr_val)

            if ser_values is not None:
                ser_values.append(ser_val)

            ml_results.append({
                'local_angle': float(ml_angle),
                'abs_angle': float(abs_angle),
                'snr_dB': float(snr_val),
                'pwr_dBm': float(res['pwr_dBm']),
                'ser_percent': ser_val
            })

        # Find best result first
        best_idx = int(np.argmax(snr_values))

        # Now print with marker only for the best index
        for i, snr_val in enumerate(snr_values):
            ml_angle = local_angles[i]
            # Convert deflection angle to absolute beam angle for display
            if angle_diff > 0:
                abs_angle = ap_angle + ml_angle
            else:
                abs_angle = ap_angle - ml_angle
            marker = " <-- BEST" if i == best_idx else ""
            print(f"  idx={i}: {ml_angle:>7.1f}° (abs: {abs_angle:>7.1f}°) SNR={snr_val:>7.2f} dB{marker}")
        best_local = local_angles[best_idx]
        best_snr = snr_values[best_idx]
        # Convert deflection angle to absolute beam angle
        if angle_diff > 0:
            best_abs = ap_angle + best_local
        else:
            best_abs = ap_angle - best_local

        print(f"\nFinal ML Result:")
        print(f"  Best local angle: {best_local:.2f}°")
        print(f"  Best absolute angle: {best_abs:.2f}°")
        print(f"  Best SNR: {best_snr:.2f} dB")

        result = {
            'ml_predictor': ml_predictor,
            'ml_suggestions': ml_suggestions,
            'ml_results': ml_results,
            'local_coarse': np.array(local_angles).tolist(),
            'snr_coarse': snr_values,
            'pwr_coarse': [r['pwr_dBm'] for r in ml_results],
            'best_angle': float(best_abs),
            'best_snr': float(best_snr),
            'best_local': float(best_local),
            'specular_angle': float(specular_angle),
            'num_angles_tested': len(ml_suggestions),
            'ml_metrics': ml_metrics,
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_values:
            result['ser_coarse'] = ser_values

        return result
