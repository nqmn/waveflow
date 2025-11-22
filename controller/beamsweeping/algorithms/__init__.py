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
from .prime_sweep import PRIMELocalizationSweep


def __getattr__(name):
    """Lazy load algorithms and utilities on demand."""
    if name == "ANMLocalizationSweep":
        from .prime_sweep import PRIMELocalizationSweep
        return PRIMELocalizationSweep
    elif name == "aruco_utils":
        from utils import aruco_utils
        return aruco_utils
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
    "PRIMELocalizationSweep",
    "aruco_utils",
    "register_algorithm",
    "get_algorithm_class",
    "list_registered_algorithms",
    "list_available_names",
]
