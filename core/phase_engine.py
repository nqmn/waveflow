"""Core phase-engine abstraction and registration helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import import_module
from typing import Any, Callable, Optional, Tuple

import numpy as np


class PhaseEngine(ABC):
    """Abstract phase-engine service used by core nodes and networks."""

    @abstractmethod
    def compute_ris_phases(
        self,
        ris: Any,
        ap_pos: np.ndarray,
        ue_pos: np.ndarray,
    ) -> Tuple[np.ndarray, dict]:
        """Compute ideal RIS phases and metadata for a RIS node."""

    @abstractmethod
    def apply_tapering(self, rows: int, cols: int, window: str = "hamming") -> np.ndarray:
        """Return element weights for the requested tapering window."""

    @abstractmethod
    def create_phase_manager(self, ris: Any) -> Any:
        """Create the compatibility phase-manager object for a RIS node."""


_phase_engine_factory: Optional[Callable[[], PhaseEngine]] = None
_phase_engine_instance: Optional[PhaseEngine] = None


def register_phase_engine_factory(factory: Callable[[], PhaseEngine]) -> None:
    """Register the global phase-engine factory."""
    global _phase_engine_factory, _phase_engine_instance
    _phase_engine_factory = factory
    _phase_engine_instance = None


def get_phase_engine() -> PhaseEngine:
    """Return the registered phase engine, bootstrapping the controller adapter if needed."""
    global _phase_engine_instance

    if _phase_engine_instance is not None:
        return _phase_engine_instance

    if _phase_engine_factory is None:
        import_module("controller.ris_phase")
        if _phase_engine_factory is None:
            raise RuntimeError("No phase engine registered")

    _phase_engine_instance = _phase_engine_factory()
    return _phase_engine_instance
