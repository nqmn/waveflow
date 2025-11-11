"""PyTorch MLP-based beam prior."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import numpy as np

from .base import SweepMLPredictor

try:
    import torch
    import torch.nn as nn
except ImportError:  # pragma: no cover - optional dependency
    torch = None
    nn = None


class MLPNetwork(nn.Module):
    """Multi-layer perceptron for beam angle prediction."""

    def __init__(self, input_size: int = 13):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.network(x)


class MLPPredictor(SweepMLPredictor):
    """Predict local beam angles with a pretrained PyTorch MLP model."""

    MODEL_ENV = "RISNET_MLP_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/mlp_beam_predictor.pth")

    def __init__(self, network):
        super().__init__(network)
        self._model: Optional[MLPNetwork] = None
        self._X_mean = None
        self._X_std = None
        self._y_mean = None
        self._y_std = None
        self._model_path = None
        self._device = None
        self._model_error = None
        self._load_model()

    @property
    def name(self) -> str:
        return "MLP Beam Prior"

    @property
    def description(self) -> str:
        if self._model is None:
            return f"MLP predictor (Error: {self._model_error})"
        return "Predicts promising local beams using a PyTorch MLP neural network."

    def _load_model(self):
        """Attempt to load the MLP model; fallback if missing."""
        if torch is None or nn is None:
            self._model_error = "PyTorch package not installed"
            return

        self._device = torch.device("cpu")

        model_path = os.environ.get(self.MODEL_ENV)
        if model_path:
            candidate = Path(model_path)
        else:
            candidate = self.DEFAULT_MODEL

        if not candidate.exists():
            self._model_error = f"model file not found ({candidate})"
            return

        try:
            checkpoint = torch.load(str(candidate), map_location=self._device)

            # Extract normalization parameters
            self._X_mean = torch.tensor(checkpoint.get('X_mean', 0.0), dtype=torch.float32)
            self._X_std = torch.tensor(checkpoint.get('X_std', 1.0), dtype=torch.float32)
            self._y_mean = checkpoint.get('y_mean', 0.0)
            self._y_std = checkpoint.get('y_std', 1.0)

            # Reconstruct model
            input_size = checkpoint.get('input_size', 13)
            self._model = MLPNetwork(input_size=input_size)
            self._model.load_state_dict(checkpoint['model_state_dict'])
            self._model.to(self._device)
            self._model.eval()
        except Exception as exc:  # pragma: no cover - load failure
            self._model_error = f"failed to load MLP model: {exc}"
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
        if self._model is None or torch is None:
            raise RuntimeError(f"MLP model not available: {self._model_error}")

        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if not (ap and ris and ue):
            raise ValueError(f"Invalid nodes: AP={ap_name}, RIS={ris_name}, UE={ue_name}")

        features = self._build_feature_vector(ap, ris, ue)
        try:
            # Normalize features
            features_tensor = torch.tensor(features, dtype=torch.float32, device=self._device)
            features_normalized = (features_tensor - self._X_mean.to(self._device)) / (self._X_std.to(self._device) + 1e-8)

            with torch.no_grad():
                output = self._model(features_normalized.unsqueeze(0))
                pred = float(output[0, 0].cpu().numpy())
        except Exception as e:  # pragma: no cover - prediction failure
            raise RuntimeError(f"MLP prediction failed: {e}")

        pred_local = float(np.clip(pred, -fov, fov))
        return [pred_local]

    def _is_model_available(self) -> bool:
        """Check if MLP model is loaded."""
        return self._model is not None and torch is not None

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
