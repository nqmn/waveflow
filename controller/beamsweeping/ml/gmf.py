"""Gaussian Mixture-based beam prior."""

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


class GMFPredictor(SweepMLPredictor):
    """Predict deflection angles via Gaussian Mixture fingerprinting."""

    MODEL_ENV = "RISNET_GMF_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/gmf_beam_prior.pkl")

    def __init__(self, network):
        super().__init__(network)
        self._gmm = None
        self._model_error = None
        self._load_model()

    @property
    def name(self) -> str:
        return "GMM Fingerprint Prior"

    @property
    def description(self) -> str:
        if self._gmm is None:
            return f"GMM fingerprint predictor (Error: {self._model_error})"
        return "Predicts beams by conditioning a Gaussian Mixture on link metrics."

    def _load_model(self):
        if joblib is None:
            self._model_error = "joblib not installed"
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
            self._gmm = joblib.load(candidate)
        except Exception as exc:  # pragma: no cover
            self._model_error = f"failed to load GMM model: {exc}"
            self._gmm = None
            return

        self._model_error = None

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        if self._gmm is None:
            raise RuntimeError(f"GMM model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)
        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)
        obs = self._build_observed_features(ap_pos, ris_pos, ue_pos, ap, ris, ue)
        angle_grid, posterior = self._compute_angle_posterior(obs, fov)
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        sorted_indices = np.argsort(posterior)[::-1]
        top_count = min(top_k, len(angle_grid))
        top_angles = angle_grid[sorted_indices[:top_count]]
        return [float(angle) for angle in top_angles]

    def _compute_link_metrics(self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
                              ap, ris, ue) -> tuple:
        physics_config = build_lightris_config_from_nodes(ap, ris, ue)
        metrics = evaluate_lightris_metrics(ap_pos, ris_pos, ue_pos,
                                           float(np.degrees(math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])) % 360),
                                           physics_config)
        return float(metrics['snr_dB']), float(metrics['rssi_dBm'])

    def _build_observed_features(self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
                                 ap, ris, ue) -> np.ndarray:
        """Construct the observed feature vector expected by the GMM."""
        snr, rssi = self._compute_link_metrics(ap_pos, ris_pos, ue_pos, ap, ris, ue)
        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))
        aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
        aoa_sin = float(math.sin(aoa_rad))
        aoa_cos = float(math.cos(aoa_rad))

        # Compute elevation angle and AP-RIS offset from AP-RIS geometry
        dx = ris_pos[0] - ap_pos[0]
        dy = ris_pos[1] - ap_pos[1]
        dz = ris_pos[2] - ap_pos[2]
        d_xy = math.hypot(dx, dy)
        el_rad = math.atan2(dz, d_xy)
        el_sin = float(math.sin(el_rad))
        el_cos = float(math.cos(el_rad))

        return np.array([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, float(dx), float(dy), float(dz)], dtype=float)

    def _compute_angle_posterior(self, obs: np.ndarray, fov: float, resolution: float = 1.0) -> tuple:
        """Estimate posterior probabilities across an angle grid using the GMM."""
        if resolution <= 0:
            raise ValueError("resolution must be positive")

        count = max(2, int(np.floor(fov / resolution)) + 1)
        angle_grid = np.linspace(0.0, fov, count, dtype=float)
        angles_rad = np.radians(angle_grid)
        obs_matrix = np.repeat(obs[np.newaxis, :], len(angles_rad), axis=0)
        samples = np.hstack([obs_matrix, angles_rad.reshape(-1, 1)])

        log_likelihoods = self._gmm.score_samples(samples)
        log_likelihoods -= float(np.max(log_likelihoods))
        posterior = np.exp(log_likelihoods)
        total = float(np.sum(posterior))
        if total <= 0 or not np.isfinite(total):
            posterior = np.ones_like(posterior) / posterior.size
        else:
            posterior /= total
        return angle_grid, posterior

    def _is_model_available(self) -> bool:
        return self._gmm is not None and joblib is not None
