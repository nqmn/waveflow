"""
Pathfinding algorithms for RIS network routing

Available algorithms:
- dijkstra: Optimal path (SNR-weighted shortest path)
- astar: Heuristic-guided search
- greedy: Fast greedy nearest-neighbor
- exhaustive: Brute-force all paths (small networks only)

Usage:
    from controller.pathfinding import get_algorithm, list_algorithms
    algo = get_algorithm('dijkstra')
    result = algo.find_path(graph, source, target, positions)
"""

from .base import PathfindingAlgorithm
from .registry import get_registry, get_algorithm, list_algorithms
from .engine import PathfindingEngine

__all__ = [
    'PathfindingAlgorithm',
    'PathfindingEngine',
    'get_registry',
    'get_algorithm',
    'list_algorithms',
]
