"""Variational Autoencoder with Gaussian Mixture-based beam prior."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor
from utils.link_budget import build_config_from_nodes, compute_ris_link_metrics

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - optional dependency
    torch = None
    nn = None

try:
    import joblib
except ImportError:  # pragma: no cover - optional dependency
    joblib = None


class VAE(nn.Module):
    """Variational Autoencoder for learning latent representation of beam features."""

    def __init__(self, input_dim: int = 10, latent_dim: int = 4, hidden_dim: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z)
        return recon_x, mu, logvar, z


class VGMFPredictor(SweepMLPredictor):
    """Predict deflection angles via Variational Autoencoder + Gaussian Mixture."""

    VAE_MODEL_ENV = "RISNET_VGMF_VAE_MODEL"
    GMM_MODEL_ENV = "RISNET_VGMF_GMM_MODEL"
    DEFAULT_VAE_MODEL = Path("controller/beamsweeping/ml/models/vgmf_vae.pth")
    DEFAULT_GMM_MODEL = Path("controller/beamsweeping/ml/models/vgmf_gmm.pkl")

    def __init__(self, network):
        super().__init__(network)
        self._vae: Optional[VAE] = None
        self._gmm = None
        self._device = None
        self._vae_error = None
        self._gmm_error = None
        self._load_models()

    @property
    def name(self) -> str:
        return "VAE-GMM Fingerprint Prior"

    @property
    def description(self) -> str:
        if self._vae is None or self._gmm is None:
            vae_status = "OK" if self._vae is not None else f"Error: {self._vae_error}"
            gmm_status = "OK" if self._gmm is not None else f"Error: {self._gmm_error}"
            return f"VAE-GMM predictor (VAE: {vae_status}, GMM: {gmm_status})"
        return "Predicts beams by encoding features through VAE, then conditioning a Gaussian Mixture on latent space."

    def _load_models(self):
        if torch is None:
            self._vae_error = "torch not installed"
            return

        if joblib is None:
            self._gmm_error = "joblib not installed"
            return

        vae_path_str = os.environ.get(self.VAE_MODEL_ENV)
        if vae_path_str:
            vae_candidate = Path(vae_path_str)
        else:
            vae_candidate = self.DEFAULT_VAE_MODEL

        gmm_path_str = os.environ.get(self.GMM_MODEL_ENV)
        if gmm_path_str:
            gmm_candidate = Path(gmm_path_str)
        else:
            gmm_candidate = self.DEFAULT_GMM_MODEL

        if not vae_candidate.exists():
            self._vae_error = f"VAE model file not found ({vae_candidate})"
        else:
            try:
                self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                checkpoint = torch.load(vae_candidate, map_location=self._device)
                hyperparams = checkpoint.get("hyperparams", {"input_dim": 10, "latent_dim": 6, "hidden_dim": 64})
                self._vae = VAE(input_dim=hyperparams["input_dim"], latent_dim=hyperparams["latent_dim"],
                               hidden_dim=hyperparams["hidden_dim"])
                self._vae.load_state_dict(checkpoint["vae_state_dict"])
                self._vae.to(self._device)
                self._vae.eval()
                self._vae_error = None
            except Exception as exc:  # pragma: no cover
                self._vae_error = f"failed to load VAE model: {exc}"
                self._vae = None

        if not gmm_candidate.exists():
            self._gmm_error = f"GMM model file not found ({gmm_candidate})"
        else:
            try:
                self._gmm = joblib.load(gmm_candidate)
                self._gmm_error = None
            except Exception as exc:  # pragma: no cover
                self._gmm_error = f"failed to load GMM model: {exc}"
                self._gmm = None

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        if self._vae is None or self._gmm is None:
            raise RuntimeError(f"VAE-GMM model not available: VAE={self._vae_error}, GMM={self._gmm_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)
        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)

        obs = self._build_observed_features(ap_pos, ris_pos, ue_pos, ap, ris, ue)

        with torch.no_grad():
            obs_tensor = torch.tensor(obs, dtype=torch.float32, device=self._device).unsqueeze(0)
            mu, _ = self._vae.encode(obs_tensor)
            z_np = mu.cpu().numpy()[0]

        angle_grid = np.linspace(0.0, 360.0, 360, dtype=float)
        angles_rad = np.radians(angle_grid)
        angle_sin = np.sin(angles_rad)
        angle_cos = np.cos(angles_rad)

        z_matrix = np.repeat(z_np[np.newaxis, :], 360, axis=0)
        samples = np.hstack([z_matrix, angle_sin.reshape(-1, 1), angle_cos.reshape(-1, 1)])

        log_likelihoods = self._gmm.score_samples(samples)
        log_likelihoods -= float(np.max(log_likelihoods))
        posterior = np.exp(log_likelihoods)
        posterior /= float(np.sum(posterior))

        angle_fov_grid = np.linspace(0.0, fov, max(2, int(fov) + 1), dtype=float)
        angle_fov_indices = np.searchsorted(angle_grid, angle_fov_grid).clip(0, 359)
        angle_posteriors = posterior[angle_fov_indices]

        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        sorted_indices = np.argsort(angle_posteriors)[::-1]
        top_count = min(top_k, len(angle_fov_grid))
        top_angles = angle_fov_grid[sorted_indices[:top_count]]

        return [float(angle) for angle in top_angles]

    def _build_observed_features(self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
                                ap, ris, ue) -> np.ndarray:
        """Construct the observed feature vector for VAE encoding."""
        snr, rssi = self._compute_link_metrics(ap_pos, ris_pos, ue_pos, ap, ris, ue)
        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))
        aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
        aoa_sin = float(math.sin(aoa_rad))
        aoa_cos = float(math.cos(aoa_rad))

        dx = ris_pos[0] - ap_pos[0]
        dy = ris_pos[1] - ap_pos[1]
        dz = ris_pos[2] - ap_pos[2]
        d_xy = math.hypot(dx, dy)
        el_rad = math.atan2(dz, d_xy)
        el_sin = float(math.sin(el_rad))
        el_cos = float(math.cos(el_rad))

        return np.array([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, float(dx), float(dy), float(dz)], dtype=float)

    def _compute_link_metrics(self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
                             ap, ris, ue) -> tuple:
        physics_config = build_config_from_nodes(ap, ris, ue)
        metrics = compute_ris_link_metrics(ap_pos, ris_pos, ue_pos,
                                          float(np.degrees(math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])) % 360),
                                          physics_config)
        return float(metrics['snr_dB']), float(metrics['rssi_dBm'])

    def _is_model_available(self) -> bool:
        return self._vae is not None and self._gmm is not None and torch is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        if not model_available:
            return 10.0
        return 3.0
