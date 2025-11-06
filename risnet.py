"""
RISnet - Mininet-inspired API for RIS Network Simulation

Provides a clean, intuitive API for creating and simulating RIS networks,
similar to how Mininet works for SDN networks.

Usage:
    from risnet import RISnet, Topology

    # Create network
    net = RISnet()

    # Add nodes
    ap = net.addAP('ap1', position=(0, 0))
    ris = net.addRIS('ris1', position=(5, 0))
    ue = net.addUE('ue1', position=(10, 3))

    # Start network
    net.start()

    # Run simulations
    paths = net.findPaths(ap, ue)
    result = net.connect(ap, ris, ue)

    # Stop network
    net.stop()
"""

import sys
from typing import List, Dict, Optional, Tuple, Union
import numpy as np

from core import RISNetwork, AccessPoint, RIS, UE
from controller import RISController
from config import Config


class RISnet:
    """Main RISnet class - similar to Mininet's Mininet class

    Provides high-level API for RIS network creation and simulation.
    """

    def __init__(self, topo=None, controller=True, config=None, autoSetPos=False):
        """Initialize RISnet

        Args:
            topo: Topology object (optional)
            controller: Whether to create RIS controller
            config: Configuration dict or Config object
            autoSetPos: Automatically arrange nodes if positions not specified
        """
        self.network = RISNetwork()
        self.controller = None
        self.config = config or Config()
        self.autoSetPos = autoSetPos
        self.started = False

        # Node registry
        self.aps = {}
        self.riss = {}
        self.ues = {}

        # Build from topology if provided
        if topo:
            self.buildFromTopo(topo)

        # Create controller if requested
        if controller:
            self.controller = RISController(self.network, self.network.environment)
            self.network.set_controller(self.controller)

    def addAP(self, name, position=None, power_dBm=20.0, freq=5.8e9):
        """Add Access Point (like Mininet's addHost)

        Args:
            name: AP name
            position: (x, y) or (x, y, z) tuple
            power_dBm: Transmit power
            freq: Frequency in Hz

        Returns:
            AP node object
        """
        if position is None:
            position = self._autoPosition('ap')

        x, y = position[0], position[1]
        z = position[2] if len(position) > 2 else 0.0

        self.network.add_ap(name, x, y, z, power_dBm, freq)
        node = self.network.get(name)
        self.aps[name] = node
        return node

    def addRIS(self, name, position=None, N=16, bits=2, max_angle_deg=60):
        """Add RIS surface (like Mininet's addSwitch)

        Args:
            name: RIS name
            position: (x, y) or (x, y, z) tuple
            N: Grid size (creates N x N array)
            bits: Phase quantization bits
            max_angle_deg: Maximum steering angle

        Returns:
            RIS node object
        """
        if position is None:
            position = self._autoPosition('ris')

        x, y = position[0], position[1]
        z = position[2] if len(position) > 2 else 0.0

        self.network.add_ris(name, x, y, z, N, bits, max_angle_deg=max_angle_deg)
        node = self.network.get(name)
        self.riss[name] = node
        return node

    def addUE(self, name, position=None):
        """Add User Equipment (like Mininet's addHost)

        Args:
            name: UE name
            position: (x, y) or (x, y, z) tuple

        Returns:
            UE node object
        """
        if position is None:
            position = self._autoPosition('ue')

        x, y = position[0], position[1]
        z = position[2] if len(position) > 2 else 0.0

        self.network.add_ue(name, x, y, z)
        node = self.network.get(name)
        self.ues[name] = node
        return node

    def addWall(self, start, end, attenuation_dB=20.0):
        """Add wall/obstacle

        Args:
            start: (x, y) start position
            end: (x, y) end position
            attenuation_dB: Signal attenuation through wall

        Returns:
            Wall object
        """
        return self.network.add_wall(start, end, attenuation_dB)

    def start(self):
        """Start the network (like Mininet's start)"""
        if self.started:
            print("Network already started")
            return

        print(f"*** Starting RISnet with {len(self.aps)} APs, {len(self.riss)} RIS, {len(self.ues)} UEs")
        self.started = True
        print("*** RISnet started")

    def stop(self):
        """Stop the network (like Mininet's stop)"""
        if not self.started:
            return

        print("*** Stopping RISnet")
        self.started = False
        print("*** RISnet stopped")

    def findPaths(self, src, dst, algorithm='dijkstra'):
        """Find all paths between two nodes (high-level API)

        Args:
            src: Source node (AP object or name)
            dst: Destination node (UE object or name)
            algorithm: 'dijkstra', 'astar', 'greedy', 'exhaustive'

        Returns:
            List of path dicts
        """
        src_name = src if isinstance(src, str) else src.name
        dst_name = dst if isinstance(dst, str) else dst.name

        if not self.controller:
            raise RuntimeError("Controller not enabled. Create RISnet with controller=True")

        return self.controller.find_all_paths(src_name, dst_name, algorithm)

    def connect(self, ap, ris, ue, beam_angle=None):
        """Connect AP->RIS->UE (legacy method)

        Args:
            ap: AP node or name
            ris: RIS node or name
            ue: UE node or name
            beam_angle: Beam steering angle (None for auto)

        Returns:
            Connection result dict
        """
        ap_name = ap if isinstance(ap, str) else ap.name
        ris_name = ris if isinstance(ris, str) else ris.name
        ue_name = ue if isinstance(ue, str) else ue.name

        return self.network.connect(ap_name, ris_name, ue_name, beam_angle)

    def sweep(self, ap, ris, ue, fov=60, step=10):
        """Perform beam sweep

        Args:
            ap: AP node or name
            ris: RIS node or name
            ue: UE node or name
            fov: Field of view (degrees)
            step: Angular step (degrees)

        Returns:
            Sweep result dict
        """
        ap_name = ap if isinstance(ap, str) else ap.name
        ris_name = ris if isinstance(ris, str) else ris.name
        ue_name = ue if isinstance(ue, str) else ue.name

        return self.network.sweep(ap_name, ris_name, ue_name, fov, step)

    def ping(self, src, dst):
        """Ping-like test between two nodes

        Args:
            src: Source node
            dst: Destination node

        Returns:
            Dict with connectivity info
        """
        paths = self.findPaths(src, dst)

        if not paths:
            return {'reachable': False, 'snr_dB': -float('inf')}

        best_path = paths[0]
        return {
            'reachable': True,
            'snr_dB': best_path['snr_dB'],
            'hops': best_path['hops'],
            'path': best_path['path']
        }

    def iperf(self, src, dst):
        """iPerf-like throughput test

        Args:
            src: Source node
            dst: Destination node

        Returns:
            Estimated throughput
        """
        result = self.ping(src, dst)

        if not result['reachable']:
            return {'throughput_Mbps': 0}

        # Simple Shannon capacity estimation
        snr_linear = 10 ** (result['snr_dB'] / 10)
        bandwidth_MHz = self.config.get('environment.bandwidth_MHz', 20)
        capacity_Mbps = bandwidth_MHz * np.log2(1 + snr_linear)

        return {
            'throughput_Mbps': capacity_Mbps,
            'snr_dB': result['snr_dB'],
            'bandwidth_MHz': bandwidth_MHz
        }

    def CLI(self):
        """Launch interactive CLI (like Mininet's CLI)"""
        from risnet_cli import RISnetCLI
        cli = RISnetCLI(self)
        cli.cmdloop()

    def buildFromTopo(self, topo):
        """Build network from topology object

        Args:
            topo: Topology object
        """
        # Add nodes
        for ap_name, ap_params in topo.aps():
            self.addAP(ap_name, **ap_params)

        for ris_name, ris_params in topo.riss():
            self.addRIS(ris_name, **ris_params)

        for ue_name, ue_params in topo.ues():
            self.addUE(ue_name, **ue_params)

        # Add walls
        for wall_params in topo.walls():
            self.addWall(**wall_params)

    def _autoPosition(self, node_type):
        """Auto-generate position for node"""
        # Simple auto-positioning: spread nodes along a line
        if node_type == 'ap':
            return (0, 0, 0)
        elif node_type == 'ris':
            idx = len(self.riss)
            return (5 + idx * 5, 0, 0)
        else:  # ue
            idx = len(self.ues)
            return (10 + idx * 5, 3, 0)

    def __enter__(self):
        """Context manager support"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.stop()


class Topology:
    """Base topology class (like Mininet's Topo)

    Subclass this to create custom topologies.
    """

    def __init__(self):
        self.ap_dict = {}
        self.ris_dict = {}
        self.ue_dict = {}
        self.wall_list = []

    def addAP(self, name, **params):
        """Add AP to topology"""
        self.ap_dict[name] = params
        return name

    def addRIS(self, name, **params):
        """Add RIS to topology"""
        self.ris_dict[name] = params
        return name

    def addUE(self, name, **params):
        """Add UE to topology"""
        self.ue_dict[name] = params
        return name

    def addWall(self, **params):
        """Add wall to topology"""
        self.wall_list.append(params)

    def aps(self):
        """Return AP dict"""
        return self.ap_dict.items()

    def riss(self):
        """Return RIS dict"""
        return self.ris_dict.items()

    def ues(self):
        """Return UE dict"""
        return self.ue_dict.items()

    def walls(self):
        """Return wall list"""
        return self.wall_list

    def build(self):
        """Build topology (override in subclass)"""
        pass


# =====================================================================
# Predefined Topologies (like Mininet's topos)
# =====================================================================

class SingleRISTopo(Topology):
    """Single RIS topology: AP -- RIS -- UE"""

    def build(self, n=1):
        """Build topology with n UEs

        Args:
            n: Number of UEs
        """
        # Add AP
        self.addAP('ap1', position=(0, 0))

        # Add RIS
        self.addRIS('ris1', position=(5, 0), N=16, bits=2)

        # Add UEs
        for i in range(n):
            self.addUE(f'ue{i+1}', position=(10, i*2))


class MultiRISTopo(Topology):
    """Multiple RIS topology with redundant paths"""

    def build(self, n=3):
        """Build topology with n RIS nodes

        Args:
            n: Number of RIS nodes
        """
        # Add AP
        self.addAP('ap1', position=(0, 0))

        # Add multiple RIS in a line
        for i in range(n):
            self.addRIS(f'ris{i+1}', position=(3 + i*3, (i-n//2)*2), N=16, bits=2)

        # Add UE
        self.addUE('ue1', position=(3 + n*3, 0))


class GridTopo(Topology):
    """Grid topology with RIS nodes in a grid"""

    def build(self, rows=2, cols=2):
        """Build grid topology

        Args:
            rows: Number of rows
            cols: Number of columns
        """
        # Add AP at start
        self.addAP('ap1', position=(0, 0))

        # Add RIS grid
        for i in range(rows):
            for j in range(cols):
                name = f'ris{i*cols + j + 1}'
                self.addRIS(name, position=(5 + j*5, i*5 - rows*2.5), N=16, bits=2)

        # Add UE at end
        self.addUE('ue1', position=(5 + cols*5, 0))


class ObstacleTopo(Topology):
    """Topology with obstacles requiring RIS routing"""

    def build(self):
        """Build topology with walls"""
        # Add nodes
        self.addAP('ap1', position=(0, 0))
        self.addRIS('ris1', position=(5, 5), N=16, bits=2)
        self.addRIS('ris2', position=(5, -5), N=16, bits=2)
        self.addUE('ue1', position=(10, 0))

        # Add wall blocking direct path
        self.addWall(start=(4, -3), end=(4, 3), attenuation_dB=30)


# Topology registry (like Mininet's topos)
topos = {
    'single': SingleRISTopo,
    'multi': MultiRISTopo,
    'grid': GridTopo,
    'obstacle': ObstacleTopo
}


# =====================================================================
# Utility functions (like Mininet's helpers)
# =====================================================================

def run_experiment(topo_class, experiment_fn, **topo_params):
    """Run an experiment with given topology

    Args:
        topo_class: Topology class
        experiment_fn: Function to run experiment (takes net as arg)
        **topo_params: Parameters for topology build()

    Returns:
        Experiment results
    """
    topo = topo_class()
    topo.build(**topo_params)

    with RISnet(topo=topo) as net:
        return experiment_fn(net)


def quick_test():
    """Quick test (like Mininet's quick test)"""
    print("*** Creating network")
    net = RISnet()

    print("*** Adding nodes")
    ap = net.addAP('ap1', position=(0, 0))
    ris = net.addRIS('ris1', position=(5, 0))
    ue = net.addUE('ue1', position=(10, 3))

    print("*** Starting network")
    net.start()

    print("*** Testing connectivity")
    result = net.ping(ap, ue)
    print(f"Ping result: {result}")

    print("*** Testing throughput")
    throughput = net.iperf(ap, ue)
    print(f"iPerf result: {throughput}")

    print("*** Stopping network")
    net.stop()


if __name__ == '__main__':
    quick_test()
