"""Base classes for machine-learning beam sweep predictors."""

from abc import ABC, abstractmethod
from typing import List, Optional


class SweepMLPredictor(ABC):
    """Interface for ML-based beam guidance."""

    def __init__(self, network):
        self.network = network

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-friendly predictor name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of the predictor."""
        raise NotImplementedError

    @abstractmethod
    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        """Return local beam angles (degrees) to prioritize."""
        raise NotImplementedError
