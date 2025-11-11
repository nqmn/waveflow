"""ML-Only Beam Sweep Algorithm (1-Phase)

Uses machine learning predictions as the ONLY sweep strategy.
No exhaustive fallback - trusts the ML model to find the best angles.

This is a true ML-guided approach:
- ML predictor identifies promising angles
- Test ONLY those predicted angles
- Return the best result found
- Fast and efficient for pre-trained models
"""
import numpy as np
from typing import Dict
from ..base import SweepAlgorithmBase
from ..ml import MLPredictorLoader
from ..common import (
    apply_waveform_realism,
    compute_ris_normal_for_sweep,
    setup_waveform_simulator,
    validate_and_get_nodes,
    clamp_to_ris_fov,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm


@register_algorithm("ml", aliases=("ml-only",))
class MLOnlySweep(SweepAlgorithmBase):
    """ML-only beam sweep algorithm (1-phase)"""

    @property
    def name(self) -> str:
        return "ML-Only Beam Sweep"

    @property
    def description(self) -> str:
        return "Pure ML-guided: tests only ML-predicted angles, no exhaustive fallback."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_predictor: str = 'xgb', top_k: int = 5,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000) -> Dict:
        """Execute ML-only sweep (single phase)

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (for ML context)
            step: Not used in ML-only mode
            seed: Random seed for reproducibility
            enable_feedback: If True, use closed-loop feedback
            max_feedback_iterations: Max iterations for feedback loop
            ml_predictor: ML predictor name (default: 'xgb')
            top_k: Number of top angles to test (default: 5)
            use_waveform: If True, simulate real signal-level SNR/SER
            modulation: Modulation type: QPSK, 16QAM, or 64QAM
            num_symbols: Number of symbols per measurement

        Returns:
            Dictionary with ML predictions and results
        """
        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Load ML predictor
        try:
            predictor = MLPredictorLoader.get_predictor(ml_predictor, self.network)
        except ValueError as e:
            raise ValueError(f"Failed to load ML predictor: {e}")

        # Get ML predictions
        ml_suggestions = predictor.predict_local_angles(
            ap_name, ris_name, ue_name, fov, top_k=top_k
        )

        # Calculate base direction (UE direction from RIS)
        # Calculate optimal RIS normal as bisector of AP and UE directions
        # This ensures the RIS can simultaneously serve both AP (receive) and UE (transmit)
        # within its FOV constraints, consistent with single connect command
        specular_angle = compute_ris_normal_for_sweep(ap, ris, ue)

        # Clamp ML-suggested angles to RIS FOV constraint (native RIS capability)
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        clamped_ml_suggestions = clamp_local_deflection_to_ris_fov(
            np.array(ml_suggestions), ris_max_angle
        ).tolist()

        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols, pilot_ratio=0.1)

        # PHASE 1: Test ONLY ML-suggested angles (clamped to RIS FOV)
        print(f"\n[ML-ONLY SWEEP]")
        print(f"ML Predictor: {ml_predictor}")
        print(f"Testing {len(clamped_ml_suggestions)} ML-predicted angles (top_k={top_k})")

        ml_results = []
        local_angles = []
        snr_values = []
        ser_values = [] if use_waveform else None

        for i, ml_angle in enumerate(clamped_ml_suggestions):
            abs_angle = specular_angle + ml_angle
            local_angles.append(ml_angle)

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
            abs_angle = specular_angle + ml_angle
            marker = " <-- BEST" if i == best_idx else ""
            print(f"  idx={i}: {ml_angle:>7.1f}° (abs: {abs_angle:>7.1f}°) SNR={snr_val:>7.2f} dB{marker}")
        best_local = local_angles[best_idx]
        best_snr = snr_values[best_idx]
        best_abs = specular_angle + best_local

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
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_values:
            result['ser_coarse'] = ser_values

        return result
