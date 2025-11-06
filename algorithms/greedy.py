"""
Greedy pathfinding algorithm

Fast local optimization, chooses nearest neighbor.
Complexity: O(V)
"""

import numpy as np
from typing import Dict
from .base import PathfindingAlgorithm


class Greedy(PathfindingAlgorithm):
    """Greedy algorithm - fast local optimization"""

    name = "greedy"
    description = "Greedy nearest neighbor (fast, suboptimal)"

    @staticmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray]) -> Dict:
        """Greedy pathfinding implementation

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions

        Returns:
            Dict with path, totalLoss, totalLength
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
