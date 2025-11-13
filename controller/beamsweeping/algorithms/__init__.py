"""Beam sweep algorithms module with auto-registration helpers."""

from ..registry import (
    get_algorithm_class,
    list_available_names,
    list_registered_algorithms,
    register_algorithm,
)
from .linear_brute_force import LinearBruteForceSweep
from .coarse_fine_sweep import CoarseFineSweep
from .directional_exhaustive_sweep import DirectionalExhaustiveSweep
from .ml_guided_sweep import MLGuidedSweep

__all__ = [
    "LinearBruteForceSweep",
    "CoarseFineSweep",
    "MLGuidedSweep",
    "DirectionalExhaustiveSweep",
    "register_algorithm",
    "get_algorithm_class",
    "list_registered_algorithms",
    "list_available_names",
]
