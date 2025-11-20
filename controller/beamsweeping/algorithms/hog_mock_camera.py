"""Synthetic/Mock Camera for HOG Testing

Generates synthetic video frames with simulated human-like objects
for testing HOG detection without a real camera.

Features:
- Generates synthetic frames with human-shaped bounding boxes
- Supports different trajectory patterns (circular, linear, random, static)
- Realistic HOG detection behavior simulation
- Works seamlessly with HOGHumanDetectionSweep
"""

import numpy as np
import cv2
from typing import Tuple


class MockCameraForHOG:
    """Synthetic camera that generates frames with simulated humans."""

    def __init__(self, width: int = 640, height: int = 480,
                 num_frames: int = 100,
                 trajectory: str = "circular",
                 num_humans: int = 1):
        """Initialize mock camera.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            num_frames: Total frames to generate
            trajectory: 'circular', 'linear', 'random', or 'static'
            num_humans: Number of simulated humans in scene
        """
        self.width = width
        self.height = height
        self.num_frames = num_frames
        self.trajectory = trajectory
        self.num_humans = num_humans
        self.frame_count = 0
        self.is_opened_flag = True

        # Center of frame
        self.cx = width // 2
        self.cy = height // 2

        # Human box dimensions (realistic for 640x480)
        self.human_width = 120
        self.human_height = 200

    def isOpened(self) -> bool:
        """Check if camera is open."""
        return self.is_opened_flag

    def read(self) -> Tuple[bool, np.ndarray]:
        """Read next synthetic frame.

        Returns:
            (success, frame) where frame is BGR image
        """
        if self.frame_count >= self.num_frames:
            return False, None

        # Create blank frame (dark background)
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 50

        # Generate human positions based on trajectory
        if self.trajectory == "circular":
            positions = self._circular_trajectory()
        elif self.trajectory == "linear":
            positions = self._linear_trajectory()
        elif self.trajectory == "random":
            positions = self._random_trajectory()
        else:  # static
            positions = self._static_trajectory()

        # Draw humans on frame
        for x, y in positions:
            self._draw_human(frame, x, y)

        # Add frame info text
        cv2.putText(frame, f"Mock Frame {self.frame_count + 1}/{self.num_frames}",
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.putText(frame, f"Trajectory: {self.trajectory}",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.putText(frame, "Simulated humans for HOG detection",
                   (10, self.height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        self.frame_count += 1
        return True, frame

    def release(self):
        """Release camera resource."""
        self.is_opened_flag = False

    def get(self, prop_id: int) -> float:
        """Get camera property.

        Args:
            prop_id: OpenCV property ID (e.g., cv2.CAP_PROP_FRAME_WIDTH)

        Returns:
            Property value
        """
        if prop_id == cv2.CAP_PROP_FRAME_WIDTH:
            return float(self.width)
        elif prop_id == cv2.CAP_PROP_FRAME_HEIGHT:
            return float(self.height)
        elif prop_id == cv2.CAP_PROP_FPS:
            return 30.0
        else:
            return 0.0

    def _circular_trajectory(self) -> list:
        """Generate circular motion trajectory."""
        positions = []
        angle = (self.frame_count / self.num_frames) * 2 * np.pi

        # Radius of circular motion
        radius = 150

        for i in range(self.num_humans):
            # Offset for multiple humans
            offset_angle = angle + (i * 2 * np.pi / self.num_humans)

            x = int(self.cx + radius * np.cos(offset_angle))
            y = int(self.cy + radius * np.sin(offset_angle) * 0.5)  # Elliptical

            positions.append((x, y))

        return positions

    def _linear_trajectory(self) -> list:
        """Generate linear motion trajectory."""
        positions = []
        progress = self.frame_count / self.num_frames

        for i in range(self.num_humans):
            # Move left to right
            x = int(self.width * progress)
            y = int(self.cy + 100 * np.sin(progress * np.pi))  # Slight up/down

            positions.append((x, y))

        return positions

    def _random_trajectory(self) -> list:
        """Generate random trajectory."""
        positions = []
        np.random.seed(42 + self.frame_count)  # Reproducible randomness

        for i in range(self.num_humans):
            x = np.random.randint(100, self.width - 100)
            y = np.random.randint(100, self.height - 100)
            positions.append((x, y))

        return positions

    def _static_trajectory(self) -> list:
        """Generate static (no movement) trajectory."""
        positions = []

        for i in range(self.num_humans):
            # Spread humans horizontally
            x = self.width // (self.num_humans + 1) * (i + 1)
            y = self.cy

            positions.append((x, y))

        return positions

    def _draw_human(self, frame: np.ndarray, x: int, y: int):
        """Draw human-shaped bounding box on frame.

        Args:
            frame: Frame to draw on
            x: X position (centroid)
            y: Y position (centroid)
        """
        # Convert centroid to top-left corner
        x1 = x - self.human_width // 2
        y1 = y - self.human_height // 2
        x2 = x1 + self.human_width
        y2 = y1 + self.human_height

        # Ensure within frame bounds
        x1 = max(0, min(x1, self.width - 1))
        y1 = max(0, min(y1, self.height - 1))
        x2 = max(0, min(x2, self.width - 1))
        y2 = max(0, min(y2, self.height - 1))

        # Draw human shape (simplified: head + body)
        # Head (circle)
        head_radius = 25
        head_x = x
        head_y = y1 + 40
        cv2.circle(frame, (head_x, head_y), head_radius, (100, 100, 200), -1)
        cv2.circle(frame, (head_x, head_y), head_radius, (0, 255, 255), 2)

        # Body (rectangle)
        body_top = head_y + head_radius + 5
        body_bottom = y2
        body_left = x - 30
        body_right = x + 30
        cv2.rectangle(frame, (body_left, body_top), (body_right, body_bottom),
                     (100, 100, 200), -1)
        cv2.rectangle(frame, (body_left, body_top), (body_right, body_bottom),
                     (0, 255, 255), 2)

        # Arms
        arm_y = body_top + 30
        cv2.line(frame, (body_left, arm_y), (body_left - 40, arm_y - 20),
                (100, 100, 200), 8)
        cv2.line(frame, (body_right, arm_y), (body_right + 40, arm_y - 20),
                (100, 100, 200), 8)

        # Legs
        leg_start = body_bottom - 40
        cv2.line(frame, (body_left + 10, leg_start), (body_left - 10, body_bottom),
                (100, 100, 200), 8)
        cv2.line(frame, (body_right - 10, leg_start), (body_right + 10, body_bottom),
                (100, 100, 200), 8)

        # Draw detection box (what HOG would find)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, "Person", (x1, y1 - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)


def demo_mock_camera():
    """Demo the mock camera."""
    print("Mock Camera Demo - Synthetic Human Detection")
    print("=" * 60)

    trajectories = ["circular", "linear", "random", "static"]

    for trajectory in trajectories:
        print(f"\nDemonstrating {trajectory} trajectory...")
        cap = MockCameraForHOG(num_frames=30, trajectory=trajectory, num_humans=2)

        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow(f"Mock Camera - {trajectory}", frame)

            key = cv2.waitKey(100)
            if key & 0xFF == ord('q'):
                break

            frame_count += 1

        cap.release()
        print(f"  Generated {frame_count} frames")

    cv2.destroyAllWindows()
    print("\nDemo complete!")


if __name__ == "__main__":
    demo_mock_camera()
