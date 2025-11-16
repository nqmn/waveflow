"""LightGBM-based beam prior."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

from utils.link_budget import build_config_from_nodes, compute_ris_link_metrics

try:
    import lightgbm as lgb  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    lgb = None


class LGBMPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained LightGBM model."""

    MODEL_ENV = "RISNET_LGBM_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/lgbm_beam_predictor.txt")

    def __init__(self, network):
        super().__init__(network)
        self._booster: Optional["lgb.Booster"] = None
        self._model_path = None
        self._model_error = None
        self._load_model()

    @property
    def name(self) -> str:
        return "LightGBM Beam Prior"

    @property
    def description(self) -> str:
        if self._booster is None:
            return f"LightGBM predictor (Error: {self._model_error})"
        return "Predicts promising local beams using a LightGBM regressor."

    def _load_model(self):
        if lgb is None:
            self._model_error = "lightgbm package not installed"
            return

        model_path = os.environ.get(self.MODEL_ENV)
        candidate = Path(model_path) if model_path else self.DEFAULT_MODEL

        if not candidate.exists():
            self._model_error = f"model file not found ({candidate})"
            return

        try:
            booster = lgb.Booster(model_file=str(candidate))
        except Exception as exc:
            self._model_error = f"failed to load LightGBM model: {exc}"
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
        if self._booster is None or lgb is None:
            raise RuntimeError(f"LightGBM model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        try:
            pred = float(self._booster.predict(np.array([features], dtype=float))[0])
        except Exception as exc:
            raise RuntimeError(f"LightGBM prediction failed: {exc}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _is_model_available(self) -> bool:
        return self._booster is not None and lgb is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        if not model_available:
            return 10.0
        return 3.0

    def _build_feature_vector(self, ap, ris, ue) -> List[float]:
        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)

        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))

        aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
        aoa_sin = float(math.sin(aoa_rad))
        aoa_cos = float(math.cos(aoa_rad))

        dx, dy, dz = (ris_pos - ap_pos).tolist()
        azimuth = math.atan2(dy, dx)
        elevation = math.atan2(dz, math.hypot(dx, dy))
        az_sin = float(math.sin(azimuth))
        az_cos = float(math.cos(azimuth))
        el_sin = float(math.sin(elevation))
        el_cos = float(math.cos(elevation))

        aod_deg = float(np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))) % 360

        physics_config = build_config_from_nodes(ap, ris, ue)
        metrics = compute_ris_link_metrics(ap_pos, ris_pos, ue_pos, aod_deg, physics_config)
        snr = float(metrics['snr_dB'])
        rssi = float(metrics['rssi_dBm'])

        return [
            float(ap_pos[0]), float(ap_pos[1]), float(ap_pos[2]),
            float(ris_pos[0]), float(ris_pos[1]), float(ris_pos[2]),
            d_ap_ris,
            aoa_sin, aoa_cos,
            float(dx), float(dy), float(dz),
            az_sin, az_cos, el_sin, el_cos,
            snr, rssi,
        ]
