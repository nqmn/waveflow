"""
Dijkstra's algorithm for shortest path

Optimal path finding with SNR-weighted edges.
Complexity: O(E log V)
"""

import heapq
import numpy as np
from typing import Dict
from .base import PathfindingAlgorithm


class Dijkstra(PathfindingAlgorithm):
    """Dijkstra's algorithm - optimal shortest path"""

    name = "dijkstra"
    description = "Dijkstra's algorithm (optimal, O(E log V))"

    @staticmethod
    def find_path(graph: Dict[str, Dict[str, float]],
                  source: str,
                  target: str,
                  node_positions: Dict[str, np.ndarray]) -> Dict:
        """Dijkstra's algorithm implementation

        Finds optimal path minimizing total loss (maximizing SNR)

        Args:
            graph: Adjacency dict
            source: Source node
            target: Target node
            node_positions: Node positions

        Returns:
            Dict with path, totalLoss, totalLength
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
