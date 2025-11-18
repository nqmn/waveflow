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
from typing import Dict, List
from ..base import SweepAlgorithmBase
from ..ml import MLPredictorLoader
from ..common import (
    apply_waveform_realism,
    setup_waveform_simulator,
    validate_and_get_nodes,
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

    @staticmethod
    def _quantize_local_angle(angle: float, increment: float) -> float:
        """Snap a prediction to the closest codebook increment."""
        if increment <= 0:
            return angle
        return round(angle / increment) * increment

    @staticmethod
    def _build_fixed_codebook(codebook_start: float, codebook_end: float, codebook_step: float) -> List[float]:
        """Build a fixed codebook with angles from start to end at specified step."""
        if codebook_step <= 0:
            return []
        codebook = []
        angle = codebook_start
        while angle <= codebook_end + 1e-6:
            codebook.append(round(angle, 1))
            angle += codebook_step
        return sorted(set(codebook))

    @staticmethod
    def _find_closest_codebook_angle(predicted_angle: float, codebook: List[float]) -> float:
        """Find the closest angle in the codebook."""
        if not codebook:
            return predicted_angle
        return min(codebook, key=lambda x: abs(x - predicted_angle))

    def _build_validation_candidates(
        self,
        predicted_angle: float,
        ris_max_angle: float,
        enable_validation: bool,
        increment: float,
        neighbors: int,
        include_predicted: bool,
        codebook_start: float = 10.0,
        codebook_end: float = 60.0,
        codebook_step: float = 10.0,
    ) -> List[float]:
        """Return the local angles we should validate around the ML prediction.

        With enable_validation=True and fixed codebook:
        - Quantize predicted angle to nearest codebook angle
        - Include N neighbors on each side from the codebook
        - include_predicted controls whether to add the raw prediction
        """
        neighbors = max(0, neighbors)
        candidates = set()

        if include_predicted or not enable_validation:
            candidates.add(predicted_angle)

        if enable_validation:
            # Build fixed codebook
            codebook = self._build_fixed_codebook(codebook_start, codebook_end, codebook_step)
            if codebook:
                # Find closest codebook angle
                closest = self._find_closest_codebook_angle(predicted_angle, codebook)
                closest_idx = codebook.index(closest)

                # Add neighbors from codebook
                for offset in range(-neighbors, neighbors + 1):
                    idx = closest_idx + offset
                    if 0 <= idx < len(codebook):
                        candidates.add(codebook[idx])

        if not candidates:
            candidates.add(predicted_angle)

        clamped = clamp_local_deflection_to_ris_fov(
            np.array(list(candidates), dtype=float),
            ris_max_angle
        )
        return sorted(set(clamped.tolist()))

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_predictor: str = 'xgb', top_k: int = 1,
              codebook_increment: float = 5.0,
              codebook_neighbors: int = 1,
              enable_codebook_validation: bool = False,
              include_predicted_angle: bool = True,
              codebook_start: float = 10.0,
              codebook_end: float = 60.0,
              codebook_step: float = 10.0,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None, **kwargs) -> Dict:
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
            top_k: Number of top angles to test (default: 1)
            codebook_increment: Deprecated - use codebook_start/end/step instead
            codebook_neighbors: Number of codebook angles to test on either side of quantized angle
            enable_codebook_validation: Whether to enable fixed codebook quantization and neighbor validation
            include_predicted_angle: If True, also include the raw ML prediction in validation set
            codebook_start: Start angle of fixed codebook (degrees, default: 10)
            codebook_end: End angle of fixed codebook (degrees, default: 60)
            codebook_step: Step size for fixed codebook (degrees, default: 10)
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

        ml_results = []
        local_angles = []
        snr_values = []
        ser_values = [] if use_waveform else None

        for ml_angle in clamped_ml_suggestions:
            validation_angles = self._build_validation_candidates(
                ml_angle,
                ris_max_angle,
                enable_codebook_validation,
                codebook_increment,
                codebook_neighbors,
                include_predicted_angle,
                codebook_start=codebook_start,
                codebook_end=codebook_end,
                codebook_step=codebook_step,
            )

            if enable_codebook_validation:
                print(f"\nML Prediction: {ml_angle:.1f}°")
                print(f"Codebook angles to test: {[f'{a:.0f}°' for a in sorted(validation_angles)]}")
            else:
                print(f"\nTesting {len(validation_angles)} angles")

            for local_angle in validation_angles:
                if angle_diff > 0:
                    abs_angle = ap_angle + local_angle
                else:
                    abs_angle = ap_angle - local_angle

                with self._ap_state_guard(ap):
                    measurement_seed = (seed + len(snr_values)) if seed is not None else None
                    res = self.network.connect(
                        ap_name, ris_name, ue_name,
                        beam_angle_deg=abs_angle,
                        seed=measurement_seed,
                        enable_feedback=enable_feedback,
                        max_feedback_iterations=max_feedback_iterations,
                        store_in_active_links=False,
                        use_get_snr=self._should_use_get_snr()
                    )

                snr_val, ser_val = apply_waveform_realism(
                    res,
                    link_simulator,
                    seed=measurement_seed,
                )
                snr_values.append(snr_val)
                local_angles.append(local_angle)

                if ser_values is not None:
                    ser_values.append(ser_val)

                ml_results.append({
                    'prediction_angle': float(ml_angle),
                    'local_angle': float(local_angle),
                    'abs_angle': float(abs_angle),
                    'snr_dB': float(snr_val),
                    'pwr_dBm': float(res['pwr_dBm']),
                    'ser_percent': ser_val
                })

        # Find best result using metric selector (if provided, otherwise default to SNR)
        if metric_selector is not None:
            best_idx = metric_selector.find_best_index(snr_values)
        else:
            best_idx = int(np.argmax(snr_values))

        # Print test results in a clean format
        print(f"\nCODEBOOK TEST RESULTS:")
        print(f"{'Angle (°)':<12} {'SNR (dB)':<12} {'Power (dBm)':<15} {'Status':<15}")
        print("-" * 55)
        for i, snr_val in enumerate(snr_values):
            local_angle = local_angles[i]
            pwr = ml_results[i]['pwr_dBm']
            marker = "BEST" if i == best_idx else ""
            print(f"{local_angle:<12.1f} {snr_val:<12.2f} {pwr:<15.2f} {marker}")
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
            'num_angles_tested': len(local_angles),
            'num_predictions': len(ml_suggestions),
            'codebook_increment': float(codebook_increment),
            'codebook_neighbors': codebook_neighbors,
            'codebook_validation_enabled': enable_codebook_validation,
            'ml_metrics': ml_metrics,
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_values:
            result['ser_coarse'] = ser_values

        return result
