"""
RIS Controller - Central orchestration for pathfinding and optimization
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
from algorithms import get_algorithm, list_algorithms
from algorithms.beamforming import BeamformingEngine
from core.physics import Physics


class RISController:
    """Centralized RIS network controller

    Manages:
    - Multi-algorithm pathfinding
    - Link quality assessment
    - Path selection strategies
    - Network-wide optimization
    """

    def __init__(self, network, environment=None):
        """
        Args:
            network: RISNetwork instance
            environment: Environment instance with walls/obstacles
        """
        self.network = network
        self.environment = environment
        self.enabled = True
        self.algorithm = 'dijkstra'  # Default algorithm
        self.strategy = 'max-snr'  # Default strategy
        self.stats = {
            'paths_found': 0,
            'last_decision_time_ms': 0,
            'update_count': 0,
            'best_snr_dB': None
        }

    def find_all_paths(self, ap_name: str, ue_name: str,
                       algorithm: Optional[str] = None,
                       use_beam_sweep: bool = True) -> List[Dict]:
        """Find all viable paths from AP to UE

        Args:
            ap_name: Access point name
            ue_name: User equipment name
            algorithm: Pathfinding algorithm ('dijkstra', 'astar', 'greedy', 'exhaustive')
            use_beam_sweep: Whether to use beam sweeping for accurate SNR

        Returns:
            List of path dicts with metadata
        """
        if not self.enabled:
            return []

        start_time = time.time()

        ap = self.network.get(ap_name)
        ue = self.network.get(ue_name)

        if not ap or not ue:
            return []

        algorithm = algorithm or self.algorithm
        paths = []

        # Build network graph with link weights
        graph, node_positions, metadata = self._build_graph()

        # Check direct path
        has_los, direct_loss = True, 0
        if self.environment:
            has_los, direct_loss = self.environment.check_line_of_sight(ap.pos, ue.pos)

        if has_los:
            # Direct path possible
            direct_snr = self._compute_link_snr(
                ap.pos, ue.pos, ap_name, ue_name, None, use_beam_sweep
            )
            paths.append({
                'id': 'direct',
                'path': [ap_name, ue_name],
                'snr_dB': 10 * np.log10(direct_snr) if direct_snr > 0 else -np.inf,
                'hops': 1,
                'total_loss_dB': direct_loss,
                'type': 'direct'
            })

        # Find paths through RIS nodes
        # Auto-discover algorithm from registry
        algorithm_class = get_algorithm(algorithm)

        result = algorithm_class.find_path(graph, ap_name, ue_name, node_positions)

        if result['path'] and len(result['path']) > 2:
            # Calculate actual SNR for this path
            path_snr = self._calculate_path_snr(
                result['path'], node_positions, use_beam_sweep
            )

            paths.append({
                'id': f'via_{"-".join(result["path"][1:-1])}',
                'path': result['path'],
                'snr_dB': 10 * np.log10(path_snr) if path_snr > 0 else -np.inf,
                'hops': len(result['path']) - 1,
                'total_loss_dB': result['totalLoss'],
                'total_length_m': result['totalLength'],
                'type': 'reflected'
            })

        # Try single-hop RIS paths
        for ris_name, ris_node in self.network.nodes.items():
            if not ris_name.startswith('R'):
                continue

            # Check if AP->RIS and RIS->UE are both LOS
            ap_ris_los, ap_ris_loss = True, 0
            ris_ue_los, ris_ue_loss = True, 0

            if self.environment:
                ap_ris_los, ap_ris_loss = self.environment.check_line_of_sight(ap.pos, ris_node.pos)
                ris_ue_los, ris_ue_loss = self.environment.check_line_of_sight(ris_node.pos, ue.pos)

            if ap_ris_los and ris_ue_los:
                # Calculate SNR for this single-hop path
                single_hop_path = [ap_name, ris_name, ue_name]
                path_snr = self._calculate_path_snr(
                    single_hop_path, node_positions, use_beam_sweep
                )

                paths.append({
                    'id': f'via_{ris_name}',
                    'path': single_hop_path,
                    'snr_dB': 10 * np.log10(path_snr) if path_snr > 0 else -np.inf,
                    'hops': 2,
                    'total_loss_dB': ap_ris_loss + ris_ue_loss,
                    'type': 'single_hop'
                })

        # Update stats
        end_time = time.time()
        self.stats['paths_found'] = len(paths)
        self.stats['last_decision_time_ms'] = int((end_time - start_time) * 1000)
        self.stats['update_count'] += 1

        if paths:
            best_path = max(paths, key=lambda p: p['snr_dB'])
            self.stats['best_snr_dB'] = best_path['snr_dB']

        return sorted(paths, key=lambda p: p['snr_dB'], reverse=True)

    def select_best_path(self, paths: List[Dict], strategy: Optional[str] = None) -> Optional[Dict]:
        """Select best path based on strategy

        Args:
            paths: List of path dicts
            strategy: Selection strategy ('max-snr', 'min-hops', 'min-loss')

        Returns:
            Best path dict or None
        """
        if not paths:
            return None

        strategy = strategy or self.strategy

        if strategy == 'max-snr':
            return max(paths, key=lambda p: p['snr_dB'])
        elif strategy == 'min-hops':
            return min(paths, key=lambda p: p['hops'])
        elif strategy == 'min-loss':
            return min(paths, key=lambda p: p['total_loss_dB'])
        else:
            return max(paths, key=lambda p: p['snr_dB'])

    def _build_graph(self) -> Tuple[Dict, Dict, Dict]:
        """Build network graph with link weights

        Returns:
            Tuple of (graph, node_positions, edge_metadata)
        """
        graph = {}
        node_positions = {}
        edge_metadata = {}

        # Add all nodes
        for name, node in self.network.nodes.items():
            graph[name] = {}
            node_positions[name] = node.pos
            edge_metadata[name] = {}

        # Build edges between all node pairs
        node_list = list(self.network.nodes.keys())

        for i, node1_name in enumerate(node_list):
            for node2_name in node_list[i + 1:]:
                node1 = self.network.nodes[node1_name]
                node2 = self.network.nodes[node2_name]

                # Check line of sight
                has_los = True
                if self.environment:
                    has_los, _ = self.environment.check_line_of_sight(node1.pos, node2.pos)

                if has_los:
                    # Calculate link weight (inverse SNR for minimization)
                    snr = self._compute_link_snr(
                        node1.pos, node2.pos, node1_name, node2_name, None, use_beam_sweep=False
                    )
                    weight = 1.0 / (snr + 1e-6)  # Avoid division by zero

                    graph[node1_name][node2_name] = weight
                    graph[node2_name][node1_name] = weight

                    edge_metadata[node1_name][node2_name] = {'snr': snr, 'los': True}
                    edge_metadata[node2_name][node1_name] = {'snr': snr, 'los': True}

        return graph, node_positions, edge_metadata

    def _compute_link_snr(self, pos1: np.ndarray, pos2: np.ndarray,
                          node1: str, node2: str,
                          beam_angle: Optional[float] = None,
                          use_beam_sweep: bool = False) -> float:
        """Compute SNR for a link

        Args:
            pos1: Position of node1
            pos2: Position of node2
            node1: Node1 name
            node2: Node2 name
            beam_angle: Beam angle in degrees (None for auto)
            use_beam_sweep: Whether to use beam sweeping

        Returns:
            SNR in linear scale
        """
        distance = np.linalg.norm(pos2 - pos1)
        if distance < 0.01:
            return 0

        # Get frequency from AP or RIS
        freq = 10e9  # Default
        ap = self.network.get('AP') or self.network.get('ap1')
        if ap:
            freq = ap.freq

        # Calculate path loss
        path_loss_dB = Physics.path_loss_dB(distance, freq)

        # Calculate atmospheric loss
        atm_loss_dB = Physics.atmospheric_loss_dB(distance, freq / 1e9)

        # Calculate gains
        gain_dBi = 0
        quantization_loss_dB = 0

        # RIS gain calculation
        if node1.startswith('R') or node2.startswith('R'):
            ris_name = node1 if node1.startswith('R') else node2
            ris = self.network.get(ris_name)

            if ris:
                N = ris.N * ris.N
                gain_dBi = Physics.array_gain_dBi(N, ris.amplifier_gain)
                quantization_loss_dB = Physics.quantization_loss_dB(ris.bits)

                # Angle loss if beam angle specified
                if beam_angle is not None:
                    target_angle = np.degrees(np.arctan2(pos2[1] - pos1[1], pos2[0] - pos1[0]))
                    angle_loss = Physics.angle_loss_dB(beam_angle, target_angle)
                    gain_dBi -= angle_loss

        # Total loss
        total_loss_dB = path_loss_dB + atm_loss_dB + quantization_loss_dB - gain_dBi

        # Calculate SNR
        tx_power_dBm = 20  # Default
        if ap:
            tx_power_dBm = ap.power_dBm

        snr_dB = Physics.compute_snr_dB(tx_power_dBm, total_loss_dB, 0, 20, 10)
        snr_linear = 10 ** (snr_dB / 10)

        return snr_linear

    def _calculate_path_snr(self, path: List[str], node_positions: Dict,
                            use_beam_sweep: bool = False) -> float:
        """Calculate end-to-end SNR for a multi-hop path

        Args:
            path: List of node names
            node_positions: Node position dict
            use_beam_sweep: Whether to use beam sweeping

        Returns:
            Path SNR in linear scale
        """
        if len(path) < 2:
            return 0

        # For simplicity, use minimum link SNR (bottleneck)
        # More sophisticated: cascaded SNR calculation
        min_snr = float('inf')

        for i in range(len(path) - 1):
            node1 = path[i]
            node2 = path[i + 1]

            link_snr = self._compute_link_snr(
                node_positions[node1],
                node_positions[node2],
                node1,
                node2,
                None,
                use_beam_sweep
            )

            min_snr = min(min_snr, link_snr)

        return min_snr
