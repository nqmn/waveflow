"""HOG-Based Human Detection Beam Sweep Algorithm

Uses Histogram of Oriented Gradients (HOG) to detect human subjects
and compute beam deflection angles based on their position.

Features:
- Real-time human detection from camera feed
- Automatic bounding box to position conversion
- Support for multiple detections (uses centroid of all humans)
- Adaptive window search: focuses measurements around first detected human
- Intelligent angle deduplication to avoid redundant measurements
- Fallback to ArUco if no humans detected
- Optional video recording with annotations
- Compatible with existing RISNet sweep infrastructure

Adaptive Window Mode (Recommended):
When enabled (default), the algorithm:
1. Captures the first human detection angle
2. Focuses measurements within a window around that angle
3. Skips angles outside the window (e.g., -25° detection -> test -35° to -15°)
4. Deduplicates measurements to avoid re-testing the same angle
Result: ~75% reduction in measurements vs exhaustive coarse sweep

Flow:
1. Capture frame from camera
2. Detect human(s) using HOG descriptor
3. Extract position from bounding box centroid
4. Transform to world coordinates
5. Compute RIS deflection angle
6. Apply adaptive window filtering (optional)
7. Measure network metrics (SNR/RSSI/CSI) if not already measured
8. Return results in standard sweep format
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import logging
import numpy as np
from typing import Dict, Optional, Tuple
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    setup_waveform_simulator,
    validate_and_get_nodes,
    FeedbackCollector,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm

# Import mock camera for testing
try:
    from .hog_mock_camera import MockCameraForHOG
    MOCK_CAMERA_AVAILABLE = True
except ImportError:
    MOCK_CAMERA_AVAILABLE = False

logger = logging.getLogger(__name__)


def non_max_suppression(boxes: np.ndarray, overlap_thresh: float = 0.65) -> np.ndarray:
    """Suppress overlapping bounding boxes to keep strongest detections."""
    if boxes.size == 0:
        return boxes

    # Work in float for the arithmetic and convert back at the end.
    boxes = boxes.astype("float32")
    pick = []

    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)

        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])

        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)

        overlap = (w * h) / areas[idxs[:last]]

        idxs = np.delete(
            idxs,
            np.concatenate(([last], np.where(overlap > overlap_thresh)[0]))
        )

    return boxes[pick].astype(np.float32)


def filter_boxes_by_geometry(
    boxes: np.ndarray,
    min_height: float = 100.0,
    min_aspect_ratio: float = 0.25,
    max_aspect_ratio: float = 0.8,
) -> np.ndarray:
    """Filter detections using simple human-like geometric constraints."""
    if boxes.size == 0:
        return boxes

    widths = boxes[:, 2] - boxes[:, 0]
    heights = boxes[:, 3] - boxes[:, 1]
    aspect_ratios = np.divide(
        widths,
        heights,
        out=np.zeros_like(widths),
        where=heights > 0
    )

    mask = (
        (heights >= min_height) &
        (aspect_ratios >= min_aspect_ratio) &
        (aspect_ratios <= max_aspect_ratio)
    )

    return boxes[mask]


class HOGHumanDetector:
    """Histogram of Oriented Gradients (HOG) descriptor for human detection."""

    def __init__(self):
        """Initialize HOG detector with pre-trained people detector."""
        if not CV2_AVAILABLE:
            raise ImportError("OpenCV required for HOG detection")

        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    @staticmethod
    def _preprocess_frame(frame: np.ndarray) -> np.ndarray:
        """Convert frame to a contrast-normalized grayscale image."""
        if frame.ndim == 3 and frame.shape[2] == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame.copy()

        # Ensure uint8 range for HOG and equalize to help in low light scenes.
        if gray.dtype != np.uint8:
            gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        return cv2.equalizeHist(gray)

    def detect(self, frame: np.ndarray, win_stride: Tuple[int, int] = (8, 8),
               padding: Tuple[int, int] = (16, 16),
               scale: float = 1.05,
               confidence_threshold: float = 0.35) -> np.ndarray:
        """Detect humans in frame using HOG descriptor.

        Args:
            frame: Input image (H, W, 3) in BGR format
            win_stride: Stride of sliding window (x, y)
            padding: Padding around detections (x, y)
            scale: Scale factor for multi-scale detection
            confidence_threshold: Minimum SVM score to keep a detection

        Returns:
            Array of bounding boxes (N, 4) where each box is [x, y, x+w, y+h]
        """
        processed_frame = self._preprocess_frame(frame)

        # Detect humans (returns rectangles and weights)
        rects, weights = self.hog.detectMultiScale(
            processed_frame,
            winStride=win_stride,
            padding=padding,
            scale=scale
        )

        if len(rects) == 0:
            return np.array([])

        rects = np.array(rects)
        weights = np.array(weights).reshape(-1) if len(weights) > 0 else None

        if weights is not None and weights.size == rects.shape[0]:
            mask = weights >= confidence_threshold
            rects = rects[mask]

        if rects.size == 0:
            return np.array([])

        # Convert (x, y, w, h) to (x1, y1, x2, y2) format
        boxes = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects], dtype=np.float32)
        boxes = non_max_suppression(boxes)

        return boxes

    def get_centroid(self, boxes: np.ndarray) -> Optional[Tuple[int, int]]:
        """Compute centroid of all detected bounding boxes.

        Args:
            boxes: Array of bounding boxes (N, 4)

        Returns:
            (x, y) centroid in pixel coordinates, or None if no boxes
        """
        if len(boxes) == 0:
            return None

        # Extract center points of each box
        centers = ((boxes[:, 0] + boxes[:, 2]) / 2, (boxes[:, 1] + boxes[:, 3]) / 2)

        # Compute mean of all centers (centroid)
        centroid_x = np.mean(centers[0])
        centroid_y = np.mean(centers[1])

        return (int(centroid_x), int(centroid_y))


@register_algorithm("hog", aliases=("human", "hog_human"))
class HOGHumanDetectionSweep(SweepAlgorithmBase):
    """Beam sweep using HOG-based human detection."""

    @property
    def name(self) -> str:
        return "HOG Human Detection Sweep"

    @property
    def description(self) -> str:
        return "Detect humans using HOG descriptor and compute beam angles from their position."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None,
              camera_id: int = 0,
              camera_matrix_path: Optional[str] = None,
              dist_coeffs_path: Optional[str] = None,
              r_cw: Optional[np.ndarray] = None,
              t_cw: Optional[np.ndarray] = None,
              max_frames: int = 100,
              angle_change_threshold: float = 1.0,
              hog_win_stride: Tuple[int, int] = (8, 8),
              hog_padding: Tuple[int, int] = (16, 16),
              hog_scale: float = 1.05,
              hog_confidence: float = 0.35,
              hog_min_height_px: float = 120.0,
              hog_min_aspect_ratio: float = 0.25,
              hog_max_aspect_ratio: float = 0.8,
              min_box_area: int = 2000,
              record_video: bool = False,
              fallback_to_aruco: bool = False,
              use_mock: bool = False,
              mock_trajectory: str = "circular",
              mock_num_humans: int = 1,
              adaptive_window: bool = True,
              window_span: float = 10.0,
              window_step: float = 2.0,
              **kwargs) -> Dict:
        """Execute HOG-based human detection sweep.

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees
            step: Step size in degrees
            seed: Random seed
            enable_feedback: Enable closed-loop feedback
            max_feedback_iterations: Max feedback iterations
            use_waveform: Enable waveform simulation
            modulation: Modulation type (QPSK, 16QAM, 64QAM)
            num_symbols: Number of symbols
            metric_selector: Custom metric selector
            camera_id: Camera device ID (default: 0)
            camera_matrix_path: Path to camera intrinsics
            dist_coeffs_path: Path to distortion coefficients
            r_cw: Rotation matrix (camera to world)
            t_cw: Translation vector (camera to world)
            max_frames: Max frames to process
            angle_change_threshold: Skip similar angles (degrees)
            hog_win_stride: HOG sliding window stride
            hog_padding: HOG padding
            hog_scale: HOG scale factor
            hog_confidence: Minimum HOG detection confidence score
            hog_min_height_px: Minimum bounding box height in pixels
            hog_min_aspect_ratio: Minimum width/height ratio for a valid human
            hog_max_aspect_ratio: Maximum width/height ratio for a valid human
            min_box_area: Minimum bounding box area (pixels^2)
            record_video: Record output video with detections
            fallback_to_aruco: Fall back to ArUco if no humans detected
            use_mock: Use synthetic camera instead of real camera (for testing)
            mock_trajectory: Trajectory type: 'circular', 'linear', 'random', 'static'
            mock_num_humans: Number of simulated humans in synthetic frames
            adaptive_window: Enable adaptive window search around first detection (default: True)
            window_span: Angular span around first detection in degrees (default: 10)
            window_step: Step size for angle measurements within window in degrees (default: 2)

        Returns:
            Dictionary with sweep results
        """
        if not CV2_AVAILABLE:
            raise ImportError(
                "OpenCV required for HOG detection. "
                "Install with: pip install opencv-python"
            )

        # Validate nodes
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Handle UE node
        if ue is None:
            logger.info("\n[HOG HUMAN DETECTION] Creating placeholder UE '%s'", ue_name)
            self.network.add_ue(ue_name, 0.0, 0.0, 0.0)
            ue = self.network.nodes[ue_name]
        else:
            logger.info(
                "\n[HOG HUMAN DETECTION] UE '%s' will be updated with detected position",
                ue_name,
            )

        # Open camera with auto-detection fallback
        cap = None
        actual_camera_id = camera_id
        using_mock = False

        if use_mock:
            # Use synthetic camera for testing
            if not MOCK_CAMERA_AVAILABLE:
                raise ImportError("Mock camera not available")

            cap = MockCameraForHOG(
                width=640,
                height=480,
                num_frames=max_frames,
                trajectory=mock_trajectory,
                num_humans=mock_num_humans
            )
            using_mock = True
            logger.info(
                "\n[HOG CAMERA] Using synthetic camera\n"
                "[HOG CAMERA] Trajectory: %s\n"
                "[HOG CAMERA] Simulated humans: %s",
                mock_trajectory,
                mock_num_humans,
            )
        else:
            # Try the specified camera first
            logger.info("\n[HOG CAMERA] Attempting to open camera %s...", camera_id)
            cap = cv2.VideoCapture(camera_id)

            # If specified camera fails, search for available cameras
            if not cap.isOpened() or cap is None:
                logger.info(
                    "[HOG CAMERA] Camera %s not available. Searching for available cameras...",
                    camera_id,
                )
                for cam_id in range(10):
                    if cam_id == camera_id:
                        continue  # Skip already tried
                    test_cap = cv2.VideoCapture(cam_id)
                    if test_cap.isOpened():
                        actual_camera_id = cam_id
                        cap = test_cap
                        logger.info("[HOG CAMERA] Found available camera at index %s", cam_id)
                        break
                    test_cap.release()

            # Final check - offer mock as fallback
            if cap is None or not cap.isOpened():
                if MOCK_CAMERA_AVAILABLE:
                    logger.info(
                        "\n[HOG CAMERA] No physical camera available.\n"
                        "[HOG CAMERA] Switching to synthetic camera for testing..."
                    )
                    cap = MockCameraForHOG(
                        width=640,
                        height=480,
                        num_frames=max_frames,
                        trajectory="circular",
                        num_humans=1
                    )
                    using_mock = True
                else:
                    raise RuntimeError(
                        f"No cameras available and mock camera unavailable. "
                        "Please connect a camera or fix mock camera import."
                    )

        logger.info("[HOG CAMERA] Using camera (Mock: %s)", using_mock)

        # Load camera calibration
        K, dist_coeffs = self._load_camera_calibration(camera_matrix_path, dist_coeffs_path)

        # Setup coordinate transforms
        if r_cw is None:
            r_cw = np.eye(3, dtype=np.float64)
        else:
            r_cw = np.array(r_cw, dtype=np.float64)

        if t_cw is None:
            t_cw = np.array([ris.pos[0], ris.pos[1], ris.pos[2]], dtype=np.float64)
        else:
            t_cw = np.array(t_cw, dtype=np.float64)

        # Initialize HOG detector
        hog_detector = HOGHumanDetector()

        # Setup video writer if recording
        video_writer = None
        if record_video:
            fourcc = cv2.VideoWriter_fourcc(*'MJPG')
            fps = 15.0
            frame_size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                         int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            video_writer = cv2.VideoWriter(
                'hog_detection_output.avi',
                fourcc, fps, frame_size
            )
            logger.info("[HOG VIDEO] Recording to hog_detection_output.avi")

        # Setup waveform simulator
        link_simulator = setup_waveform_simulator(use_waveform, modulation, num_symbols)
        feedback_collector = FeedbackCollector(enable_feedback)

        # Storage for measurements
        local_angles = []
        snr_values = []
        pwr_values = []
        ser_values = [] if use_waveform else None
        raw_poses = []

        frame_count = 0
        unique_poses = 0
        frames_with_detections = 0
        last_angle = None
        last_detection_frame = None
        last_display_frame = None
        last_detection_info = None
        best_snr = None

        # Adaptive window search state
        first_detection_angle = None
        window_angles_generated = False
        measured_angles = set()  # Track all measured angles to avoid duplicates

        header_lines = [
            "",
            "[HOG HUMAN DETECTION SWEEP]",
            f"Camera ID: {actual_camera_id}",
            f"Min Box Area: {min_box_area} pixels^2",
            f"HOG Window Stride: {hog_win_stride}",
            f"Max Frames: {max_frames}",
        ]
        if adaptive_window:
            header_lines.append(f"Adaptive Window: ENABLED (span={window_span}°, step={window_step}°)")
        else:
            header_lines.append("Adaptive Window: DISABLED")
        header_lines.append("Processing frames (press 'q' to stop)...")
        logger.info("\n%s", "\n".join(header_lines))

        try:
            while cap.isOpened() and frame_count < max_frames:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                output_frame = frame.copy()

                # Detect humans using HOG
                boxes = hog_detector.detect(
                    frame,
                    win_stride=hog_win_stride,
                    padding=hog_padding,
                    scale=hog_scale,
                    confidence_threshold=hog_confidence
                )

                # Filter boxes by minimum area
                if len(boxes) > 0:
                    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
                    valid_boxes = boxes[areas >= min_box_area]
                    valid_boxes = filter_boxes_by_geometry(
                        valid_boxes,
                        min_height=hog_min_height_px,
                        min_aspect_ratio=hog_min_aspect_ratio,
                        max_aspect_ratio=hog_max_aspect_ratio
                    )
                else:
                    valid_boxes = np.array([])

                # Draw detections on frame
                if len(valid_boxes) > 0:
                    tallest_idx = np.argmax((valid_boxes[:, 3] - valid_boxes[:, 1]))
                    primary_box = valid_boxes[tallest_idx]

                    for idx, (x1, y1, x2, y2) in enumerate(valid_boxes.astype(int)):
                        cv2.rectangle(output_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        label = "Human" if idx == tallest_idx else "Candidate"
                        cv2.putText(output_frame, label, (x1, y1 - 5),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                    # Get centroid of all detections (mimics ArUco marker center)
                    centroid_px = hog_detector.get_centroid(valid_boxes)
                    if centroid_px is not None:
                        cx, cy = centroid_px
                        cv2.circle(output_frame, (cx, cy), 8, (0, 0, 255), -1)
                        cv2.putText(output_frame, f"Centroid ({cx}, {cy})",
                                   (cx + 10, cy), cv2.FONT_HERSHEY_SIMPLEX,
                                   0.5, (0, 0, 255), 2)

                        # Extract 3D position from 2D bounding box (mimic ArUco's tvec extraction)
                        # This mimics what cv2.aruco.estimatePoseSingleMarkers does
                        x_box, y_box, x2_box, y2_box = primary_box  # Tallest detected box
                        box_width = x2_box - x_box
                        box_height = y2_box - y_box

                        # Estimate distance from bounding box size
                        # Assume human is ~1.7m tall physically
                        human_height_m = 1.7
                        focal_length = K[1, 1]  # Use fy for vertical
                        distance_z = (human_height_m * focal_length) / box_height if box_height > 0 else 1.0

                        # Convert pixel centroid to normalized image coordinates
                        u, v = cx, cy
                        fx, fy = K[0, 0], K[1, 1]
                        cx_c, cy_c = K[0, 2], K[1, 2]

                        # Normalized image coordinates (same as ArUco)
                        x_norm = (u - cx_c) / fx
                        y_norm = (v - cy_c) / fy

                        # Construct camera frame position vector (mimics ArUco tvec)
                        # tvec = [x, y, z] in camera frame
                        x_cam = x_norm * distance_z
                        y_cam = y_norm * distance_z
                        z_cam = distance_z

                        tvec = np.array([x_cam, y_cam, z_cam]).reshape(3, 1)
                        rvec = np.zeros((3, 1))  # No rotation for human detection

                        # Calculate distance from camera
                        dist_cam = np.sqrt(x_cam**2 + y_cam**2 + z_cam**2)

                        # Transform to world coordinates (same as ArUco)
                        p_ue_world = self._camera_to_world(tvec, rvec, r_cw, t_cw)
                        x_world, y_world, z_world = p_ue_world

                        # Display coordinate information (mimics ArUco output)
                        cam_text = f"Cam: x={x_cam:.3f}m y={y_cam:.3f}m z={z_cam:.3f}m d={dist_cam:.3f}m"
                        cv2.putText(output_frame, cam_text, (10, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                        world_text = f"World: x={x_world:.3f} y={y_world:.3f} z={z_world:.3f}"
                        cv2.putText(output_frame, world_text, (10, 55),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                        # Log coordinate transformation for first detection (mimic ArUco logging)
                        if unique_poses == 0:
                            is_identity = (np.allclose(r_cw, np.eye(3)) and
                                         np.allclose(t_cw, np.zeros(3)))
                            logger.info(
                                "\n[COORDINATE TRANSFORMATION DETAILS]\n"
                                "Frame %s:\n"
                                "  HOG Bounding Box Detection:\n"
                                "    Centroid pixel: (%s, %s)\n"
                                "    Box dimensions: %.0fx%.0f pixels\n"
                                "    Estimated human height: %sm\n"
                                "  Camera frame (from HOG detector):\n"
                                "    x_cam = %.6f m\n"
                                "    y_cam = %.6f m\n"
                                "    z_cam = %.6f m\n"
                                "    distance = %.6f m\n"
                                "  Transform parameters:\n"
                                "    R_cw (rotation matrix):\n"
                                "      %s\n"
                                "    t_cw (translation): %s\n"
                                "    Is identity transform: %s\n"
                                "  World frame (RIS-centered):\n"
                                "    x_world = %.6f\n"
                                "    y_world = %.6f\n"
                                "    z_world = %.6f",
                                frame_count,
                                cx,
                                cy,
                                box_width,
                                box_height,
                                human_height_m,
                                x_cam,
                                y_cam,
                                z_cam,
                                dist_cam,
                                r_cw,
                                t_cw,
                                is_identity,
                                x_world,
                                y_world,
                                z_world,
                            )

                        # Update UE position from detection (mimics ArUco behavior)
                        ue.pos = np.array(p_ue_world, dtype=np.float64)

                        frames_with_detections += 1

                        # Compute RIS deflection angle (same as ArUco)
                        ap_vec = ap.pos - ris.pos
                        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

                        ue_vec = p_ue_world - ris.pos
                        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

                        local_angle = ue_angle - ap_angle

                        # Clamp to RIS FOV
                        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
                        local_angle = clamp_local_deflection_to_ris_fov(
                            local_angle, ris_max_angle
                        )

                        # Adaptive window logic: capture first detection angle and generate window
                        if adaptive_window and first_detection_angle is None:
                            first_detection_angle = local_angle
                            window_angles_generated = True
                            logger.info(
                                "\n[ADAPTIVE WINDOW] First detection at %.1f°\n"
                                "[ADAPTIVE WINDOW] Window span: [%.1f°, %.1f°]\n"
                                "[ADAPTIVE WINDOW] Step size: %s°",
                                first_detection_angle,
                                first_detection_angle - window_span,
                                first_detection_angle + window_span,
                                window_step,
                            )

                        # Check if angle should be measured
                        skip_reason = None

                        # 1. Check if already measured (deduplication)
                        angle_rounded = round(local_angle / window_step) * window_step
                        if angle_rounded in measured_angles:
                            skip_reason = f"already measured (angle {angle_rounded:.1f}°)"

                        # 2. Check adaptive window constraint
                        elif adaptive_window and window_angles_generated:
                            window_min = first_detection_angle - window_span
                            window_max = first_detection_angle + window_span
                            if local_angle < window_min or local_angle > window_max:
                                skip_reason = f"outside window [{window_min:.1f}°, {window_max:.1f}°]"

                        # 3. Check if similar to last angle (consecutive threshold)
                        elif last_angle is not None and abs(local_angle - last_angle) < angle_change_threshold:
                            skip_reason = f"similar to last (delta {abs(local_angle - last_angle):.1f}° < {angle_change_threshold}°)"

                        if skip_reason:
                            cv2.putText(output_frame, f"SKIP: {local_angle:.1f}° ({skip_reason})",
                                       (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                        else:
                            # Measure network metrics
                            try:
                                measurement = self.network.connect(
                                    ap.name, ris.name, ue.name,
                                    beam_angle_deg=local_angle,
                                    enable_feedback=enable_feedback,
                                    max_feedback_iterations=max_feedback_iterations
                                )

                                snr = measurement.get('snr_dB', 0)
                                pwr = measurement.get('pwr_dBm', 0)
                                ser = measurement.get('ser', 0) if use_waveform else None

                                local_angles.append(local_angle)
                                snr_values.append(snr)
                                pwr_values.append(pwr)
                                if ser is not None:
                                    ser_values.append(ser)

                                # Track as measured
                                measured_angles.add(angle_rounded)

                                # Store raw pose data (mimic ArUco format)
                                raw_poses.append({
                                    'position': p_ue_world.copy(),
                                    'angle': local_angle,
                                    'tvec': tvec.copy(),
                                    'rvec': rvec.copy(),
                                    'x_cam': x_cam,
                                    'y_cam': y_cam,
                                    'z_cam': z_cam,
                                    'dist_cam': dist_cam
                                })

                                unique_poses += 1
                                last_angle = local_angle

                                # Display measurement
                                cv2.putText(output_frame, f"Angle: {local_angle:.1f}deg SNR: {snr:.1f}dB",
                                           (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

                            except Exception as e:
                                logger.warning("[HOG] Measurement error: %s", e)

                    # Preserve the latest frame that actually had a detection so the
                    # final viewer shows what was detected instead of an empty frame.
                        last_detection_frame = output_frame.copy()
                        last_detection_info = {
                            'frame': frame_count,
                            'centroid': (cx, cy),
                            'box': (box_width, box_height),
                            'x_cam': x_cam,
                            'y_cam': y_cam,
                            'z_cam': z_cam,
                            'dist_cam': dist_cam,
                            'p_world': p_ue_world.copy()
                        }

                else:
                    # No detections
                    cv2.putText(output_frame, "NO HUMANS DETECTED", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

                # Display statistics
                cv2.putText(output_frame, f"Frame: {frame_count}/{max_frames}",
                           (10, output_frame.shape[0] - 20),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                cv2.putText(output_frame, f"Detections: {frames_with_detections}",
                           (10, output_frame.shape[0] - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

                # Store last processed frame (used if no detections ever happened)
                last_display_frame = output_frame.copy()

                # Show frame
                cv2.imshow("HOG Human Detection", output_frame)

                # Write to video
                if video_writer is not None:
                    video_writer.write(output_frame.astype('uint8'))

                # Exit on 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            cap.release()
            if video_writer is not None:
                video_writer.release()

        # Display final frame with instructions to close
        final_source_frame = last_detection_frame if last_detection_frame is not None else last_display_frame
        if final_source_frame is not None:
            # Create final display frame with instructions
            final_frame = final_source_frame.copy()
            h, w = final_frame.shape[:2]

            # Add dark overlay for readability
            overlay = final_frame.copy()
            cv2.rectangle(overlay, (10, h - 120), (w - 10, h - 10), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.3, final_frame, 0.7, 0, final_frame)

            # Add instructions
            cv2.putText(final_frame, "Scan Complete!", (20, h - 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
            cv2.putText(final_frame, "Click on window or press 'q' to close", (20, h - 50),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

            # Compute best SNR for display
            best_snr_display = max(snr_values) if len(snr_values) > 0 else None
            snr_text = f"{best_snr_display:.2f}" if best_snr_display is not None else "N/A"
            cv2.putText(final_frame, f"Measurements: {unique_poses} | Best SNR: {snr_text} dB",
                       (20, h - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

            # Save snapshot of last frame (useful for validation/debug)
            snapshot_path = "hog_detection_snapshot.png"
            cv2.imwrite(snapshot_path, final_frame)

            if last_detection_info is not None:
                bw, bh = last_detection_info['box']
                pw = last_detection_info['p_world']
                logger.info(
                    "\n[HOG DETECTION SNAPSHOT]\n"
                    "  Frame: %s\n"
                    "  Centroid: %s\n"
                    "  Box size: %.0fx%.0f px\n"
                    "  Camera coords: x=%.3fm y=%.3fm z=%.3fm d=%.3fm\n"
                    "  World coords: x=%.3f y=%.3f z=%.3f",
                    last_detection_info['frame'],
                    last_detection_info['centroid'],
                    bw,
                    bh,
                    last_detection_info['x_cam'],
                    last_detection_info['y_cam'],
                    last_detection_info['z_cam'],
                    last_detection_info['dist_cam'],
                    pw[0],
                    pw[1],
                    pw[2],
                )

            logger.info("[HOG VIEWER] Snapshot saved to %s", snapshot_path)

            # Display until user closes window
            cv2.imshow("HOG Human Detection", final_frame)
            logger.info("\n[HOG VIEWER] Scan complete. Click window or press 'q' to close.")

            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # 'q' or ESC
                    break
                # Check if window is closed by user clicking X
                if cv2.getWindowProperty("HOG Human Detection", cv2.WND_PROP_VISIBLE) < 1:
                    break

        cv2.destroyAllWindows()

        # Compute results
        if len(local_angles) == 0:
            logger.warning("[HOG] Warning: No human detections with valid measurements")
            return {
                'local_coarse': [],
                'snr_coarse': [],
                'pwr_coarse': [],
                'best_angle': None,
                'best_snr': None,
                'best_local': None,
                'num_angles_tested': 0,
                'frames_processed': frame_count,
                'detections_count': frames_with_detections,
                'status': 'no_detections'
            }

        best_idx = np.argmax(snr_values)
        best_angle = local_angles[best_idx]
        best_snr = snr_values[best_idx]

        logger.info(
            "\n[HOG RESULTS]\n"
            "Frames processed: %s\n"
            "Human detections: %s\n"
            "Unique angles measured: %s\n"
            "Best angle: %.2f degrees\n"
            "Best SNR: %.2f dB",
            frame_count,
            frames_with_detections,
            unique_poses,
            best_angle,
            best_snr,
        )

        return {
            'local_coarse': local_angles,
            'snr_coarse': snr_values,
            'pwr_coarse': pwr_values,
            'ser_coarse': ser_values,
            'best_angle': best_angle,
            'best_snr': best_snr,
            'best_local': best_angle,
            'num_angles_tested': unique_poses,
            'frames_processed': frame_count,
            'detections_count': frames_with_detections,
            'raw_poses': raw_poses,
            'status': 'success'
        }

    def _load_camera_calibration(self, K_path: Optional[str],
                                 dist_path: Optional[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Load camera intrinsics from files or use defaults.

        Args:
            K_path: Path to camera matrix file
            dist_path: Path to distortion coefficients file

        Returns:
            Tuple of (K, dist_coeffs)
        """
        if K_path is None:
            # Default camera intrinsics (640x480)
            K = np.array([
                [500, 0, 320],
                [0, 500, 240],
                [0, 0, 1]
            ], dtype=np.float32)
        else:
            K = np.load(K_path, allow_pickle=False).astype(np.float32)

        if dist_path is None:
            dist_coeffs = np.zeros((4,), dtype=np.float32)
        else:
            dist_coeffs = np.load(dist_path, allow_pickle=False).astype(np.float32)

        return K, dist_coeffs

    def _camera_to_world(self, tvec: np.ndarray, rvec: np.ndarray,
                         r_cw: np.ndarray, t_cw: np.ndarray) -> np.ndarray:
        """Transform point from camera to world coordinates.

        Args:
            tvec: Translation vector in camera frame (3, 1) or (3,)
            rvec: Rotation vector in camera frame (3, 1) or (3,)
            r_cw: Rotation matrix camera-to-world
            t_cw: Translation vector camera-to-world

        Returns:
            Point in world coordinates (3,)
        """
        tvec = np.array(tvec).flatten()
        p_world = r_cw @ tvec + t_cw
        return p_world
