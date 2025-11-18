"""CLI helper utilities for topology management and network I/O"""

import json
import math
import os
import numpy as np


def sanitize_for_json(value):
    """Convert numpy/native structures into JSON-safe representations."""
    if value is None:
        return None

    if isinstance(value, (bool, str)):
        return value

    if isinstance(value, (int,)):
        return int(value)

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)

    # numpy scalar types
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        val = float(value)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, np.ndarray):
        return [sanitize_for_json(v) for v in value.tolist()]

    if isinstance(value, dict):
        return {str(k): sanitize_for_json(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_json(v) for v in value]

    # Fallback to string representation for unsupported types
    return str(value)


class TopologyHelper:
    """Helper for topology management and visualization"""

    def __init__(self, net):
        self.net = net
        self.type_counters = {'ap': 0, 'ris': 0, 'ue': 0}

    def generate_auto_name(self, node_type):
        """Generate automatic node name based on type"""
        type_map = {'ap': 'AP', 'ris': 'R', 'ue': 'UE'}
        type_name = type_map.get(node_type, node_type.upper())

        # Count nodes of this type
        type_class_map = {
            'ap': 'AccessPoint',
            'ris': 'RIS',
            'ue': 'UE'
        }
        class_name = type_class_map.get(node_type)
        if class_name:
            type_count = sum(1 for n in self.net.nodes.values() if type(n).__name__ == class_name)
            return f"{type_name}{type_count + 1}"
        return f"{type_name}1"

    def generate_position(self, node_type, max_angle_deg=60.0, distance_range=(5, 15)):
        """Generate random position with optional RIS-aware placement."""
        ris_nodes = [n for n in self.net.nodes.values() if type(n).__name__ == 'RIS']

        if node_type == 'ue' and len(ris_nodes) == 1:
            # Focused single-RIS support: keep UE within that RIS FOV
            ris = ris_nodes[0]
            ris_x, ris_y = ris.pos[0], ris.pos[1]
            ris_normal = getattr(ris, 'normal_angle_deg', 0.0)
            ris_fov = getattr(ris, 'max_angle_deg', max_angle_deg)

            angle_deg = np.random.uniform(ris_normal - ris_fov, ris_normal + ris_fov)
            angle_rad = np.radians(angle_deg)
            distance = np.random.uniform(distance_range[0], distance_range[1])

            x = ris_x + distance * np.cos(angle_rad)
            y = ris_y + distance * np.sin(angle_rad)
            return x, y

        if not ris_nodes:
            # No RIS yet, generate unconstrained position
            x = np.random.uniform(0, 15)
            y = np.random.uniform(0, 15)
            return x, y

        # Default legacy behavior: reference first RIS for angle-relative placement
        ris = ris_nodes[0]
        ris_x, ris_y = ris.pos[0], ris.pos[1]
        angle_deg = np.random.uniform(-max_angle_deg, max_angle_deg)
        angle_rad = np.radians(angle_deg)
        distance = np.random.uniform(distance_range[0], distance_range[1])
        x = ris_x + distance * np.cos(angle_rad)
        y = ris_y + distance * np.sin(angle_rad)
        return x, y

    def print_topology(self):
        """Print ASCII topology view"""
        if not self.net.nodes:
            print("Network is empty")
            return

        nodes = self.net.nodes
        positions = {name: node.pos for name, node in nodes.items()}

        # Get bounds
        if not positions:
            return

        xs = [pos[0] for pos in positions.values()]
        ys = [pos[1] for pos in positions.values()]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        # Add padding
        x_range = max(x_max - x_min, 1.0)
        y_range = max(y_max - y_min, 1.0)

        x_min -= x_range * 0.1
        x_max += x_range * 0.1
        y_min -= y_range * 0.1
        y_max += y_range * 0.1

        x_range = x_max - x_min
        y_range = y_max - y_min

        # Scale to fit in 50x20 character grid
        width, height = 50, 20
        x_scale = (width - 2) / x_range if x_range > 0 else 1
        y_scale = (height - 2) / y_range if y_range > 0 else 1

        # Create mapping from node name to character
        name_to_char = {}
        char_index = 0
        char_pool = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

        for name in sorted(nodes.keys()):
            if char_index < len(char_pool):
                name_to_char[name] = char_pool[char_index]
                char_index += 1
            else:
                name_to_char[name] = "?"

        # Create grid
        grid = [[None for _ in range(width)] for _ in range(height)]

        # Place nodes on grid
        node_positions = {}
        for name, pos in positions.items():
            node = nodes[name]

            x_char = int((pos[0] - x_min) * x_scale + 1)
            y_char = int((y_max - pos[1]) * y_scale + 1)

            x_char = max(1, min(x_char, width - 2))
            y_char = max(1, min(y_char, height - 2))

            grid[y_char][x_char] = name
            node_positions[name] = (x_char, y_char)

        # Print topology
        print("\nTopology View (ASCII):")
        print("=" * 52)

        # Print legend
        legend = "Legend: "
        for name in sorted(nodes.keys()):
            legend += f"{name_to_char[name]}={name}  "
        print(legend)
        print("-" * 52)

        for row in grid:
            line = "| "
            for cell in row:
                if cell is None:
                    line += "."
                else:
                    line += name_to_char[cell]
            line += " |"
            print(line)

        print("-" * 52)

        # Print coordinate info
        print("\nNode Coordinates:")
        print(f"{'Name':<12} {'Type':<15} {'Position (x,y,z)':<25}")
        print("-" * 52)
        for name in sorted(nodes.keys()):
            node = nodes[name]
            node_type = type(node).__name__
            x, y, z = node.pos[0], node.pos[1], node.pos[2]
            print(f"{name:<12} {node_type:<15} ({x:6.2f}, {y:6.2f}, {z:6.2f})")
        print("=" * 52)


class NetworkIO:
    """Handle network save/load operations"""

    def save(self, net, filepath):
        """Save network state to JSON file"""
        network_data = {'nodes': []}

        for name, node in net.nodes.items():
            node_type = type(node).__name__
            node_info = {
                'name': name,
                'type': node_type,
                'pos': list(node.pos)
            }

            if node_type == 'AccessPoint':
                node_info['power_dBm'] = node.power_dBm
                node_info['freq'] = getattr(node, 'freq', 5.8e9)
                node_info['bandwidth_MHz'] = getattr(node, 'bandwidth_MHz', 100.0)
                node_info['antenna_gain_dBi'] = getattr(node, 'antenna_gain_dBi', 3.0)
                node_info['noise_figure_dB'] = getattr(node, 'noise_figure_dB', 6.0)
            elif node_type == 'RIS':
                node_info['N'] = node.N
                node_info['bits'] = node.bits
                node_info['freq'] = getattr(node, 'freq', 10e9)
                node_info['max_angle_deg'] = getattr(node, 'max_angle_deg', 60.0)
                node_info['normal_angle_deg'] = getattr(node, 'normal_angle_deg', 0.0)
                node_info['current_beam_angle'] = sanitize_for_json(getattr(node, 'current_beam_angle', None))

                def _phase_matrix(values, to_degrees=False):
                    if values is None:
                        return None
                    arr = np.array(values, dtype=float).reshape(node.N, node.N)
                    if to_degrees:
                        arr = np.degrees(arr)
                    return sanitize_for_json(arr.tolist())

                node_info['current_phases_deg'] = _phase_matrix(getattr(node, 'current_phases', None), to_degrees=True)
                node_info['quantized_phases_deg'] = _phase_matrix(getattr(node, 'quantized_phases', None), to_degrees=True)
                if getattr(node, 'phase_states', None) is not None:
                    states_arr = np.array(node.phase_states).reshape(node.N, node.N)
                    node_info['phase_states'] = sanitize_for_json(states_arr.tolist())
            elif node_type == 'UE':
                node_info['antenna_gain_dBi'] = getattr(node, 'antenna_gain_dBi', 3.0)
                node_info['noise_figure_dB'] = getattr(node, 'noise_figure_dB', 6.0)
                node_info['max_angle_deg'] = getattr(node, 'max_angle_deg', 180.0)
                node_info['normal_angle_deg'] = getattr(node, 'normal_angle_deg', 0.0)

            network_data['nodes'].append(sanitize_for_json(node_info))

        network_data['active_links'] = sanitize_for_json(getattr(net, 'active_links', {}))
        network_data['results'] = {
            'connect': sanitize_for_json(getattr(net, 'last_connect_result', None)),
            'sweep': sanitize_for_json(getattr(net, 'last_sweep_result', None))
        }

        with open(filepath, 'w') as f:
            json.dump(network_data, f, indent=2)

    def load(self, net, filepath):
        """Load network state from JSON file"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Network file not found: {filepath}")

        try:
            with open(filepath, 'r') as f:
                network_data = json.load(f)

            net.nodes.clear()

            # Clear active links before loading - will be repopulated if nodes exist
            if hasattr(net, 'active_links'):
                net.active_links.clear()

            results_block = network_data.get('results') or {}
            if hasattr(net, 'last_connect_result'):
                net.last_connect_result = results_block.get('connect')
            if hasattr(net, 'last_sweep_result'):
                net.last_sweep_result = results_block.get('sweep')

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
                    ap_node = net.get(name)
                    ap_node.bandwidth_MHz = bw
                    ap_node.freq = freq
                elif node_type == 'RIS':
                    N = node_info.get('N', 16)
                    bits = node_info.get('bits', 1)
                    freq = node_info.get('freq', 10e9)
                    max_angle = node_info.get('max_angle_deg', 60.0)
                    normal_angle = node_info.get('normal_angle_deg', 0.0)
                    net.add_ris(
                        name, x, y, z, N, bits, freq,
                        max_angle_deg=max_angle,
                        normal_angle_deg=normal_angle
                    )
                    ris_node = net.get(name)
                    ris_node.freq = freq
                    ris_node.max_angle_deg = max_angle
                    ris_node.normal_angle_deg = normal_angle
                    ris_node.current_beam_angle = node_info.get('current_beam_angle', ris_node.current_beam_angle)

                    def _restore_phase(key, radians=False):
                        data = node_info.get(key)
                        if data is None:
                            return None
                        arr = np.array(data, dtype=float)
                        if arr.size != ris_node.N * ris_node.N:
                            return None
                        arr = arr.reshape(ris_node.N * ris_node.N)
                        if radians:
                            arr = np.radians(arr)
                        return arr

                    restored_current = _restore_phase('current_phases_deg', radians=True)
                    if restored_current is not None:
                        ris_node.current_phases = restored_current

                    restored_quantized = _restore_phase('quantized_phases_deg', radians=True)
                    if restored_quantized is not None:
                        ris_node.quantized_phases = restored_quantized

                    states_data = node_info.get('phase_states')
                    if states_data is not None:
                        states_arr = np.array(states_data, dtype=int).reshape(ris_node.N * ris_node.N)
                        ris_node.phase_states = states_arr

                elif node_type == 'UE':
                    ant_gain = node_info.get('antenna_gain_dBi', 3.0)
                    noise_fig = node_info.get('noise_figure_dB', 6.0)
                    max_angle = node_info.get('max_angle_deg', 180.0)
                    normal_angle = node_info.get('normal_angle_deg', 0.0)
                    net.add_ue(
                        name, x, y, z,
                        antenna_gain_dBi=ant_gain,
                        noise_figure_dB=noise_fig,
                        max_angle_deg=max_angle,
                        normal_angle_deg=normal_angle
                    )

            # Restore active_links only if nodes were successfully loaded
            # This prevents stale links from being restored on empty topologies
            if net.nodes and hasattr(net, 'active_links'):
                net.active_links = network_data.get('active_links', {})

        except Exception as e:
            print(f"Warning: Failed to load network from {filepath}: {e}")
