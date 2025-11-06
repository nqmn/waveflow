"""
Algorithm modules for RIS optimization

Algorithms are auto-discovered from this package.
Add new algorithms by creating a new file with a PathfindingAlgorithm subclass.
"""

from .base import PathfindingAlgorithm
from .beamforming import BeamformingEngine
from .registry import get_registry, get_algorithm, list_algorithms

# Legacy support - keep PathfindingEngine for backwards compatibility
from .pathfinding import PathfindingEngine

__all__ = [
    'PathfindingAlgorithm',
    'BeamformingEngine',
    'PathfindingEngine',  # Legacy
    'get_registry',
    'get_algorithm',
    'list_algorithms'
]
