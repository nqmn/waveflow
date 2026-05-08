"""KGMF beam prior (sector classifier + GMM posterior)."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import List

import numpy as np

from .base import SweepMLPredictor
from utils.lightris import build_lightris_config_from_nodes, evaluate_lightris_metrics

try:
    import joblib
except ImportError:  # pragma: no cover - optional dependency
    joblib = None


class KGMFPredictor(SweepMLPredictor):
    """Sector-aware GMM prior."""

    MODEL_ENV = "RISNET_KGMF_GMM"
    SECTOR_ENV = "RISNET_KGMF_SECTOR_MODEL"
    DEFAULT_GMM = Path("controller/beamsweeping/ml/models/kgmf_gmm.pkl")
    DEFAULT_SECTOR = Path("controller/beamsweeping/ml/models/kgmf_sector_classifier.pkl")
    DEFAULT_SECTOR_COUNT = 18

    def __init__(self, network):
        super().__init__(network)
        self._gmm = None
        self._sector_model = None
        self._sector_count = self.DEFAULT_SECTOR_COUNT
        self._model_error = None
        self._load_models()

    @property
    def name(self) -> str:
        return "KGMF Sector+GMM Prior"

    @property
    def description(self) -> str:
        if self._gmm is None or self._sector_model is None:
            return f"KGMF predictor (Error: {self._model_error})"
        return "Predicts beams by classifying the sector, then conditioning a GMM on SNR/RSSI."

    def _load_models(self):
        if joblib is None:
            self._model_error = "joblib not installed"
            return

        gmm_path = Path(os.environ.get(self.MODEL_ENV, self.DEFAULT_GMM))
        sector_path = Path(os.environ.get(self.SECTOR_ENV, self.DEFAULT_SECTOR))

        if not gmm_path.exists():
            self._model_error = f"GMM file missing ({gmm_path})"
            return
        if not sector_path.exists():
            self._model_error = f"sector classifier missing ({sector_path})"
            return

        try:
            self._gmm = joblib.load(gmm_path)
            self._sector_model = joblib.load(sector_path)
        except Exception as exc:
            self._model_error = f"failed to load KGMF models: {exc}"
            self._gmm = None
            self._sector_model = None
            return

        if hasattr(self._sector_model, 'n_classes_'):
            self._sector_count = int(self._sector_model.n_classes_)
        else:
            self._sector_count = self.DEFAULT_SECTOR_COUNT

        self._model_error = None

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        if self._gmm is None or self._sector_model is None:
            raise RuntimeError(f"KGMF models not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)
        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        snr, rssi = self._compute_link_metrics(ap, ris, ue)
        sector = int(self._sector_model.predict([[snr, rssi]])[0])
        angle_rad = self._conditional_angle(snr, rssi)
        angle_deg = float(np.degrees(angle_rad)) % 360.0
        angle_deg = self._align_to_sector(angle_deg, sector)
        pred_local = float(np.clip(angle_deg, 0.0, fov))
        return [pred_local]

    def _align_to_sector(self, angle_deg: float, sector: int) -> float:
        width = 360.0 / self._sector_count
        center = (sector + 0.5) * width
        diff = self._wrap_angle(angle_deg - center)
        clamped = max(min(diff, width / 2), -width / 2)
        return (center + clamped) % 360.0

    def _wrap_angle(self, angle: float) -> float:
        while angle > 180.0:
            angle -= 360.0
        while angle <= -180.0:
            angle += 360.0
        return angle

    def _compute_link_metrics(self, ap, ris, ue) -> tuple:
        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)
        physics_config = build_lightris_config_from_nodes(ap, ris, ue)
        metrics = evaluate_lightris_metrics(ap_pos, ris_pos, ue_pos,
                                           float(np.degrees(math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])) % 360),
                                           physics_config)
        return float(metrics['snr_dB']), float(metrics['rssi_dBm'])

    def _conditional_angle(self, snr: float, rssi: float) -> float:
        obs = np.array([snr, rssi])
        weights = []
        conditional_means = []
        for idx in range(self._gmm.n_components):
            mean = self._gmm.means_[idx]
            cov = self._component_covariance(idx)
            mu_xy = mean[:2]
            mu_angle = mean[2]
            Sigma_xx = cov[:2, :2]
            Sigma_zx = cov[2, :2]
            try:
                Sigma_xx_inv = np.linalg.inv(Sigma_xx)
            except np.linalg.LinAlgError:
                Sigma_xx_inv = np.linalg.pinv(Sigma_xx)

            diff = obs - mu_xy
            cond_mean = mu_angle + float(Sigma_zx @ Sigma_xx_inv @ diff)
            pdf = self._gaussian_pdf(obs, mu_xy, Sigma_xx)
            weight = self._gmm.weights_[idx] * pdf
            weights.append(weight)
            conditional_means.append(cond_mean)

        weights = np.array(weights, dtype=float)
        if not np.isfinite(weights).all():
            weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)

        if weights.sum() <= 0:
            probs = np.ones_like(weights) / len(weights)
        else:
            probs = weights / weights.sum()

        return float(np.dot(probs, conditional_means))

    def _gaussian_pdf(self, x: np.ndarray, mean: np.ndarray, cov: np.ndarray) -> float:
        dim = x.shape[0]
        det = np.linalg.det(cov)
        if det <= 0:
            det = 1e-8
        try:
            inv = np.linalg.inv(cov)
        except np.linalg.LinAlgError:
            inv = np.linalg.pinv(cov)

        diff = x - mean
        exponent = -0.5 * float(diff @ inv @ diff)
        norm = np.sqrt((2 * math.pi) ** dim * det)
        return float(np.exp(exponent) / norm)

    def _component_covariance(self, idx: int) -> np.ndarray:
        cov_type = self._gmm.covariance_type
        if cov_type == 'full':
            return self._gmm.covariances_[idx]
        if cov_type == 'tied':
            return self._gmm.covariances_
        if cov_type == 'diag':
            return np.diag(self._gmm.covariances_[idx])
        if cov_type == 'spherical':
            size = self._gmm.means_.shape[1]
            return np.eye(size) * self._gmm.covariances_[idx]
        raise RuntimeError(f"Unsupported covariance type: {cov_type}")

    def _is_model_available(self) -> bool:
        return self._gmm is not None and self._sector_model is not None and joblib is not None
