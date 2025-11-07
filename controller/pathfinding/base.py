"""
Base class for pathfinding algorithms

All pathfinding algorithms should inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List
import numpy as np


class PathfindingAlgorithm(ABC):
    """Base class for pathfinding algorithms"""

    name = "base"  # Override in subclass
    description = "Base algorithm"  # Override in subclass

    @staticmethod
    @abstractmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray]) -> Dict:
        """Find path from source to target

        Args:
            graph: Adjacency dict {node: {neighbor: weight}}
            source: Source node name
            target: Target node name
            node_positions: Dict of node positions

        Returns:
            Dict with 'path', 'totalLoss', 'totalLength'
        """
        pass

    @classmethod
    def get_info(cls):
        """Get algorithm information"""
        return {
            'name': cls.name,
            'description': cls.description
        }
