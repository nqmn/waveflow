"""VAE-encoded features with XGBoost regression for beam prediction."""

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
    import torch
    import torch.nn as nn
except ImportError:
    torch = None
    nn = None

try:
    import xgboost as xgb
except ImportError:
    xgb = None

try:
    import joblib
except ImportError:
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


class VXGBPredictor(SweepMLPredictor):
    """Predict deflection angles via VAE encoder + XGBoost regressor.

    Combines VAE latent space encoding with XGBoost for improved angle prediction.
    """

    VAE_MODEL_ENV = "RISNET_VXGB_VAE_MODEL"
    XGB_MODEL_ENV = "RISNET_VXGB_XGB_MODEL"
    DEFAULT_VAE_MODEL = Path("controller/beamsweeping/ml/models/vxgb_vae.pth")
    DEFAULT_XGB_MODEL = Path("controller/beamsweeping/ml/models/vxgb_xgb.json")
    SCALER_FILENAME = "vxgb_scaler.pkl"
    PCA_FILENAME = "vxgb_pca.pkl"
    KMEANS_FILENAME = "vxgb_kmeans.pkl"
    PIPELINE_META_FILENAME = "vxgb_pipeline.json"

    SCALER_ENV = "RISNET_VXGB_SCALER"
    PCA_ENV = "RISNET_VXGB_PCA"
    KMEANS_ENV = "RISNET_VXGB_KMEANS"

    def __init__(self, network):
        super().__init__(network)
        self._vae: Optional[VAE] = None
        self._booster: Optional[xgb.Booster] = None
        self._device = None
        self._vae_error = None
        self._xgb_error = None
        self._scaler = None
        self._pca = None
        self._kmeans = None
        self._pipeline_loaded = False
        self._load_models()

    @property
    def name(self) -> str:
        return "VAE-XGBoost Beam Prior"

    @property
    def description(self) -> str:
        if self._vae is None or self._booster is None:
            vae_status = "OK" if self._vae is not None else f"Error: {self._vae_error}"
            xgb_status = "OK" if self._booster is not None else f"Error: {self._xgb_error}"
            return f"VAE-XGBoost predictor (VAE: {vae_status}, XGB: {xgb_status})"
        return "Predicts angles by encoding features through VAE, then regressing with XGBoost."

    def _load_models(self):
        if torch is None:
            self._vae_error = "torch not installed"
        else:
            self._load_vae()

        if xgb is None:
            self._xgb_error = "xgboost package not installed"
        else:
            self._load_xgb()

    def _load_vae(self):
        vae_path_str = os.environ.get(self.VAE_MODEL_ENV)
        if vae_path_str:
            vae_candidate = Path(vae_path_str)
        else:
            vae_candidate = self.DEFAULT_VAE_MODEL

        if not vae_candidate.exists():
            self._vae_error = f"VAE model file not found ({vae_candidate})"
            return

        try:
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            checkpoint = torch.load(vae_candidate, map_location=self._device)
            hyperparams = checkpoint.get("hyperparams", {"input_dim": 10, "latent_dim": 6, "hidden_dim": 64})
            self._vae = VAE(
                input_dim=hyperparams["input_dim"],
                latent_dim=hyperparams["latent_dim"],
                hidden_dim=hyperparams["hidden_dim"]
            )
            self._vae.load_state_dict(checkpoint["vae_state_dict"])
            self._vae.to(self._device)
            self._vae.eval()
            self._vae_error = None
        except Exception as exc:
            self._vae_error = f"failed to load VAE model: {exc}"
            self._vae = None

    def _load_xgb(self):
        xgb_path_str = os.environ.get(self.XGB_MODEL_ENV)
        if xgb_path_str:
            xgb_candidate = Path(xgb_path_str)
        else:
            xgb_candidate = self.DEFAULT_XGB_MODEL

        if not xgb_candidate.exists():
            self._xgb_error = f"XGB model file not found ({xgb_candidate})"
            return

        try:
            self._booster = xgb.Booster()
            self._booster.load_model(str(xgb_candidate))
            self._xgb_error = None
            self._load_pipeline(xgb_candidate.parent)
        except Exception as exc:
            self._xgb_error = f"failed to load XGB model: {exc}"
            self._booster = None

    def _load_pipeline(self, model_dir: Path) -> None:
        metadata = self._load_pipeline_metadata(model_dir)
        if metadata is None:
            return

        try:
            scaler_path = self._resolve_pipeline_path(self.SCALER_ENV, model_dir / self.SCALER_FILENAME)
            pca_path = self._resolve_pipeline_path(self.PCA_ENV, model_dir / self.PCA_FILENAME)
            kmeans_path = self._resolve_pipeline_path(self.KMEANS_ENV, model_dir / self.KMEANS_FILENAME)
            self._scaler = self._load_pickle(scaler_path)
            self._pca = self._load_pickle(pca_path)
            self._kmeans = self._load_pickle(kmeans_path)
            self._pipeline_loaded = True
        except Exception as exc:
            self._pipeline_loaded = False

    def _load_pipeline_metadata(self, model_dir: Path):
        meta_path = model_dir / self.PIPELINE_META_FILENAME
        if not meta_path.exists():
            return None
        try:
            with meta_path.open('r', encoding='utf-8') as stream:
                return json.load(stream)
        except Exception:
            return None

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

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        if self._vae is None or self._booster is None:
            raise RuntimeError(
                f"VAE-XGBoost model not available: VAE={self._vae_error}, XGB={self._xgb_error}"
            )

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
            _, _, _, z = self._vae(obs_tensor)
            z_np = z.cpu().numpy()[0]

        vae_features = np.array([z_np], dtype=float)
        try:
            dmatrix = xgb.DMatrix(vae_features)
            pred = float(self._booster.predict(dmatrix)[0])
        except Exception as e:
            raise RuntimeError(f"XGBoost prediction failed: {e}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _build_observed_features(
        self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
        ap, ris, ue
    ) -> np.ndarray:
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

    def _compute_link_metrics(
        self, ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray,
        ap, ris, ue
    ) -> tuple:
        physics_config = build_config_from_nodes(ap, ris, ue)
        metrics = compute_ris_link_metrics(
            ap_pos, ris_pos, ue_pos,
            float(np.degrees(math.atan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])) % 360),
            physics_config
        )
        return float(metrics['snr_dB']), float(metrics['rssi_dBm'])

    def _is_model_available(self) -> bool:
        return self._vae is not None and self._booster is not None and torch is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        if not model_available:
            return 10.0
        return 2.5
