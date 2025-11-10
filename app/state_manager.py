"""
State persistence manager for web API
Handles saving and loading network state to disk
"""

import json
import os
from typing import Dict, Optional


class WebStateManager:
    """Manage network state persistence for web mode"""

    # Default state file location
    DEFAULT_STATE_FILE = '.risnet_web_state.json'

    def __init__(self, state_file: str = None):
        """Initialize state manager

        Args:
            state_file: Path to state file (default: .risnet_web_state.json)
        """
        self.state_file = state_file or self.DEFAULT_STATE_FILE

    def save_network(self, net) -> bool:
        """Save network state to disk

        Args:
            net: RISNetwork instance (or ThreadSafeNetwork wrapper)

        Returns:
            True if successful, False otherwise
        """
        try:
            network_data = {'nodes': []}

            # Access the underlying network if it's a wrapper
            nodes = net.nodes if hasattr(net, 'nodes') else net._network.nodes

            for name, node in nodes.items():
                node_type = type(node).__name__
                node_info = {
                    'name': name,
                    'type': node_type,
                    'pos': list(node.pos)
                }

                if node_type == 'AccessPoint':
                    node_info['power_dBm'] = getattr(node, 'power_dBm', 20.0)
                    node_info['freq'] = getattr(node, 'freq', 5.8e9)
                    node_info['bandwidth_MHz'] = getattr(node, 'bandwidth_MHz', 20.0)
                    node_info['antenna_gain_dBi'] = getattr(node, 'antenna_gain_dBi', 3.0)
                    node_info['noise_figure_dB'] = getattr(node, 'noise_figure_dB', 6.0)

                elif node_type == 'RIS':
                    node_info['N'] = getattr(node, 'N', 16)
                    node_info['bits'] = getattr(node, 'bits', 2)
                    node_info['freq'] = getattr(node, 'freq', 10e9)
                    node_info['max_angle_deg'] = getattr(node, 'max_angle_deg', 60.0)

                elif node_type == 'UE':
                    node_info['antenna_gain_dBi'] = getattr(node, 'antenna_gain_dBi', 3.0)
                    node_info['noise_figure_dB'] = getattr(node, 'noise_figure_dB', 6.0)

                network_data['nodes'].append(node_info)

            # Write to file
            with open(self.state_file, 'w') as f:
                json.dump(network_data, f, indent=2)

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
            with open(self.state_file, 'r') as f:
                network_data = json.load(f)

            # Clear existing nodes
            net.nodes.clear() if hasattr(net, 'nodes') else net._network.nodes.clear()

            # Load nodes
            for node_info in network_data.get('nodes', []):
                node_type = node_info['type']
                name = node_info['name']
                x, y, z = node_info['pos']

                if node_type == 'AccessPoint':
                    power = node_info.get('power_dBm', 20.0)
                    freq = node_info.get('freq', 5.8e9)
                    bw = node_info.get('bandwidth_MHz', 20.0)
                    ant_gain = node_info.get('antenna_gain_dBi', 3.0)
                    noise_fig = node_info.get('noise_figure_dB', 6.0)
                    net.add_ap(
                        name, x, y, z, power, freq, bw,
                        antenna_gain_dBi=ant_gain,
                        noise_figure_dB=noise_fig
                    )

                elif node_type == 'RIS':
                    N = node_info.get('N', 16)
                    bits = node_info.get('bits', 2)
                    freq = node_info.get('freq', 10e9)
                    max_angle = node_info.get('max_angle_deg', 60.0)
                    net.add_ris(
                        name, x, y, z, N, bits, freq,
                        max_angle_deg=max_angle
                    )

                elif node_type == 'UE':
                    ant_gain = node_info.get('antenna_gain_dBi', 3.0)
                    noise_fig = node_info.get('noise_figure_dB', 6.0)
                    net.add_ue(
                        name, x, y, z,
                        antenna_gain_dBi=ant_gain,
                        noise_figure_dB=noise_fig
                    )

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
