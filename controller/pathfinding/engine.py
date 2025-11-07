"""
Pathfinding algorithms for multi-hop RIS routing

Implements:
- Dijkstra: SNR-weighted shortest path (optimal)
- A*: Heuristic-guided search
- Greedy: Fast local optimization
- Exhaustive: Brute-force all paths
"""
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
import heapq
from itertools import permutations


class PathfindingEngine:
    """Multi-algorithm pathfinding engine for RIS networks"""

    @staticmethod
    def dijkstra(graph: Dict[str, Dict[str, float]],
                 source: str,
                 target: str,
                 node_positions: Dict[str, np.ndarray]) -> Dict:
        """Dijkstra's algorithm for shortest path

        Finds optimal path minimizing total loss (maximizing SNR)

        Args:
            graph: Adjacency dict {node: {neighbor: weight}}
            source: Source node name
            target: Target node name
            node_positions: Dict of node positions

        Returns:
            Dict with 'path', 'totalLoss', 'totalLength'
        """
        nodes = list(graph.keys())
        distances = {node: float('inf') for node in nodes}
        prev = {}
        pq = [(0, source)]  # Priority queue: (distance, node)
        distances[source] = 0
        visited = set()

        while pq:
            current_dist, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == target:
                break

            if current not in graph:
                continue

            for neighbor, weight in graph[current].items():
                distance = current_dist + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    prev[neighbor] = current
                    heapq.heappush(pq, (distance, neighbor))

        # Reconstruct path
        path = []
        current = target
        total_length = 0

        if prev.get(current) or current == source:
            while current:
                path.insert(0, current)
                if prev.get(current):
                    total_length += np.linalg.norm(
                        node_positions[current] - node_positions[prev[current]]
                    )
                current = prev.get(current)

        return {
            'path': path if path else [],
            'totalLoss': distances[target] if distances[target] != float('inf') else float('inf'),
            'totalLength': total_length
        }

    @staticmethod
    def astar(graph: Dict[str, Dict[str, float]],
              source: str,
              target: str,
              node_positions: Dict[str, np.ndarray],
              heuristic_weight: float = 0.1) -> Dict:
        """A* pathfinding with distance heuristic

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node position dict
            heuristic_weight: Weight for distance heuristic

        Returns:
            Dict with 'path', 'totalLoss', 'totalLength'
        """
        def heuristic(node1, node2):
            """Euclidean distance heuristic"""
            return np.linalg.norm(node_positions[node1] - node_positions[node2]) * heuristic_weight

        g_score = {node: float('inf') for node in graph.keys()}
        f_score = {node: float('inf') for node in graph.keys()}
        prev = {}

        g_score[source] = 0
        f_score[source] = heuristic(source, target)

        open_set = [(f_score[source], source)]
        visited = set()

        while open_set:
            current_f, current = heapq.heappop(open_set)

            if current in visited:
                continue
            visited.add(current)

            if current == target:
                # Reconstruct path
                path = []
                total_length = 0
                temp = current

                while temp:
                    path.insert(0, temp)
                    if prev.get(temp):
                        total_length += np.linalg.norm(
                            node_positions[temp] - node_positions[prev[temp]]
                        )
                    temp = prev.get(temp)

                return {
                    'path': path,
                    'totalLoss': g_score[target],
                    'totalLength': total_length
                }

            if current not in graph:
                continue

            for neighbor, weight in graph[current].items():
                tentative_g = g_score[current] + weight

                if tentative_g < g_score[neighbor]:
                    prev[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, target)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return {'path': [], 'totalLoss': float('inf'), 'totalLength': 0}

    @staticmethod
    def greedy(graph: Dict[str, Dict[str, float]],
               source: str,
               target: str,
               node_positions: Dict[str, np.ndarray]) -> Dict:
        """Greedy pathfinding - choose nearest neighbor

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions

        Returns:
            Dict with 'path', 'totalLoss', 'totalLength'
        """
        visited = set()
        path = [source]
        current = source
        total_loss = 0
        total_length = 0
        max_hops = 20  # Prevent infinite loops

        while current != target and len(path) < max_hops:
            visited.add(current)
            best_neighbor = None
            best_heuristic = float('inf')

            if current not in graph:
                break

            for neighbor, weight in graph[current].items():
                if neighbor in visited:
                    continue

                # Heuristic: edge weight + distance to target
                dist_to_target = np.linalg.norm(
                    node_positions[neighbor] - node_positions[target]
                )
                heuristic_val = weight + dist_to_target * 0.1

                if heuristic_val < best_heuristic:
                    best_heuristic = heuristic_val
                    best_neighbor = neighbor

            if not best_neighbor:
                break

            total_loss += graph[current][best_neighbor]
            total_length += np.linalg.norm(
                node_positions[current] - node_positions[best_neighbor]
            )
            path.append(best_neighbor)
            current = best_neighbor

        if current != target:
            return {'path': [], 'totalLoss': float('inf'), 'totalLength': 0}

        return {
            'path': path,
            'totalLoss': total_loss,
            'totalLength': total_length
        }

    @staticmethod
    def exhaustive(graph: Dict[str, Dict[str, float]],
                   source: str,
                   target: str,
                   node_positions: Dict[str, np.ndarray],
                   max_hops: int = 4) -> Dict:
        """Exhaustive search - try all possible paths

        WARNING: Exponential complexity - use only for small networks

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions
            max_hops: Maximum path length to consider

        Returns:
            Dict with 'path', 'totalLoss', 'totalLength'
        """
        # Get intermediate nodes (exclude source and target)
        all_nodes = set(graph.keys())
        intermediate = all_nodes - {source, target}

        best_path = []
        best_loss = float('inf')
        best_length = 0

        # Try all possible path lengths
        for num_intermediate in range(min(len(intermediate), max_hops - 1) + 1):
            # Try all permutations of intermediate nodes
            for intermediate_nodes in permutations(intermediate, num_intermediate):
                path = [source] + list(intermediate_nodes) + [target]

                # Check if path is valid and calculate loss
                total_loss = 0
                total_length = 0
                valid = True

                for i in range(len(path) - 1):
                    current_node = path[i]
                    next_node = path[i + 1]

                    if current_node not in graph or next_node not in graph[current_node]:
                        valid = False
                        break

                    total_loss += graph[current_node][next_node]
                    total_length += np.linalg.norm(
                        node_positions[current_node] - node_positions[next_node]
                    )

                if valid and total_loss < best_loss:
                    best_loss = total_loss
                    best_path = path
                    best_length = total_length

        return {
            'path': best_path,
            'totalLoss': best_loss,
            'totalLength': best_length
        }

    @staticmethod
    def validate_path_steering_constraints(path: List[str],
                                           node_positions: Dict[str, np.ndarray],
                                           max_angle_deg: float = 60) -> bool:
        """Validate that all RIS nodes in path can achieve required steering angles

        Args:
            path: List of node names
            node_positions: Node positions
            max_angle_deg: Maximum steering angle per RIS

        Returns:
            True if path is feasible
        """
        if len(path) < 3:
            return True  # Direct links always valid

        for i in range(1, len(path) - 1):
            node = path[i]
            if not node.startswith('R'):  # Only check RIS nodes
                continue

            prev_node = path[i - 1]
            next_node = path[i + 1]

            pos = node_positions[node]
            prev_pos = node_positions[prev_node]
            next_pos = node_positions[next_node]

            # Calculate incident and reflection angles
            incident_vec = pos - prev_pos
            incident_angle = np.arctan2(incident_vec[1], incident_vec[0])

            target_vec = next_pos - pos
            target_angle = np.arctan2(target_vec[1], target_vec[0])

            # Specular reflection angle
            specular_angle = incident_angle + np.pi

            # Deflection from specular
            deflection = target_angle - specular_angle
            deflection = np.rad2deg(deflection)

            # Normalize to [-180, 180]
            while deflection > 180:
                deflection -= 360
            while deflection < -180:
                deflection += 360

            if abs(deflection) > max_angle_deg:
                return False

        return True

    @staticmethod
    def get_algorithm(name: str):
        """Get pathfinding algorithm by name

        Args:
            name: Algorithm name ('dijkstra', 'astar', 'greedy', 'exhaustive')

        Returns:
            Algorithm function
        """
        algorithms = {
            'dijkstra': PathfindingEngine.dijkstra,
            'astar': PathfindingEngine.astar,
            'greedy': PathfindingEngine.greedy,
            'exhaustive': PathfindingEngine.exhaustive
        }
        return algorithms.get(name.lower(), PathfindingEngine.dijkstra)
