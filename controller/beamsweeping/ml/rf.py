"""Random Forest-based beam prior."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

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
        try:
            pred = float(self._model.predict(np.array([features], dtype=float))[0])
        except Exception as e:  # pragma: no cover - prediction failure
            raise RuntimeError(f"Random Forest prediction failed: {e}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _is_model_available(self) -> bool:
        """Check if Random Forest model is loaded."""
        return self._model is not None and RandomForestRegressor is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        """Random Forest-specific uncertainty (based on model performance).

        Random Forest has best performance (R²=0.9438), so lowest uncertainty.
        """
        if not model_available:
            return 10.0
        return 2.5  # Random Forest uncertainty (best model)

    def _build_feature_vector(self, ap, ris, ue) -> List[float]:
        """Construct simple geometry-based features."""
        ap_pos = ap.pos
        ris_pos = ris.pos
        ue_pos = ue.pos
        vec_ap_ris = ris_pos - ap_pos
        vec_ris_ue = ue_pos - ris_pos

        features = [
            float(ap_pos[0]), float(ap_pos[1]), float(ap_pos[2]),
            float(ris_pos[0]), float(ris_pos[1]), float(ris_pos[2]),
            float(ue_pos[0]), float(ue_pos[1]), float(ue_pos[2]),
            float(np.linalg.norm(vec_ap_ris)),
            float(np.linalg.norm(vec_ris_ue)),
            float(getattr(ap, "power_dBm", 20.0)),
            float(getattr(ap, "freq", 5.8e9)),
            float(getattr(ris, "N", 16)),
            float(getattr(ris, "bits", 2)),
        ]
        return features
