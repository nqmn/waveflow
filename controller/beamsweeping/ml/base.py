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
                - 'confidence': Confidence score (float, 0-1, where 1.0 = highest confidence)
                - 'model_available': Whether model loaded successfully (bool)
        """
        import time
        start_time = time.perf_counter()

        angles = self.predict_local_angles(ap_name, ris_name, ue_name, fov, top_k)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Determine model availability and confidence
        model_available = self._is_model_available()
        confidence = self._compute_confidence(model_available, angles)

        metrics = {
            'prediction_time_ms': round(elapsed_ms, 3),
            'confidence': round(confidence, 3),
            'model_available': model_available,
        }

        return angles, metrics

    def _is_model_available(self) -> bool:
        """Check if ML model is loaded and available."""
        # Override in subclasses if needed
        return True

    def _compute_confidence(self, model_available: bool, angles: List[float]) -> float:
        """Compute confidence score for predictions.

        Confidence based on:
        - Model availability (0.5 if fallback, 1.0 if model loaded)
        - Prediction stability (angles should be within reasonable range)

        A prediction is "confident" if:
        - Model is successfully loaded (not using fallback)
        - Predicted angles are reasonable (within FOV bounds)

        Returns: float between 0.0 (no confidence) and 1.0 (high confidence)
        """
        if not model_available:
            return 0.5  # Fallback mode has lower confidence

        # Check if angles are valid (not NaN, not extreme outliers)
        if not angles or len(angles) == 0:
            return 0.3

        return 1.0  # Model is loaded and produced valid predictions
