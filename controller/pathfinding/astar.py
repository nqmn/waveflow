"""
A* pathfinding algorithm

Heuristic-guided search with distance heuristic.
Complexity: O(E log V) with good heuristic
"""

import heapq
import numpy as np
from typing import Dict
from .base import PathfindingAlgorithm


class AStar(PathfindingAlgorithm):
    """A* algorithm - heuristic-guided search"""

    name = "astar"
    description = "A* with distance heuristic (optimal, fast)"

    @staticmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray],
                  heuristic_weight: float = 0.1) -> Dict:
        """A* pathfinding implementation

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions
            heuristic_weight: Weight for distance heuristic

        Returns:
            Dict with path, totalLoss, totalLength
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
