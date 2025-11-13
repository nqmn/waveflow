"""
RIS Controller - Central orchestration for pathfinding and optimization
"""
import numpy as np
from typing import Dict, List, Optional, Tuple
import time
from .pathfinding import get_algorithm, list_algorithms
from .beamforming import BeamformingEngine
from core.physics import Physics
from core.nodes import AccessPoint, RIS


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
        self.use_measured_snr = False  # Option 3: Use feedback channel SNR
        self.stats = {
            'paths_found': 0,
            'last_decision_time_ms': 0,
            'update_count': 0,
            'best_snr_dB': None
        }

    # Option 3: Feedback Channel Methods (UE → Controller SNR)
    def enable_feedback_channel(self, ue_name: str, ris_name: str,
                               history_size: int = 100) -> 'FeedbackChannel':
        """
        Enable feedback channel from UE to this controller.

        Args:
            ue_name: Source UE node name
            ris_name: RIS node name (this controller's RIS)
            history_size: Maximum CSI reports to store

        Returns:
            FeedbackChannel instance
        """
        channel = self.network.create_feedback_channel(ue_name, ris_name, history_size)
        self.use_measured_snr = True
        return channel

    def get_latest_ue_snr_dB(self, ue_name: str, ris_name: str,
                             use_messaging: bool = True) -> Optional[float]:
        """
        Query latest measured SNR from UE.

        Two modes:
        1. use_messaging=True (DEFAULT): Query via control channel (real-world)
           - Sends SNR_REQUEST to UE
           - Receives SNR_RESPONSE back
           - Includes latency simulation

        2. use_messaging=False: Query feedback channel directly (legacy)
           - Instant access to accumulated measurements
           - No latency

        Args:
            ue_name: UE node name
            ris_name: RIS node name
            use_messaging: Use control channel (True) or feedback channel (False)

        Returns:
            Latest SNR in dB, or None if no response/no reports
        """
        # Real-world mode: Query via messaging system
        if use_messaging and self.network.snr_messaging is not None:
            response = self.network.snr_messaging.query_ue_snr(
                self.network.get(ris_name).name,  # Controller on this RIS
                ue_name,
                ris_name
            )
            if response and response.status == 'success':
                return response.snr_dB
            return None

        # Legacy mode: Query feedback channel directly
        channel = self.network.get_feedback_channel(ue_name, ris_name)
        if channel is None:
            return None
        return channel.get_latest_snr_dB()

    def get_average_ue_snr_dB(self, ue_name: str, ris_name: str,
                             window: Optional[int] = None) -> Optional[float]:
        """
        Get average SNR from UE feedback channel over a window.

        Args:
            ue_name: UE node name
            ris_name: RIS node name
            window: Number of recent reports to average (None = all)

        Returns:
            Average SNR in dB, or None if no reports
        """
        channel = self.network.get_feedback_channel(ue_name, ris_name)
        if channel is None:
            return None
        return channel.get_average_snr_dB(window)

    def get_ue_snr_history(self, ue_name: str, ris_name: str,
                          last_n: Optional[int] = None) -> List[Dict]:
        """
        Get historical SNR measurements from UE feedback channel.

        Args:
            ue_name: UE node name
            ris_name: RIS node name
            last_n: Number of recent reports to return (None = all)

        Returns:
            List of CSI report dictionaries
        """
        channel = self.network.get_feedback_channel(ue_name, ris_name)
        if channel is None:
            return []
        return channel.get_history_dicts(last_n)

    def get_ue_feedback_statistics(self, ue_name: str, ris_name: str) -> Dict:
        """
        Get feedback channel statistics for a UE.

        Args:
            ue_name: UE node name
            ris_name: RIS node name

        Returns:
            Dictionary with channel statistics
        """
        channel = self.network.get_feedback_channel(ue_name, ris_name)
        if channel is None:
            return {'status': 'no_channel'}
        return channel.get_statistics()

    def get_all_feedback_statistics(self) -> Dict:
        """
        Get network-wide feedback channel statistics.

        Returns:
            Dictionary with all channel statistics
        """
        return self.network.list_feedback_channels()

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
            if not isinstance(ris_node, RIS):
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

        node1_obj = self.network.get(node1)
        node2_obj = self.network.get(node2)

        freq = 10e9  # Default frequency
        tx_power_dBm = 20  # Default transmit power

        # Use AccessPoint metadata if available (AP might be node1 or node2)
        for candidate in (node1_obj, node2_obj):
            if isinstance(candidate, AccessPoint):
                freq = candidate.freq
                tx_power_dBm = candidate.power_dBm
                break

        # Calculate path loss & atmospheric absorption
        path_loss_dB = Physics.path_loss_dB(distance, freq)
        atm_loss_dB = Physics.atmospheric_loss_dB(distance, freq / 1e9)

        gain_dBi = 0
        quantization_loss_dB = 0

        # Apply RIS gain/quantization losses when a RIS participates
        ris_node = node1_obj if isinstance(node1_obj, RIS) else (
            node2_obj if isinstance(node2_obj, RIS) else None
        )

        if ris_node:
            total_elements = ris_node.N * ris_node.N
            gain_dBi = Physics.array_gain_dBi(total_elements, ris_node.amplifier_gain)
            quantization_loss_dB = Physics.quantization_loss_dB(ris_node.bits)

            if beam_angle is not None:
                target_angle = np.degrees(np.arctan2(pos2[1] - pos1[1], pos2[0] - pos1[0]))
                angle_loss = Physics.angle_loss_dB(beam_angle, target_angle)
                gain_dBi -= angle_loss

        total_loss_dB = path_loss_dB + atm_loss_dB + quantization_loss_dB - gain_dBi
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
