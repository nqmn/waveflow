"""
Algorithm registry with auto-discovery

Automatically discovers and registers all algorithm classes.
"""

import importlib
import pkgutil
from typing import Dict, Type
from .base import PathfindingAlgorithm


class AlgorithmRegistry:
    """Registry for pathfinding algorithms with auto-discovery"""

    def __init__(self):
        self._algorithms: Dict[str, Type[PathfindingAlgorithm]] = {}
        self._discover_algorithms()

    def _discover_algorithms(self):
        """Auto-discover algorithm classes in the pathfinding package"""
        from . import base as pathfinding_module
        import os

        # Get the directory of this module
        current_dir = os.path.dirname(__file__)

        # List of algorithm modules to discover
        algorithm_modules = ['dijkstra', 'astar', 'greedy', 'exhaustive']

        for modname in algorithm_modules:
            if modname in ['base', 'registry', '__init__', 'engine']:
                continue  # Skip non-algorithm modules

            try:
                # Import module
                module = importlib.import_module(f'controller.pathfinding.{modname}')

                # Find PathfindingAlgorithm subclasses
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)

                    # Check if it's a class and subclass of PathfindingAlgorithm
                    if (isinstance(attr, type) and
                        issubclass(attr, PathfindingAlgorithm) and
                        attr is not PathfindingAlgorithm):

                        # Register algorithm
                        self.register(attr)

            except Exception as e:
                pass  # Silently skip modules that can't be loaded

    def register(self, algorithm_class: Type[PathfindingAlgorithm]):
        """Register an algorithm class

        Args:
            algorithm_class: Algorithm class to register
        """
        name = algorithm_class.name
        self._algorithms[name] = algorithm_class
        print(f"Registered algorithm: {name} - {algorithm_class.description}")

    def get(self, name: str) -> Type[PathfindingAlgorithm]:
        """Get algorithm by name

        Args:
            name: Algorithm name

        Returns:
            Algorithm class

        Raises:
            KeyError: If algorithm not found
        """
        if name not in self._algorithms:
            raise KeyError(f"Algorithm '{name}' not found. Available: {self.list()}")

        return self._algorithms[name]

    def list(self) -> list:
        """List all registered algorithm names"""
        return list(self._algorithms.keys())

    def get_all_info(self) -> Dict:
        """Get information about all algorithms"""
        return {
            name: algo.get_info()
            for name, algo in self._algorithms.items()
        }


# Global registry instance
_registry = None


def get_registry() -> AlgorithmRegistry:
    """Get global algorithm registry (singleton)"""
    global _registry
    if _registry is None:
        _registry = AlgorithmRegistry()
    return _registry


def get_algorithm(name: str):
    """Get algorithm by name (convenience function)"""
    return get_registry().get(name)


def list_algorithms():
    """List all available algorithms (convenience function)"""
    return get_registry().list()
