"""XGBoost-based beam prior."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

try:
    import xgboost as xgb  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    xgb = None


class XGBPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained XGBoost model."""

    MODEL_ENV = "RISNET_XGB_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/xgb_beam_predictor.json")

    def __init__(self, network):
        super().__init__(network)
        self._booster: Optional["xgb.Booster"] = None
        self._model_path = None
        self._model_error = None
        self._load_model()

    @property
    def name(self) -> str:
        return "XGBoost Beam Prior"

    @property
    def description(self) -> str:
        if self._booster is None:
            return f"XGBoost predictor (Error: {self._model_error})"
        return "Predicts promising local beams using an XGBoost regressor."

    def _load_model(self):
        """Attempt to load the XGBoost model; fallback if missing."""
        if xgb is None:
            self._model_error = "xgboost package not installed"
            return

        model_path = os.environ.get(self.MODEL_ENV)
        if model_path:
            candidate = Path(model_path)
        else:
            candidate = self.DEFAULT_MODEL

        if not candidate.exists():
            self._model_error = f"model file not found ({candidate})"
            return

        booster = xgb.Booster()
        try:
            booster.load_model(str(candidate))
        except Exception as exc:  # pragma: no cover - load failure
            self._model_error = f"failed to load XGB model: {exc}"
            return

        self._booster = booster
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
        if self._booster is None or xgb is None:
            raise RuntimeError(f"XGBoost model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        try:
            dmatrix = xgb.DMatrix(np.array([features], dtype=float))
            pred = float(self._booster.predict(dmatrix)[0])
        except Exception as e:  # pragma: no cover - prediction failure
            raise RuntimeError(f"XGBoost prediction failed: {e}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _is_model_available(self) -> bool:
        """Check if XGBoost model is loaded."""
        return self._booster is not None and xgb is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        """XGBoost-specific uncertainty (based on model performance).

        XGBoost typically achieves good accuracy with ~3 degree uncertainty.
        """
        if not model_available:
            return 10.0
        return 3.0  # XGBoost uncertainty

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
            float(getattr(ris, "bits", 1)),  # Default: 1 bit (matches trained dataset)
        ]
        return features
