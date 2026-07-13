"""Random Forest-based beam prior."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

from .features import build_sklearn_features

try:
    from sklearn.ensemble import RandomForestRegressor  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    RandomForestRegressor = None


class RFPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained Random Forest model."""

    MODEL_ENV = "RISNET_RF_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/rf_beam_predictor.pkl")

    def __init__(self, network):
        super().__init__(network)
        self._model: Optional[RandomForestRegressor] = None
        self._model_path = None
        self._model_error = None
        self._last_uncertainty: Optional[float] = None
        self._load_model()

    @property
    def name(self) -> str:
        return "Random Forest Beam Prior"

    @property
    def description(self) -> str:
        if self._model is None:
            return f"Random Forest predictor (Error: {self._model_error})"
        return "Predicts promising local beams using a Random Forest regressor."

    def _load_model(self):
        """Attempt to load the Random Forest model; fallback if missing."""
        if RandomForestRegressor is None:
            self._model_error = "scikit-learn package not installed"
            return

        model_path = os.environ.get(self.MODEL_ENV)
        if model_path:
            candidate = Path(model_path)
        else:
            candidate = self.DEFAULT_MODEL

        if not candidate.exists():
            self._model_error = f"model file not found ({candidate})"
            return

        try:
            with candidate.open('rb') as f:
                self._model = pickle.load(f)
        except Exception as exc:  # pragma: no cover - load failure
            self._model_error = f"failed to load RF model: {exc}"
            return

        self._model_path = candidate
        self._model_error = None

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        """Return ML-prioritized local beam angles."""
        if self._model is None or RandomForestRegressor is None:
            raise RuntimeError(f"Random Forest model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        X = np.array([features], dtype=float)
        try:
            pred = float(self._model.predict(X)[0])
        except Exception as e:  # pragma: no cover - prediction failure
            raise RuntimeError(f"Random Forest prediction failed: {e}")

        self._last_uncertainty = self._ensemble_uncertainty(X)

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _ensemble_uncertainty(self, X: np.ndarray) -> Optional[float]:
        """Standard deviation of per-tree predictions (degrees), if available."""
        estimators = getattr(self._model, 'estimators_', None)
        if not estimators:
            return None
        try:
            tree_preds = np.array([est.predict(X)[0] for est in estimators], dtype=float)
        except Exception:  # pragma: no cover - defensive against exotic pickles
            return None
        return float(np.std(tree_preds))

    def _is_model_available(self) -> bool:
        """Check if Random Forest model is loaded."""
        return self._model is not None and RandomForestRegressor is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        """Random Forest uncertainty from the spread of per-tree predictions.

        The ensemble standard deviation from the most recent prediction is a
        data-driven measure of confidence: unanimous trees give a low value,
        disagreeing trees a high one. Falls back to a fixed estimate when the
        spread is unavailable.
        """
        if not model_available:
            return 10.0
        if self._last_uncertainty is not None:
            # Floor keeps error bounds non-degenerate when all trees agree
            return max(0.1, self._last_uncertainty)
        return 3.5  # Fallback: typical test MAE band (R^2~0.87 on beam_dataset)

    def _build_feature_vector(self, ap, ris, ue) -> List[float]:
        """Construct the canonical feature vector shared with the training scripts.

        See controller/beamsweeping/ml/features.py (SKLEARN_FEATURE_COLUMNS) for
        the authoritative column list and ordering.
        """
        return build_sklearn_features(ap, ris, ue)
