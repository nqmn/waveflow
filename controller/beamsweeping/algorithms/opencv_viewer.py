"""OpenCV Camera Viewer with Network Visualization

Displays AP, RIS, and UE positions overlaid on the camera feed.
Converts world coordinates to camera frame, then projects to 2D image.

Features:
- Real-time visualization of network geometry
- ArUco marker detection for UE position
- World-to-camera coordinate transformation
- 3D-to-2D perspective projection
- Colored markers and connecting lines
- Text overlays with coordinates
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import logging
import numpy as np
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class OpenCVCameraViewer:
    """Visualize AP, RIS, UE positions in camera feed with coordinate transforms."""

    def __init__(self, K: np.ndarray, dist: np.ndarray,
                 r_cw: np.ndarray, t_cw: np.ndarray):
        """Initialize viewer with camera calibration and world transform.

        Args:
            K: Camera intrinsic matrix (3, 3)
            dist: Distortion coefficients (4,) or (5,)
            r_cw: Rotation matrix camera-to-world (3, 3)
            t_cw: Translation vector camera-to-world (3,)
        """
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV (cv2) required for camera viewer")

        self.K = np.array(K, dtype=np.float32)
        self.dist = np.array(dist, dtype=np.float32)
        self.r_cw = np.array(r_cw, dtype=np.float64)
        self.t_cw = np.array(t_cw, dtype=np.float64)

        # Compute inverse transform: world-to-camera
        self.r_wc = self.r_cw.T  # Inverse rotation
        self.t_wc = -self.r_wc @ self.t_cw  # Inverse translation

    def world_to_camera(self, p_world: np.ndarray) -> np.ndarray:
        """Transform point from world frame to camera frame.

        Args:
            p_world: Point in world coordinates (3,)

        Returns:
            Point in camera coordinates (3,)
        """
        p_world = np.array(p_world).flatten()
        p_cam = self.r_wc @ p_world + self.t_wc
        return p_cam

    def project_to_image(self, p_cam: np.ndarray) -> Optional[Tuple[int, int]]:
        """Project 3D camera point to 2D image coordinates.

        Args:
            p_cam: Point in camera frame (3,)

        Returns:
            (u, v) pixel coordinates or None if behind camera
        """
        p_cam = np.array(p_cam).flatten()

        # Point must be in front of camera (z > 0)
        if p_cam[2] <= 0:
            return None

        # Project using camera intrinsics
        p_cam_h = p_cam.reshape(3, 1)  # Homogeneous coordinates
        p_img_h = self.K @ p_cam_h
        p_img = p_img_h[:2] / p_img_h[2]  # Normalize by depth

        u, v = int(p_img[0, 0]), int(p_img[1, 0])
        return (u, v)

    def draw_point(self, frame: np.ndarray, uv: Tuple[int, int],
                   label: str, color: Tuple[int, int, int],
                   radius: int = 8, thickness: int = -1) -> None:
        """Draw a labeled point on the frame.

        Args:
            frame: Image frame to draw on
            uv: (u, v) pixel coordinates
            label: Text label
            color: BGR color tuple
            radius: Circle radius in pixels
            thickness: Fill thickness (-1 for filled)
        """
        h, w = frame.shape[:2]

        # Clamp to image bounds
        u, v = uv
        if not (0 <= u < w and 0 <= v < h):
            return  # Outside image

        # Draw circle
        cv2.circle(frame, uv, radius, color, thickness)

        # Draw label offset from circle
        label_pos = (u + radius + 5, v - 5)
        cv2.putText(frame, label, label_pos, cv2.FONT_HERSHEY_SIMPLEX,
                   0.5, color, 1, cv2.LINE_AA)

    def draw_line(self, frame: np.ndarray, uv1: Tuple[int, int],
                  uv2: Tuple[int, int], color: Tuple[int, int, int],
                  thickness: int = 2) -> None:
        """Draw a line between two points.

        Args:
            frame: Image frame to draw on
            uv1: First point (u, v)
            uv2: Second point (u, v)
            color: BGR color tuple
            thickness: Line thickness in pixels
        """
        h, w = frame.shape[:2]

        u1, v1 = uv1
        u2, v2 = uv2

        # Check if both points are in bounds
        if (0 <= u1 < w and 0 <= v1 < h and 0 <= u2 < w and 0 <= v2 < h):
            cv2.line(frame, uv1, uv2, color, thickness, cv2.LINE_AA)

    def draw_text(self, frame: np.ndarray, text: str, position: Tuple[int, int],
                  color: Tuple[int, int, int] = (255, 255, 255),
                  font_scale: float = 0.5, thickness: int = 1) -> None:
        """Draw text on frame.

        Args:
            frame: Image frame to draw on
            text: Text to display
            position: (x, y) pixel position
            color: BGR color tuple
            font_scale: Font size scale
            thickness: Text thickness
        """
        cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX,
                   font_scale, color, thickness, cv2.LINE_AA)

    def _draw_grid(self, frame: np.ndarray, grid_spacing: int = 50) -> None:
        """Draw reference grid on frame.

        Args:
            frame: Image frame to draw on
            grid_spacing: Pixel spacing between grid lines
        """
        h, w = frame.shape[:2]
        grid_color = (200, 200, 200)  # Light gray
        grid_thickness = 1

        # Draw vertical lines
        for x in range(0, w, grid_spacing):
            cv2.line(frame, (x, 0), (x, h), grid_color, grid_thickness)

        # Draw horizontal lines
        for y in range(0, h, grid_spacing):
            cv2.line(frame, (0, y), (w, y), grid_color, grid_thickness)

    def visualize(self, frame: np.ndarray, ap_pos: np.ndarray, ris_pos: np.ndarray,
                  ue_pos: Optional[np.ndarray] = None,
                  show_coordinates: bool = True, show_grid: bool = True) -> np.ndarray:
        """Visualize AP, RIS, and UE positions on camera frame.

        Args:
            frame: Input camera frame (H, W, 3)
            ap_pos: AP position in world coordinates (3,)
            ris_pos: RIS position in world coordinates (3,)
            ue_pos: UE position in world coordinates (3,) or None if not detected
            show_coordinates: If True, display coordinate text overlays
            show_grid: If True, display reference grid

        Returns:
            Annotated frame with markers and lines
        """
        output = frame.copy()
        h, w = frame.shape[:2]

        # Draw reference grid if enabled
        if show_grid:
            self._draw_grid(output, grid_spacing=50)

        # Convert world positions to camera frame
        ap_cam = self.world_to_camera(ap_pos)
        ris_cam = self.world_to_camera(ris_pos)
        ue_cam = self.world_to_camera(ue_pos) if ue_pos is not None else None

        # Project to image
        ap_uv = self.project_to_image(ap_cam)
        ris_uv = self.project_to_image(ris_cam)
        ue_uv = self.project_to_image(ue_cam) if ue_cam is not None else None

        # Draw AP (blue)
        if ap_uv is not None:
            self.draw_point(output, ap_uv, "AP", (255, 0, 0), radius=8)

        # Draw RIS (red)
        if ris_uv is not None:
            self.draw_point(output, ris_uv, "RIS", (0, 0, 255), radius=8)

        # Draw UE (black) and connecting lines
        if ue_uv is not None:
            self.draw_point(output, ue_uv, "UE", (0, 0, 0), radius=8)

            # Draw lines: AP → RIS → UE
            if ap_uv is not None and ris_uv is not None:
                self.draw_line(output, ap_uv, ris_uv, (255, 255, 255), thickness=2)

            if ris_uv is not None:
                self.draw_line(output, ris_uv, ue_uv, (0, 255, 255), thickness=2)

        # Draw coordinate text overlays
        if show_coordinates:
            text_y = 30
            text_x = 10

            # AP world position
            if ap_uv is not None:
                ap_text = f"AP world = ({ap_pos[0]:.2f}, {ap_pos[1]:.2f}, {ap_pos[2]:.2f})"
                self.draw_text(output, ap_text, (text_x, text_y), color=(255, 0, 0))
                text_y += 25

            # RIS world position
            if ris_uv is not None:
                ris_text = f"RIS world = ({ris_pos[0]:.2f}, {ris_pos[1]:.2f}, {ris_pos[2]:.2f})"
                self.draw_text(output, ris_text, (text_x, text_y), color=(0, 0, 255))
                text_y += 25

            # UE world and camera positions
            if ue_uv is not None:
                ue_text = f"UE world = ({ue_pos[0]:.2f}, {ue_pos[1]:.2f}, {ue_pos[2]:.2f})"
                self.draw_text(output, ue_text, (text_x, text_y), color=(0, 0, 0))
                text_y += 25

                ue_cam_text = f"UE cam = ({ue_cam[0]:.2f}, {ue_cam[1]:.2f}, {ue_cam[2]:.2f})"
                self.draw_text(output, ue_cam_text, (text_x, text_y), color=(0, 0, 0))
                text_y += 25

                # Distance from camera to UE
                dist_cam_to_ue = np.linalg.norm(ue_cam)
                dist_text = f"Distance = {dist_cam_to_ue:.2f}m"
                self.draw_text(output, dist_text, (text_x, text_y), color=(200, 200, 200))

        return output


def run_camera_viewer(camera_id: int = 0,
                      ap_pos: np.ndarray = None,
                      ris_pos: np.ndarray = None,
                      K: Optional[np.ndarray] = None,
                      dist: Optional[np.ndarray] = None,
                      r_cw: Optional[np.ndarray] = None,
                      t_cw: Optional[np.ndarray] = None,
                      aruco_dict_type: str = "DICT_4X4_50",
                      marker_size: float = 0.05) -> None:
    """Run interactive camera viewer with network visualization.

    Displays AP, RIS, and UE positions overlaid on camera feed.
    Press 'q' to exit.

    Args:
        camera_id: Camera device ID
        ap_pos: AP position in world coordinates (3,)
        ris_pos: RIS position in world coordinates (3,)
        K: Camera intrinsic matrix (default: standard values)
        dist: Distortion coefficients (default: zero)
        r_cw: Rotation matrix camera-to-world
        t_cw: Translation vector camera-to-world
        aruco_dict_type: ArUco dictionary type
        marker_size: Physical marker size in meters
    """
    if not CV2_AVAILABLE:
        raise ImportError("OpenCV (cv2) required")

    # Validate inputs
    if r_cw is None or t_cw is None:
        raise ValueError("Camera-to-world transformation (r_cw, t_cw) required")

    if ap_pos is None or ris_pos is None:
        raise ValueError("AP and RIS positions required")

    # Default camera calibration
    if K is None:
        K = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=np.float32)
    if dist is None:
        dist = np.zeros((4, 1), dtype=np.float32)

    # Initialize viewer
    viewer = OpenCVCameraViewer(K, dist, r_cw, t_cw)

    # Initialize camera and ArUco
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera {camera_id}")

    aruco_dict = cv2.aruco.getPredefinedDictionary(
        getattr(cv2.aruco, aruco_dict_type)
    )
    detector = cv2.aruco.ArucoDetector(aruco_dict)

    logger.info(
        "\nCamera Viewer - Network Visualization\nAP: %s\nRIS: %s\nPress 'q' to exit",
        ap_pos,
        ris_pos,
    )

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Detect UE marker
            ue_pos = None
            corners, ids, _ = detector.detectMarkers(frame)

            if ids is not None and len(ids) > 0:
                rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                    corners, marker_size, K, dist
                )
                rvec = rvec[0]
                tvec = tvec[0]

                # Transform to world coordinates
                r_cw = np.array(r_cw, dtype=np.float64)
                t_cw = np.array(t_cw, dtype=np.float64)
                ue_cam = tvec.flatten()
                ue_pos = r_cw @ ue_cam + t_cw

            # Visualize
            output = viewer.visualize(frame, ap_pos, ris_pos, ue_pos, show_coordinates=True)

            # Display
            cv2.imshow("Network Visualization", output)

            # Exit on 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    # Example usage
    import numpy as np

    # Example positions (meters)
    ap_pos = np.array([0.0, 0.0, 1.0])
    ris_pos = np.array([5.0, 0.0, 1.0])

    # Example camera-to-world transform
    r_cw = np.array([
        [1, 0, 0],
        [0, 0, -1],
        [0, 1, 0]
    ], dtype=np.float64)
    t_cw = np.array([2.5, 1.0, 0.0], dtype=np.float64)

    # Run viewer
    try:
        run_camera_viewer(
            camera_id=0,
            ap_pos=ap_pos,
            ris_pos=ris_pos,
            r_cw=r_cw,
            t_cw=t_cw,
            marker_size=0.05
        )
    except Exception as e:
        logger.error("Error: %s", e)
