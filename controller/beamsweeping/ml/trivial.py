"""Fallback predictor that always centers on UE direction."""

from typing import List
from .base import SweepMLPredictor


class ZeroOffsetPredictor(SweepMLPredictor):
    """Deterministic prior: always start at 0° (UE direction)."""

    @property
    def name(self) -> str:
        return "Zero-Offset Prior"

    @property
    def description(self) -> str:
        return "Always test the UE direction (0° local) first."

    def predict_local_angles(
        self,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        fov: float,
        top_k: int = 3
    ) -> List[float]:
        # Trivial starting point; real models can override this behaviour.
        return [0.0]
