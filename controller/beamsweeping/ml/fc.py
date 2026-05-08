"""Fully Connected Neural Network beam predictor."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor
from utils.lightris import build_lightris_config_from_nodes, evaluate_lightris_metrics

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


class FCNet(nn.Module):
    """Simple fully connected network for angle prediction."""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 128, output_dim: int = 1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.2)

        self.fc2 = nn.Linear(hidden_dim, 64)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.2)

        self.fc3 = nn.Linear(64, 32)
        self.relu3 = nn.ReLU()

        self.output = nn.Linear(32, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.dropout1(x)

        x = self.fc2(x)
        x = self.relu2(x)
        x = self.dropout2(x)

        x = self.fc3(x)
        x = self.relu3(x)

        x = self.output(x)
        return x


class FCPredictor(SweepMLPredictor):
    """Predict beam angles using a fully connected neural network."""

    MODEL_ENV = "RISNET_FC_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/fc_beam_predictor.pth")

    def __init__(self, network):
        super().__init__(network)
        self._model: Optional[FCNet] = None
        self._model_error = None
        self._device = None
        self._load_model()

    @property
    def name(self) -> str:
        return "FC Network Beam Predictor"

    @property
    def description(self) -> str:
        if self._model is None:
            return f"FC network predictor (Error: {self._model_error})"
        return "Predicts beam angles using a fully connected neural network with 3 hidden layers."

    def _load_model(self):
        if torch is None:
            self._model_error = "torch not installed"
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
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = FCNet(input_dim=7, hidden_dim=128, output_dim=1)
            state_dict = torch.load(candidate, map_location=self._device)
            self._model.load_state_dict(state_dict)
            self._model.to(self._device)
            self._model.eval()
        except Exception as exc:  # pragma: no cover
            self._model_error = f"failed to load FC model: {exc}"
            self._model = None
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
        if self._model is None:
            raise RuntimeError(f"FC model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)
        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        try:
            with torch.no_grad():
                features_tensor = torch.tensor(features, dtype=torch.float32, device=self._device).unsqueeze(0)
                pred = float(self._model(features_tensor).cpu().numpy()[0, 0])
        except Exception as exc:
            raise RuntimeError(f"FC prediction failed: {exc}")

        pred_local = float(np.clip(pred, 0.0, fov))

        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")

        top_count = min(top_k, 1)
        return [pred_local] * top_count

    def _is_model_available(self) -> bool:
        return self._model is not None and torch is not None

    def _compute_uncertainty(self, model_available: bool) -> float:
        if not model_available:
            return 10.0
        return 2.5

    def _build_feature_vector(self, ap, ris, ue) -> List[float]:
        ap_pos = np.array(ap.pos)
        ris_pos = np.array(ris.pos)
        ue_pos = np.array(ue.pos)

        d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))

        aoa_rad = math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0])
        aoa_sin = float(math.sin(aoa_rad))
        aoa_cos = float(math.cos(aoa_rad))

        # Compute elevation angle from AP-RIS geometry
        dx = ris_pos[0] - ap_pos[0]
        dy = ris_pos[1] - ap_pos[1]
        dz = ris_pos[2] - ap_pos[2]
        d_xy = math.hypot(dx, dy)
        el_rad = math.atan2(dz, d_xy)
        el_sin = float(math.sin(el_rad))
        el_cos = float(math.cos(el_rad))

        aod_deg = float(np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))) % 360

        physics_config = build_lightris_config_from_nodes(ap, ris, ue)
        metrics = evaluate_lightris_metrics(ap_pos, ris_pos, ue_pos, aod_deg, physics_config)
        snr = float(metrics['snr_dB'])
        rssi = float(metrics['rssi_dBm'])

        return [snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos]
