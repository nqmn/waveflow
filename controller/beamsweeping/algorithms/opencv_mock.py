"""Mock Camera for Testing OpenCV Vision Sweep Algorithm

Generates synthetic camera frames with simulated ArUco markers at different positions.
Useful for testing without physical camera hardware.

Features:
- Synthetic frame generation (blank images with noise)
- Simulated ArUco markers with pose variation
- Configurable marker positions and trajectories
- Support for circular motion, linear motion, or random positions
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import numpy as np
from typing import Optional, Tuple, List


class MockCamera:
    """Mock camera that generates frames with simulated ArUco markers."""

    def __init__(self, width: int = 640, height: int = 480,
                 marker_trajectory: str = "circular",
                 num_frames: int = 100,
                 center_x: float = 320,
                 center_y: float = 240,
                 radius: float = 50):
        """Initialize mock camera.

        Args:
            width: Frame width in pixels
            height: Frame height in pixels
            marker_trajectory: Type of motion ('circular', 'linear', 'random', 'static')
            num_frames: Total number of frames to generate
            center_x: Center X for circular motion
            center_y: Center Y for circular motion
            radius: Radius of circular motion (pixels)
        """
        self.width = width
        self.height = height
        self.frame_count = 0
        self.num_frames = num_frames
        self.is_open = True

        self.trajectory = marker_trajectory
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius

        print(f"MockCamera initialized: {width}x{height}, {num_frames} frames")
        print(f"Trajectory: {marker_trajectory}")

    def isOpened(self) -> bool:
        """Check if camera is still generating frames."""
        return self.is_open and self.frame_count < self.num_frames

    def read(self) -> Tuple[bool, np.ndarray]:
        """Read next frame with simulated ArUco marker.

        Returns:
            Tuple of (success, frame) where frame contains a simulated marker
        """
        if not self.isOpened():
            self.is_open = False
            return False, None

        # Generate blank frame
        frame = self._generate_frame()

        # Get marker position for this frame
        marker_x, marker_y = self._get_marker_position(self.frame_count)

        # Draw ArUco marker (simulated as a square with ID)
        self._draw_aruco_marker(frame, marker_x, marker_y, marker_id=0)

        self.frame_count += 1
        return True, frame

    def release(self) -> None:
        """Release camera resources."""
        self.is_open = False

    def _generate_frame(self) -> np.ndarray:
        """Generate a blank camera frame with noise.

        Returns:
            RGB frame (H, W, 3)
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV required for mock camera")

        # Create white background
        frame = np.ones((self.height, self.width, 3), dtype=np.uint8) * 200

        # Add some noise to make it look realistic
        noise = np.random.randint(0, 20, frame.shape, dtype=np.uint8)
        frame = cv2.add(frame, noise.astype(np.uint8))

        # Add some texture (horizontal lines)
        for y in range(0, self.height, 20):
            cv2.line(frame, (0, y), (self.width, y), (180, 180, 180), 1)

        return frame

    def _get_marker_position(self, frame_idx: int) -> Tuple[float, float]:
        """Get marker position based on trajectory type.

        Args:
            frame_idx: Current frame index

        Returns:
            (x, y) position in pixels
        """
        if self.trajectory == "circular":
            # Circular motion
            angle = 2 * np.pi * frame_idx / self.num_frames
            x = self.center_x + self.radius * np.cos(angle)
            y = self.center_y + self.radius * np.sin(angle)
            return x, y

        elif self.trajectory == "linear":
            # Linear motion left to right
            x = 100 + (self.width - 200) * frame_idx / self.num_frames
            y = self.height / 2
            return x, y

        elif self.trajectory == "random":
            # Random position within safe bounds
            x = np.random.uniform(50, self.width - 50)
            y = np.random.uniform(50, self.height - 50)
            return x, y

        elif self.trajectory == "static":
            # Static position (center)
            return self.center_x, self.center_y

        else:
            raise ValueError(f"Unknown trajectory: {self.trajectory}")

    def _draw_aruco_marker(self, frame: np.ndarray, x: float, y: float,
                          marker_id: int = 0, size: int = 40) -> None:
        """Draw a simulated ArUco marker on frame.

        Args:
            frame: Frame to draw on
            x: Center X position
            y: Center Y position
            marker_id: Marker ID (for label)
            size: Marker size in pixels
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV required for mock camera")

        # Draw marker square (black outline, white fill)
        x, y = int(x), int(y)
        half_size = size // 2

        top_left = (x - half_size, y - half_size)
        bottom_right = (x + half_size, y + half_size)

        # Draw filled square (white background)
        cv2.rectangle(frame, top_left, bottom_right, (255, 255, 255), -1)

        # Draw border (black)
        cv2.rectangle(frame, top_left, bottom_right, (0, 0, 0), 3)

        # Draw internal pattern (simulating ArUco pattern)
        quarter = size // 4
        cv2.rectangle(frame, (x - quarter, y - quarter), (x + quarter, y + quarter),
                     (0, 0, 0), -1)

        # Draw ID label
        cv2.putText(frame, f"ID:{marker_id}", (x - 20, y + 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # Add corner markers for detection (small circles)
        corners = [
            (x - half_size, y - half_size),  # Top-left
            (x + half_size, y - half_size),  # Top-right
            (x + half_size, y + half_size),  # Bottom-right
            (x - half_size, y + half_size),  # Bottom-left
        ]
        for corner in corners:
            cv2.circle(frame, corner, 3, (0, 0, 255), -1)


class MockPoseEstimator:
    """Mock pose estimator that simulates ArUco pose detection.

    Instead of using cv2.aruco.estimatePoseSingleMarkers, this generates
    synthetic pose data based on marker position in image.
    """

    def __init__(self, K: np.ndarray, marker_size: float = 0.05,
                 camera_distance: float = 3.0):
        """Initialize mock pose estimator.

        Args:
            K: Camera intrinsic matrix (3, 3)
            marker_size: Physical marker size in meters
            camera_distance: Distance from camera to marker (meters)
        """
        self.K = np.array(K, dtype=np.float32)
        self.marker_size = marker_size
        self.camera_distance = camera_distance

    def estimate_pose(self, marker_pixel_x: float, marker_pixel_y: float,
                     frame_width: int, frame_height: int,
                     noise_level: float = 0.01) -> Tuple[np.ndarray, np.ndarray]:
        """Estimate pose of marker based on pixel position.

        Args:
            marker_pixel_x: Marker X in pixels
            marker_pixel_y: Marker Y in pixels
            frame_width: Image width
            frame_height: Image height
            noise_level: Noise level for realistic variation

        Returns:
            Tuple of (rvec, tvec) for pose estimation
        """
        # Normalize pixel coordinates to [-1, 1]
        cx = self.K[0, 2]
        cy = self.K[1, 2]
        fx = self.K[0, 0]
        fy = self.K[1, 1]

        x_norm = (marker_pixel_x - cx) / fx
        y_norm = (marker_pixel_y - cy) / fy

        # Convert to 3D camera coordinates (at fixed distance)
        z_cam = self.camera_distance
        x_cam = x_norm * z_cam
        y_cam = y_norm * z_cam

        # Add noise
        noise = np.random.randn(3) * noise_level
        tvec = np.array([x_cam, y_cam, z_cam]) + noise

        # Pose is typically upright (small rotation)
        rvec = np.array([0.1 * np.random.randn(), 0.1 * np.random.randn(),
                        0.1 * np.random.randn()])

        return rvec, tvec


def create_mock_camera(trajectory: str = "circular",
                       num_frames: int = 100,
                       width: int = 640,
                       height: int = 480) -> MockCamera:
    """Create a mock camera for testing.

    Args:
        trajectory: Motion type ('circular', 'linear', 'random', 'static')
        num_frames: Number of frames to generate
        width: Frame width
        height: Frame height

    Returns:
        MockCamera instance
    """
    return MockCamera(width=width, height=height,
                     marker_trajectory=trajectory,
                     num_frames=num_frames)


def demo_mock_camera():
    """Demonstrate mock camera functionality."""
    if not CV2_AVAILABLE:
        print("OpenCV required for demo")
        return

    print("\n" + "="*70)
    print("MOCK CAMERA DEMONSTRATION")
    print("="*70)

    # Create mock camera with circular motion
    mock_cam = create_mock_camera(trajectory="circular", num_frames=30)

    print("\nGenerating frames with circular marker motion...")
    print("Press 'q' to exit, any other key to next frame\n")

    frame_count = 0
    while mock_cam.isOpened():
        ret, frame = mock_cam.read()
        if not ret:
            break

        frame_count += 1

        # Display frame
        cv2.imshow("Mock Camera - Circular Motion", frame)

        key = cv2.waitKey(500) & 0xFF
        if key == ord('q'):
            break

        if frame_count % 10 == 0:
            print(f"  Frame {frame_count}/{mock_cam.num_frames}")

    mock_cam.release()
    cv2.destroyAllWindows()

    print(f"\nGenerated {frame_count} frames successfully!")

    # Demonstrate pose estimation
    print("\n" + "="*70)
    print("MOCK POSE ESTIMATOR DEMONSTRATION")
    print("="*70)

    K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float32)
    estimator = MockPoseEstimator(K, marker_size=0.05, camera_distance=3.0)

    print("\nEstimating pose for marker at different pixel positions:")
    positions = [(320, 240), (200, 200), (450, 300), (100, 400)]

    for px, py in positions:
        rvec, tvec = estimator.estimate_pose(px, py, 640, 480)
        print(f"  Pixel ({px:3d}, {py:3d}) → tvec: ({tvec[0]:.3f}, {tvec[1]:.3f}, {tvec[2]:.3f})")

    print("\n" + "="*70)


if __name__ == '__main__':
    demo_mock_camera()
