"""
Thread-safe wrapper for RISNetwork and RISController
Adds locking to prevent concurrent access issues in web mode
"""

import threading
from typing import Dict, List, Optional
from core import RISNetwork
from controller.ris_controller import RISController


class ThreadSafeNetwork:
    """Thread-safe wrapper around RISNetwork"""

    def __init__(self, network: RISNetwork):
        """Wrap a RISNetwork with a lock

        Args:
            network: RISNetwork instance to protect
        """
        self._network = network
        self._lock = threading.RLock()  # Reentrant lock for nested calls

    def _execute(self, func, *args, **kwargs):
        """Execute function with lock held"""
        with self._lock:
            return func(*args, **kwargs)

    # Delegated read-only operations
    def get(self, name):
        """Get node by name (thread-safe)"""
        with self._lock:
            return self._network.get(name)

    def get_nodes_dict(self):
        """Get all nodes as dict (thread-safe)"""
        with self._lock:
            return self._network.get_nodes_dict()

    def list_nodes(self):
        """List all nodes (thread-safe)"""
        with self._lock:
            return list(self._network.nodes.keys())

    # Delegated write operations
    def add_ap(self, *args, **kwargs):
        """Add AP (thread-safe)"""
        with self._lock:
            return self._network.add_ap(*args, **kwargs)

    def add_ris(self, *args, **kwargs):
        """Add RIS (thread-safe)"""
        with self._lock:
            return self._network.add_ris(*args, **kwargs)

    def add_ue(self, *args, **kwargs):
        """Add UE (thread-safe)"""
        with self._lock:
            return self._network.add_ue(*args, **kwargs)

    def remove_node(self, name: str):
        """Remove node (thread-safe)"""
        with self._lock:
            return self._network.remove_node(name)

    def update_node_position(self, name: str, x: float, y: float, z: float = 0.0):
        """Update node position (thread-safe)"""
        with self._lock:
            return self._network.update_node_position(name, x, y, z)

    def connect(self, *args, **kwargs):
        """Connect nodes (thread-safe)"""
        with self._lock:
            return self._network.connect(*args, **kwargs)

    def sweep(self, *args, **kwargs):
        """Perform beam sweep (thread-safe)"""
        with self._lock:
            return self._network.sweep(*args, **kwargs)

    def add_wall(self, *args, **kwargs):
        """Add wall (thread-safe)"""
        with self._lock:
            return self._network.add_wall(*args, **kwargs)

    def clear_walls(self):
        """Clear walls (thread-safe)"""
        with self._lock:
            return self._network.clear_walls()

    def set_impairments(self, data: Dict):
        """Set impairments (thread-safe)"""
        with self._lock:
            return self._network.set_impairments(data)

    def set_controller(self, controller):
        """Set controller (thread-safe)"""
        with self._lock:
            return self._network.set_controller(controller)

    # Properties
    @property
    def nodes(self):
        """Access nodes dict (requires lock acquisition by caller)"""
        return self._network.nodes

    @property
    def environment(self):
        """Access environment"""
        return self._network.environment

    @property
    def impairments(self):
        """Access impairments"""
        return self._network.impairments

    @property
    def _controller(self):
        """Access controller"""
        return self._network._controller


class ThreadSafeController:
    """Thread-safe wrapper around RISController"""

    def __init__(self, controller: RISController):
        """Wrap a RISController with a lock

        Args:
            controller: RISController instance to protect
        """
        self._controller = controller
        self._lock = threading.RLock()

    def find_all_paths(self, *args, **kwargs):
        """Find all paths (thread-safe)"""
        with self._lock:
            return self._controller.find_all_paths(*args, **kwargs)

    def select_best_path(self, *args, **kwargs):
        """Select best path (thread-safe)"""
        with self._lock:
            return self._controller.select_best_path(*args, **kwargs)

    def set_algorithm(self, algorithm: str):
        """Set pathfinding algorithm (thread-safe)"""
        with self._lock:
            self._controller.algorithm = algorithm

    def set_strategy(self, strategy: str):
        """Set selection strategy (thread-safe)"""
        with self._lock:
            self._controller.strategy = strategy

    def enable(self):
        """Enable controller (thread-safe)"""
        with self._lock:
            self._controller.enabled = True

    def disable(self):
        """Disable controller (thread-safe)"""
        with self._lock:
            self._controller.enabled = False

    @property
    def stats(self):
        """Get controller stats (thread-safe)"""
        with self._lock:
            return self._controller.stats.copy()

    @property
    def enabled(self):
        """Check if controller is enabled"""
        with self._lock:
            return self._controller.enabled

    @property
    def algorithm(self):
        """Get current algorithm"""
        with self._lock:
            return self._controller.algorithm

    @property
    def strategy(self):
        """Get current strategy"""
        with self._lock:
            return self._controller.strategy
