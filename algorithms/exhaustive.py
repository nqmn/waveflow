"""
Exhaustive search algorithm

Tries all possible paths (brute force).
Complexity: O(V!) - use only for small networks
"""

import numpy as np
from typing import Dict
from itertools import permutations
from .base import PathfindingAlgorithm


class Exhaustive(PathfindingAlgorithm):
    """Exhaustive search - tries all paths"""

    name = "exhaustive"
    description = "Exhaustive search (optimal, very slow, O(V!))"

    @staticmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray],
                  max_hops: int = 4) -> Dict:
        """Exhaustive search implementation

        WARNING: Exponential complexity - use only for small networks

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions
            max_hops: Maximum path length to consider

        Returns:
            Dict with path, totalLoss, totalLength
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
