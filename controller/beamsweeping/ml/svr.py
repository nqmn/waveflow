"""Support Vector Regression-based beam prior."""

from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

try:
    from sklearn.svm import SVR  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    SVR = None


class SVRPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained Support Vector Regression model."""

    MODEL_ENV = "RISNET_SVR_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/svr_beam_predictor.pkl")

    def __init__(self, network):
        super().__init__(network)
        self._model: Optional[SVR] = None
        self._scaler = None
        self._model_path = None
        self._model_error = None
        self._load_model()

    @property
    def name(self) -> str:
        return "SVR Beam Prior"

    @property
    def description(self) -> str:
        if self._model is None:
            return f"SVR predictor (Error: {self._model_error})"
        return "Predicts promising local beams using Support Vector Regression."

    def _load_model(self):
        """Attempt to load the SVR model; fallback if missing."""
        if SVR is None:
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
                checkpoint = pickle.load(f)
                self._model = checkpoint
                # Extract scaler if stored in checkpoint
                if hasattr(checkpoint, 'scaler'):
                    self._scaler = checkpoint.scaler
        except Exception as exc:  # pragma: no cover - load failure
            self._model_error = f"failed to load SVR model: {exc}"
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
        if self._model is None or SVR is None:
            raise RuntimeError(f"SVR model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        try:
            # Scale features if scaler is available
            if self._scaler is not None:
                features_scaled = self._scaler.transform(np.array([features], dtype=float))
            else:
                features_scaled = np.array([features], dtype=float)

            pred = float(self._model.predict(features_scaled)[0])
        except Exception as e:  # pragma: no cover - prediction failure
            raise RuntimeError(f"SVR prediction failed: {e}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _is_model_available(self) -> bool:
        """Check if SVR model is loaded."""
        return self._model is not None and SVR is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        """SVR-specific uncertainty (based on model performance).

        SVR has good performance (R²=0.8830) with moderate uncertainty.
        """
        if not model_available:
            return 10.0
        return 3.5  # SVR uncertainty

    def _build_feature_vector(self, ap, ris, ue) -> List[float]:
        """Construct feature vector using 13 features (9 positions + 4 derived).

        Features (13 total):
          - AP position (3 coords: x, y, z)
          - RIS position (3 coords: x, y, z)
          - UE position (3 coords: x, y, z)
          - d_ap_ris: Euclidean distance from AP to RIS
          - d_ris_ue: Euclidean distance from RIS to UE
          - aoa: Angle of Arrival (azimuth, degrees, [0, 360))
          - aod: Angle of Departure (azimuth, degrees, [0, 360))
        """
        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)

        # Distance features
        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))
        d_ris_ue = float(np.linalg.norm(ue_pos - ris_pos))

        # Angle features (azimuth only, 2D XY plane)
        aoa = float(np.degrees(np.arctan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])))
        aoa = aoa % 360  # Normalize to [0, 360)

        aod = float(np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])))
        aod = aod % 360  # Normalize to [0, 360)

        features = [
            # Position features (3D coordinates)
            float(ap_pos[0]), float(ap_pos[1]), float(ap_pos[2]),
            float(ris_pos[0]), float(ris_pos[1]), float(ris_pos[2]),
            float(ue_pos[0]), float(ue_pos[1]), float(ue_pos[2]),
            # Distance features
            d_ap_ris, d_ris_ue,
            # Angle features
            aoa, aod,
        ]
        return features
