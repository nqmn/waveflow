"""Beam sweep algorithms module with auto-registration helpers."""

from ..registry import (
    get_algorithm_class,
    list_available_names,
    list_registered_algorithms,
    register_algorithm,
)
from .linear_brute_force import LinearBruteForceSweep
from .coarse_fine_sweep import CoarseFineSweep
from .directional_exhaustive_sweep import EdgeCenterSweep
from .ml_guided_sweep import MLGuidedSweep
from .hierarchical_sweep import HierarchicalSweep
from .adaptive_directional_sweep import AdaptiveDirectionalSweep
from .opencv_sweep import OpenCVVisionSweep
from .hog_sweep import HOGHumanDetectionSweep
from utils import aruco_utils


def __getattr__(name):
    """Lazy load algorithms on demand."""
    if name == "ANMLocalizationSweep":
        from .anm_localization_sweep import ANMLocalizationSweep
        return ANMLocalizationSweep
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LinearBruteForceSweep",
    "CoarseFineSweep",
    "MLGuidedSweep",
    "EdgeCenterSweep",
    "HierarchicalSweep",
    "AdaptiveDirectionalSweep",
    "OpenCVVisionSweep",
    "HOGHumanDetectionSweep",
    "ANMLocalizationSweep",
    "aruco_utils",
    "register_algorithm",
    "get_algorithm_class",
    "list_registered_algorithms",
    "list_available_names",
]
