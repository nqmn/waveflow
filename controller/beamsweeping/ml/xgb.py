"""XGBoost-based beam prior."""

from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import List, Optional

import math
import numpy as np

from .base import SweepMLPredictor

from utils.link_budget import build_config_from_nodes, compute_ris_link_metrics

try:
    import xgboost as xgb  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    xgb = None


class XGBPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained XGBoost model."""

    MODEL_ENV = "RISNET_XGB_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/xgb_beam_predictor.json")
    SCALER_FILENAME = "xgb_scaler.pkl"
    PCA_FILENAME = "xgb_pca.pkl"
    KMEANS_FILENAME = "xgb_kmeans.pkl"
    PIPELINE_META_FILENAME = "xgb_pipeline.json"

    SCALER_ENV = "RISNET_XGB_SCALER"
    PCA_ENV = "RISNET_XGB_PCA"
    KMEANS_ENV = "RISNET_XGB_KMEANS"

    def __init__(self, network):
        super().__init__(network)
        self._booster: Optional["xgb.Booster"] = None
        self._model_path = None
        self._model_error = None
        self._model_dir: Optional[Path] = None
        self._scaler = None
        self._pca = None
        self._kmeans = None
        self._pipeline_metadata = None
        self._pipeline_loaded = False
        self._pipeline_mandatory = False
        self._pipeline_error = None
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

        self._model_dir = candidate.parent

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
        self._load_pipeline(candidate.parent)
        if self._pipeline_mandatory and not self._pipeline_loaded:
            self._model_error = f"preprocessing pipeline missing: {self._pipeline_error}"

    def _load_pipeline(self, model_dir: Path) -> None:
        metadata = self._load_pipeline_metadata(model_dir)
        self._pipeline_mandatory = metadata is not None
        if not self._pipeline_mandatory:
            return
        try:
            scaler_path = self._resolve_pipeline_path(self.SCALER_ENV, model_dir / self.SCALER_FILENAME)
            pca_path = self._resolve_pipeline_path(self.PCA_ENV, model_dir / self.PCA_FILENAME)
            kmeans_path = self._resolve_pipeline_path(self.KMEANS_ENV, model_dir / self.KMEANS_FILENAME)
            self._scaler = self._load_pickle(scaler_path)
            self._pca = self._load_pickle(pca_path)
            self._kmeans = self._load_pickle(kmeans_path)
            self._pipeline_loaded = True
            self._pipeline_error = None
            self._pipeline_metadata = metadata
        except Exception as exc:
            self._pipeline_loaded = False
            self._pipeline_error = str(exc)

    def _load_pipeline_metadata(self, model_dir: Path):
        meta_path = model_dir / self.PIPELINE_META_FILENAME
        if not meta_path.exists():
            return None
        with meta_path.open('r', encoding='utf-8') as stream:
            return json.load(stream)

    def _resolve_pipeline_path(self, env_var: str, default_path: Path) -> Path:
        override_path = os.environ.get(env_var)
        if override_path:
            return Path(override_path)
        return default_path

    def _load_pickle(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"pipeline artifact missing: {path}")
        with path.open('rb') as stream:
            return pickle.load(stream)

    def _transform_feature_vector(self, features: List[float]) -> np.ndarray:
        arr = np.array([features], dtype=float)
        if not self._pipeline_loaded:
            return arr
        scaled = self._scaler.transform(arr)
        pca_out = self._pca.transform(scaled)
        cluster_ids = self._kmeans.predict(pca_out)
        cluster_col = cluster_ids.reshape(-1, 1).astype(float)
        return np.hstack([pca_out, cluster_col])

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

        if self._pipeline_mandatory and not self._pipeline_loaded:
            raise RuntimeError(f"ML preprocessing pipeline missing ({self._pipeline_error}). Please ensure the scaler/PCA/KMeans artifacts are available.")

        features = self._build_feature_vector(ap, ris, ue)
        feature_vector = self._transform_feature_vector(features)
        try:
            dmatrix = xgb.DMatrix(feature_vector)
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
        """Construct feature vector using the updated geometry trig + link metrics."""
        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)

        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))

        # Incident AoA azimuth (rad)
        aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
        aoa_sin = float(math.sin(aoa_rad))
        aoa_cos = float(math.cos(aoa_rad))

        # AP→RIS offset for trig features
        dx, dy, dz = (ris_pos - ap_pos).tolist()
        azimuth = math.atan2(dy, dx)
        elevation = math.atan2(dz, math.hypot(dx, dy))
        az_sin = float(math.sin(azimuth))
        az_cos = float(math.cos(azimuth))
        el_sin = float(math.sin(elevation))
        el_cos = float(math.cos(elevation))

        # AoD used only inside link-budget for physics metrics
        aod_rad = math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])
        aod_deg = float(np.degrees(aod_rad)) % 360

        physics_config = build_config_from_nodes(ap, ris, ue)
        metrics = compute_ris_link_metrics(ap_pos, ris_pos, ue_pos, aod_deg, physics_config)
        snr = float(metrics['snr_dB'])
        rssi = float(metrics['rssi_dBm'])

        ap_az_sin = az_sin
        ap_az_cos = az_cos
        ap_el_sin = el_sin
        ap_el_cos = el_cos
        spec_rad = 2.0 * azimuth - aoa_rad
        spec_sin = float(math.sin(spec_rad))
        spec_cos = float(math.cos(spec_rad))
        align_cos = float(az_cos * aoa_cos + az_sin * aoa_sin)
        align_sin = float(az_sin * aoa_cos - az_cos * aoa_sin)

        return [
            d_ap_ris,
            aoa_sin, aoa_cos,
            float(dx), float(dy), float(dz),
            spec_sin, spec_cos,
            align_cos, align_sin,
            snr, rssi,
        ]
