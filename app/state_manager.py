"""
State persistence manager for web API
Handles saving and loading network state to disk
"""

import os

from cli.helpers import NetworkIO


class WebStateManager:
    """Manage network state persistence for web mode"""

    # Default state file location
    DEFAULT_STATE_FILE = '.risnet_web_state.json'

    def __init__(self, state_file: str = None, network_io: NetworkIO = None):
        """Initialize state manager

        Args:
            state_file: Path to state file (default: .risnet_web_state.json)
        """
        self.state_file = state_file or self.DEFAULT_STATE_FILE
        self.network_io = network_io or NetworkIO()

    @staticmethod
    def _resolve_network(net):
        """Return underlying RISNetwork for thread-safe wrappers."""
        return getattr(net, '_network', net)

    def save_network(self, net) -> bool:
        """Save network state to disk

        Args:
            net: RISNetwork instance (or ThreadSafeNetwork wrapper)

        Returns:
            True if successful, False otherwise
        """
        try:
            network = self._resolve_network(net)
            self.network_io.save(network, self.state_file)
            return True

        except Exception as e:
            print(f"Error saving network state: {e}")
            return False

    def load_network(self, net) -> bool:
        """Load network state from disk

        Args:
            net: RISNetwork instance (or ThreadSafeNetwork wrapper)

        Returns:
            True if successful, False if file doesn't exist or error
        """
        if not os.path.exists(self.state_file):
            return False  # No state file to load

        try:
            network = self._resolve_network(net)
            self.network_io.load(network, self.state_file)
            return True

        except Exception as e:
            print(f"Warning: Failed to load network state: {e}")
            return False

    def clear_state(self) -> bool:
        """Delete state file

        Returns:
            True if successful or file doesn't exist, False on error
        """
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
            return True
        except Exception as e:
            print(f"Error clearing state: {e}")
            return False
