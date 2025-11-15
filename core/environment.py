"""
Environment modeling with obstacles and walls
"""
import numpy as np
from typing import List, Tuple, Optional

class Wall:
    """Represents a physical wall/obstacle in the environment"""

    def __init__(self, start, end, attenuation_dB=20.0, name=None):
        """
        Args:
            start: Start point (x, y) tuple or numpy array
            end: End point (x, y) tuple or numpy array
            attenuation_dB: Signal attenuation through wall in dB
            name: Optional wall identifier
        """
        self.start = np.array(start) if not isinstance(start, np.ndarray) else start
        self.end = np.array(end) if not isinstance(end, np.ndarray) else end
        self.attenuation_dB = attenuation_dB
        self.name = name or f"Wall_{id(self)}"

    def to_dict(self):
        """Convert wall to dictionary for API"""
        return {
            'name': self.name,
            'start': self.start.tolist()[:2],  # Only x, y
            'end': self.end.tolist()[:2],
            'attenuation_dB': self.attenuation_dB
        }

    @staticmethod
    def from_dict(data):
        """Create wall from dictionary"""
        return Wall(
            start=data['start'],
            end=data['end'],
            attenuation_dB=data.get('attenuation_dB', 20.0),
            name=data.get('name')
        )


class Environment:
    """Environment manager with walls and obstacles"""

    def __init__(self):
        self.walls: List[Wall] = []
        self.bounds = {'x_min': -10, 'x_max': 10, 'y_min': -10, 'y_max': 10}

    def add_wall(self, start, end, attenuation_dB=20.0, name=None):
        """Add a wall to the environment

        Args:
            start: Start point (x, y)
            end: End point (x, y)
            attenuation_dB: Signal attenuation through wall
            name: Optional wall name
        """
        wall = Wall(start, end, attenuation_dB, name)
        self.walls.append(wall)
        return wall

    def remove_wall(self, name):
        """Remove wall by name"""
        self.walls = [w for w in self.walls if w.name != name]

    def clear_walls(self):
        """Remove all walls"""
        self.walls.clear()

    def check_line_of_sight(self, pos1, pos2) -> Tuple[bool, float]:
        """Check if there's line of sight between two points

        Args:
            pos1: First point (numpy array or tuple)
            pos2: Second point (numpy array or tuple)

        Returns:
            Tuple of (has_los: bool, total_attenuation_dB: float)
        """
        pos1 = np.array(pos1)[:2]  # Only use x, y
        pos2 = np.array(pos2)[:2]

        total_attenuation = 0.0
        has_los = True

        for wall in self.walls:
            if self._line_segments_intersect(pos1, pos2, wall.start[:2], wall.end[:2]):
                has_los = False
                total_attenuation += wall.attenuation_dB

        return has_los, total_attenuation

    @staticmethod
    def _line_segments_intersect(p1, p2, p3, p4) -> bool:
        """Check if line segment p1-p2 intersects with p3-p4

        Uses the cross-product method for line segment intersection

        Args:
            p1, p2: First line segment endpoints
            p3, p4: Second line segment endpoints

        Returns:
            True if segments intersect
        """
        def ccw(A, B, C):
            """Check if three points are in counter-clockwise order"""
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

        # Check if p1-p2 and p3-p4 intersect
        return (ccw(p1, p3, p4) != ccw(p2, p3, p4) and
                ccw(p1, p2, p3) != ccw(p1, p2, p4))

    def get_blocked_paths(self, pos1, pos2) -> List[Wall]:
        """Get list of walls blocking a path

        Args:
            pos1: Start point
            pos2: End point

        Returns:
            List of walls that block the path
        """
        pos1 = np.array(pos1)[:2]
        pos2 = np.array(pos2)[:2]

        blocked_by = []
        for wall in self.walls:
            if self._line_segments_intersect(pos1, pos2, wall.start[:2], wall.end[:2]):
                blocked_by.append(wall)

        return blocked_by

    def to_dict(self):
        """Convert environment to dictionary for API"""
        return {
            'walls': [w.to_dict() for w in self.walls],
            'bounds': self.bounds
        }

    def from_dict(self, data):
        """Load environment from dictionary"""
        self.walls.clear()
        for wall_data in data.get('walls', []):
            self.walls.append(Wall.from_dict(wall_data))
        if 'bounds' in data:
            self.bounds = data['bounds']
