"""Base classes for machine-learning beam sweep predictors."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Tuple


class SweepMLPredictor(ABC):
    """Interface for ML-based beam guidance."""

    def __init__(self, network):
        self.network = network

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-friendly predictor name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the predictor."""
        raise NotImplementedError

    @abstractmethod
    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        """Return local beam angles (degrees) to prioritize."""
        raise NotImplementedError

    def predict_with_metrics(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> Tuple[List[float], Dict]:
        """Return local beam angles with prediction metrics.

        Returns:
            Tuple of (angles, metrics_dict) where metrics_dict contains:
                - 'prediction_time_ms': Time to make prediction (float)
                - 'uncertainty': Prediction uncertainty/variance (float, in degrees)
                - 'error_bounds': Estimated error bounds ±X degrees (float)
                - 'model_available': Whether model loaded successfully (bool)

        Note: Confidence is computed when actual/true values are available during evaluation.
        """
        import time
        start_time = time.perf_counter()

        angles = self.predict_local_angles(ap_name, ris_name, ue_name, fov, top_k)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Determine model availability
        model_available = self._is_model_available()

        # Compute uncertainty and error bounds
        uncertainty = self._compute_uncertainty(model_available)
        error_bounds = self._compute_error_bounds(uncertainty)

        metrics = {
            'prediction_time_ms': round(elapsed_ms, 3),
            'uncertainty': round(uncertainty, 3),
            'error_bounds': round(error_bounds, 3),
            'model_available': model_available,
        }

        return angles, metrics

    def _is_model_available(self) -> bool:
        """Check if ML model is loaded and available."""
        # Override in subclasses if needed
        return True

    def _compute_uncertainty(self, model_available: bool) -> float:
        """Compute prediction uncertainty/variance (in degrees).

        Uncertainty represents the expected variance in predictions.
        Higher uncertainty = less reliable predictions.

        For model-based predictions: 2-5 degrees (depends on model accuracy)
        For unavailable models: 10 degrees (high uncertainty)

        Returns: float uncertainty in degrees
        """
        if not model_available:
            return 10.0  # High uncertainty when model unavailable

        # Default uncertainty for available models (can be overridden in subclasses)
        # Based on model type and training accuracy
        return 3.5  # Typical uncertainty for trained models

    def _compute_error_bounds(self, uncertainty: float) -> float:
        """Compute estimated prediction error bounds (±X degrees).

        Error bounds = expected range of error from true optimal angle.
        Based on the uncertainty metric.

        Returns: float error bound in degrees (symmetric: ±value)
        """
        # Error bounds = 1.5x the uncertainty
        # uncertainty=2.5° -> error_bounds=3.75° ≈ ±3.8°
        # uncertainty=10.0° -> error_bounds=15.0° ≈ ±15.0°
        return uncertainty * 1.5

    def compute_confidence(self, predicted_angle: float, actual_angle: float, fov: float = 60.0) -> float:
        """Compute confidence score based on prediction accuracy.

        Confidence represents how close the prediction is to the actual/true value.

        Calculation:
        - If prediction error = 0°: confidence = 1.0 (100%)
        - If prediction error = ±5°: confidence ≈ 0.92 (92%)
        - If prediction error = ±10°: confidence ≈ 0.84 (84%)
        - If prediction error = ±FOV/2 (e.g., 30°): confidence ≈ 0.0 (0%)

        Returns: float confidence between 0.0 and 1.0
        """
        error = abs(predicted_angle - actual_angle)

        # Normalize error relative to FOV
        # At FOV/2 distance, confidence approaches 0
        max_error = fov / 2.0  # Half FOV as max acceptable error

        # Confidence = 1 - (error / max_error), clipped to [0, 1]
        confidence = max(0.0, 1.0 - (error / max_error))

        return round(confidence, 3)
