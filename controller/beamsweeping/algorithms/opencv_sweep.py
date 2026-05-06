"""OpenCV Vision-Based Beam Sweep Algorithm

Uses ArUco marker detection to track UE position from camera feed.
Computes deflection angles from world coordinates and measures SNR/RSSI/CSI
via network.connect() at each detected pose.

Flow:
1. Detect UE pose via ArUco markers (coordinates relative to camera)
2. Transform to world coordinates (camera_to_world transform)
3. Compute deflection angle from AP/RIS/UE geometry
4. Pass deflection angle to network.connect(beam_angle_deg=angle)
5. Collect metrics (SNR, RSSI, CSI) for each detection
6. Return results in standard sweep format
"""

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

import logging
import numpy as np
from typing import Dict, Optional, Tuple, List
from ..base import SweepAlgorithmBase
from ..common import (
    apply_waveform_realism,
    setup_waveform_simulator,
    validate_and_get_nodes,
    FeedbackCollector,
    clamp_local_deflection_to_ris_fov,
)
from ..registry import register_algorithm

# Import visualization module
try:
    from .opencv_viewer import OpenCVCameraViewer
    VIEWER_AVAILABLE = True
except ImportError:
    VIEWER_AVAILABLE = False

# Import mock camera for testing
try:
    from .opencv_mock import MockCamera
    MOCK_AVAILABLE = True
except ImportError:
    MOCK_AVAILABLE = False

logger = logging.getLogger(__name__)


@register_algorithm("opencv", aliases=("vision", "aruco"))
class OpenCVVisionSweep(SweepAlgorithmBase):
    """Vision-based beam sweep using ArUco marker tracking"""

    @property
    def name(self) -> str:
        return "OpenCV Vision-Based Sweep"

    @property
    def description(self) -> str:
        return "Real-time UE tracking via ArUco markers. Computes deflection angles from world coordinates."

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              ml_angles=None, use_waveform: bool = False,
              modulation: str = 'QPSK', num_symbols: int = 1000,
              metric_selector=None,
              camera_id: int = 0,
              aruco_dict_type: str = "DICT_5X5_100",
              marker_size: float = 0.05,
              camera_matrix_path: Optional[str] = None,
              dist_coeffs_path: Optional[str] = None,
              r_cw: Optional[np.ndarray] = None,
              t_cw: Optional[np.ndarray] = None,
              max_frames: int = 100,
              angle_change_threshold: float = 1.0,
              enable_viewer: bool = True,
              use_mock: bool = False,
              mock_trajectory: str = "circular",
              target_marker_id: Optional[int] = 0,
              **kwargs) -> Dict:
        """Execute OpenCV-based vision sweep

        Requires: pip install opencv-python (for camera and ArUco support)

        IMPORTANT: When using OpenCV vision sweep, the UE position is automatically
        determined from the detected ArUco marker in the camera feed. This means:
        - If UE does not exist: Creates placeholder UE at origin (will be replaced by detection)
        - If UE exists in topology: Position will be replaced with detected marker position
        - The detected marker position overrides any UE position from the network topology
        - This ensures beam steering angle is based on actually detected positions
        - Benefit: User can run 'connect --algo opencv' directly without pre-positioning the UE

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees (for reference)
            step: Step size in degrees (for reference)
            seed: Random seed for reproducibility
            enable_feedback: Enable closed-loop feedback per measurement
            max_feedback_iterations: Max feedback iterations per measurement
            use_waveform: Enable waveform realism simulation
            modulation: Modulation type (QPSK, 16QAM, 64QAM)
            num_symbols: Number of symbols per measurement
            metric_selector: Custom metric selection function
            camera_id: Camera device ID (default: 0)
            aruco_dict_type: ArUco dictionary type (default: DICT_4X4_50)
            marker_size: Physical marker size in meters
            camera_matrix_path: Path to camera intrinsics (K matrix, .npy)
            dist_coeffs_path: Path to distortion coefficients (.npy)
            r_cw: Rotation matrix (camera to world), shape (3,3)
            t_cw: Translation vector (camera to world), shape (3,)
            max_frames: Max frames to process before stopping
            angle_change_threshold: Skip poses within this angle of previous (degrees)
            enable_viewer: Enable camera viewer with AP/RIS/UE overlay (default: True)
            use_mock: Use mock camera instead of real camera (default: False)
            mock_trajectory: Mock camera trajectory type: 'circular', 'linear', 'random', 'static' (default: 'circular')

        Returns:
            Dictionary with sweep results in standard format:
                - local_coarse: Detected deflection angles
                - snr_coarse: SNR values for each angle
                - pwr_coarse: Power values for each angle
                - best_angle: Best absolute beam angle found
                - best_snr: Best SNR value
                - best_local: Best local deflection angle
                - specular_angle: Reference specular angle (AP direction)
                - num_angles_tested: Number of unique poses detected
                - raw_poses: List of detected (rvec, tvec) pairs (optional)
                - frames_processed: Total frames processed
        """
        if not CV2_AVAILABLE:
            raise ImportError(
                "OpenCV (cv2) is required for vision-based sweep. "
                "Install with: pip install opencv-python"
            )

        # Validate nodes
        # For OpenCV vision sweep: UE position will be determined from camera detection
        # If UE exists in topology, it will be replaced with detected position
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # Handle UE node
        if ue is None:
            logger.info(
                "\n[OPENCV VISION SWEEP] UE '%s' not found in network.\n"
                "[OPENCV VISION SWEEP] Creating placeholder UE node (position will be set from camera detection).",
                ue_name,
            )
            try:
                self.network.add_ue(ue_name, 0.0, 0.0, 0.0)
                ue = self.network.nodes[ue_name]
                logger.info("[OPENCV VISION SWEEP] Created placeholder UE '%s' at origin.", ue_name)
            except Exception as e:
                raise ValueError(f"Could not create UE node: {e}") from e
        else:
            ue_pos_original = np.array(ue.pos, dtype=np.float64).copy()
            logger.info(
                "\n[OPENCV VISION SWEEP] UE '%s' exists in topology.\n"
                "[OPENCV VISION SWEEP] Will replace UE position with detected marker position.\n"
                "[OPENCV VISION SWEEP] Original UE position: %s",
                ue_name,
                ue_pos_original,
            )

        # Initialize camera and ArUco detection
        if use_mock:
            if not MOCK_AVAILABLE:
                raise ImportError("Mock camera not available")
            cap = MockCamera(
                width=640,
                height=480,
                marker_trajectory=mock_trajectory,
                num_frames=max_frames
            )
            logger.info("[OPENCV MOCK] Using synthetic camera with %s trajectory", mock_trajectory)
        else:
            cap = cv2.VideoCapture(camera_id)
            if not cap.isOpened():
                raise RuntimeError(f"Failed to open camera {camera_id}")

        # Load camera intrinsics
        K, dist_coeffs = self._load_camera_calibration(camera_matrix_path, dist_coeffs_path)

        # Setup ArUco detector
        try:
            aruco_dict = cv2.aruco.getPredefinedDictionary(
                getattr(cv2.aruco, aruco_dict_type)
            )
            detector = cv2.aruco.ArucoDetector(aruco_dict)
        except AttributeError:
            raise ValueError(f"Invalid ArUco dictionary type: {aruco_dict_type}")

        # Camera assumed to be mounted at RIS if extrinsics not supplied
        default_rotation = False
        default_translation = False
        if r_cw is None:
            r_cw = np.eye(3, dtype=np.float64)
            default_rotation = True
        else:
            r_cw = np.array(r_cw, dtype=np.float64)

        if t_cw is None:
            t_cw = np.array([ris.pos[0], ris.pos[1], ris.pos[2]], dtype=np.float64)
            default_translation = True
        else:
            t_cw = np.array(t_cw, dtype=np.float64)

        if default_rotation:
            logger.info("[OPENCV] r_cw not provided. Assuming camera axes aligned with RIS (identity rotation).")
        if default_translation:
            logger.info(
                "[OPENCV] t_cw not provided. Assuming camera located at RIS position %s.",
                np.asarray(ris.pos),
            )

        # Get RIS parameters
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)

        # Calculate AP and RIS angles for deflection computation
        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        # For mock camera, compute r_cw and t_cw if using identity
        # so that camera detection maps correctly to world coordinates
        if use_mock and np.allclose(r_cw, np.eye(3)) and np.allclose(t_cw, np.zeros(3)):
            # Position camera AT RIS center with axes aligned to world
            # This ensures marker bearing in camera frame directly maps to world bearing
            # If marker is detected at camera (x, y, z), world position = (x + ris_x, y + ris_y, z + ris_z)

            # Camera is positioned at RIS location (same origin)
            t_cw = np.array([ris.pos[0], ris.pos[1], ris.pos[2]])

            # Camera axes aligned with world axes (identity rotation)
            r_cw = np.eye(3, dtype=np.float64)

            logger.info(
                "[MOCK CAMERA] Computed transformation:\n"
                "  Camera position (t_cw): %s\n"
                "  Camera rotation (r_cw): identity\n"
                "  Note: Camera is at RIS center with world-aligned axes",
                t_cw,
            )

        # Setup waveform simulator if requested
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
        frames_with_markers = 0  # Track detection rate
        last_detection_frame = None  # Store the last frame with detected marker
        last_detection_info = {}  # Store marker info for validation display

        # Note: Video recording removed. Detected frame will be saved as image instead.

        logger.info(
            "\n[OPENCV VISION SWEEP]\n"
            "Camera ID: %s\n"
            "ArUco Dict: %s\n"
            "Marker Size: %sm\n"
            "Max Frames: %s\n"
            "Processing frames...",
            camera_id,
            aruco_dict_type,
            marker_size,
            max_frames,
        )

        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                output_frame = frame.copy()
                tvec = None
                rvec = None
                marker_detected = False

                # Detect ArUco markers or use mock pose estimation
                if use_mock:
                    # For mock camera: work backwards from actual UE world position
                    # 1. Get actual UE world position
                    ue_world = np.array(ue.pos, dtype=np.float64)

                    # 2. Transform from world to camera frame
                    r_wc = r_cw.T  # World to camera rotation (inverse of r_cw)
                    t_wc = -r_wc @ t_cw  # World to camera translation (inverse of t_cw)
                    ue_cam = r_wc @ ue_world + t_wc

                    # 3. Create tvec/rvec directly from the correct camera coordinates
                    # tvec is the position in camera frame (no rotation needed for point)
                    tvec = ue_cam.reshape(3, 1)
                    # rvec is identity (marker is aligned with world frame)
                    rvec = np.array([0.0, 0.0, 0.0]).reshape(3, 1)
                    frames_with_markers += 1
                    marker_detected = True
                else:
                    corners, ids, rejected = detector.detectMarkers(frame)

                    if ids is None or len(ids) == 0:
                        # Display frame without detections
                        cv2.putText(output_frame, "NO MARKERS DETECTED - place marker in view",
                                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        cv2.putText(output_frame, f"Frames scanned: {frame_count}",
                                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                        cv2.imshow("ArUco Marker Detection", output_frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                        continue

                    # Pick target marker (defaults to first if no filter)
                    selected_index = 0
                    if target_marker_id is not None:
                        found = False
                        for idx, marker_id in enumerate(ids.flatten()):
                            if marker_id == target_marker_id:
                                selected_index = idx
                                found = True
                                break
                        if not found:
                            # Requested marker id not in this frame
                            continue

                    frames_with_markers += 1
                    marker_detected = True

                    rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                        [corners[selected_index]], marker_size, K, dist_coeffs
                    )

                    rvec = rvec[0]
                    tvec = tvec[0]

                    # Draw detected markers with green squares
                    selected_ids = ids[selected_index:selected_index+1]
                    cv2.aruco.drawDetectedMarkers(output_frame, [corners[selected_index]], selected_ids)

                    # Additionally draw explicit green rectangle around marker corners for clarity
                    corner_points = corners[selected_index][0].astype(int)
                    cv2.polylines(output_frame, [corner_points], True, (0, 255, 0), 3)
                    for point in corner_points:
                        cv2.circle(output_frame, tuple(point), 4, (0, 255, 0), -1)

                # Transform UE position to world coordinates (camera → world)
                p_ue_world = self._camera_to_world(tvec, rvec, r_cw, t_cw)

                # Extract marker coordinates in camera frame
                x_cam, y_cam, z_cam = tvec.flatten()
                dist_cam = np.sqrt(x_cam**2 + y_cam**2 + z_cam**2)

                # Extract world coordinates
                x_world, y_world, z_world = p_ue_world

                # Display marker information on frame
                marker_text = f"Cam: x={x_cam:.3f}m y={y_cam:.3f}m z={z_cam:.3f}m d={dist_cam:.3f}m"
                cv2.putText(output_frame, marker_text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                world_text = f"World: x={x_world:.3f} y={y_world:.3f} z={z_world:.3f}"
                cv2.putText(output_frame, world_text, (10, 55),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                # Log coordinate transformation for first detection
                if unique_poses == 0:
                    is_identity = (np.allclose(r_cw, np.eye(3)) and
                                   np.allclose(t_cw, np.zeros(3)))
                    logger.info(
                        "\n[COORDINATE TRANSFORMATION DETAILS]\n"
                        "Frame %s:\n"
                        "  Camera frame (from ArUco detector):\n"
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

                # Draw axis on marker if not mock
                if not use_mock:
                    try:
                        cv2.drawFrameAxes(output_frame, K, dist_coeffs, rvec, tvec, marker_size * 0.5)
                    except AttributeError:
                        try:
                            cv2.aruco.drawAxis(output_frame, K, dist_coeffs, rvec, tvec, marker_size * 0.5)
                        except:
                            pass

                # Display frame
                cv2.imshow("ArUco Marker Detection", output_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                # Store last detection frame and info for validation display
                last_detection_frame = output_frame.copy()
                last_detection_info = {
                    'frame_count': frame_count,
                    'x_cam': x_cam,
                    'y_cam': y_cam,
                    'z_cam': z_cam,
                    'dist_cam': dist_cam,
                    'p_ue_world': p_ue_world.copy(),
                    'tvec': tvec.copy(),
                    'rvec': rvec.copy()
                }

                # IMPORTANT: Update UE position from camera detection
                # When using OpenCV vision, the UE position should come from the camera,
                # not from the network topology. This ensures the beam steering angle
                # is calculated based on the actually detected marker position.
                if unique_poses == 0:
                    ue_pos_before = np.array(ue.pos, dtype=np.float64).copy()
                    ue.pos = np.array(p_ue_world, dtype=np.float64)
                    logger.info(
                        "\n[UE POSITION UPDATE]\n"
                        "  UE position before (from network topology): %s\n"
                        "  UE position after (from camera detection): %s\n"
                        "  This ensures deflection angle is based on detected marker position",
                        ue_pos_before,
                        ue.pos.tolist(),
                    )

                # Compute deflection angle from AP/RIS/UE geometry
                deflection_angle = self._compute_deflection_angle(ap, ris, p_ue_world)

                # Clamp to RIS FOV
                deflection_clamped = np.clip(deflection_angle, -ris_max_angle, ris_max_angle)

                # Log deflection calculation for first detection
                if unique_poses == 0:
                    ap_vec = ap.pos - ris.pos
                    ue_vec = p_ue_world - ris.pos
                    ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
                    ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))
                    logger.info(
                        "\n[DEFLECTION ANGLE CALCULATION]\n"
                        "  RIS position: %s\n"
                        "  AP position: %s\n"
                        "  UE position (world frame): %s\n"
                        "  Vector RIS→AP: %s\n"
                        "  Vector RIS→UE: %s\n"
                        "  AP azimuth angle: %.2f°\n"
                        "  UE azimuth angle: %.2f°\n"
                        "  Raw deflection angle: %.2f°\n"
                        "  Clamped deflection angle: %.2f°",
                        ris.pos,
                        ap.pos,
                        p_ue_world,
                        ap.pos - ris.pos,
                        p_ue_world - ris.pos,
                        ap_angle,
                        ue_angle,
                        deflection_angle,
                        deflection_clamped,
                    )

                # Skip if too close to previously measured angle (redundancy check)
                if local_angles:
                    min_angle_diff = np.abs(np.array(local_angles) - deflection_clamped).min()
                    if min_angle_diff < angle_change_threshold:
                        continue

                unique_poses += 1
                local_angles.append(float(deflection_clamped))
                raw_poses.append({
                    'rvec': rvec.tolist(),
                    'tvec': tvec.tolist(),
                    'p_ue_world': p_ue_world.tolist(),
                    'raw_deflection': float(deflection_angle),
                    'clamped_deflection': float(deflection_clamped)
                })

                # Compute absolute beam angle from deflection
                # Deflection is symmetric, so we add to AP angle
                abs_angle = ap_angle + deflection_clamped

                # Measure SNR/RSSI/CSI at this angle via network.connect()
                with self._ap_state_guard(ap):
                    measurement_seed = (seed + unique_poses) if seed is not None else None
                    res = self.network.connect(
                        ap_name, ris_name, ue_name,
                        beam_angle_deg=abs_angle,
                        seed=measurement_seed,
                        enable_feedback=enable_feedback,
                        max_feedback_iterations=max_feedback_iterations,
                        store_in_active_links=False,
                        use_get_snr=self._should_use_get_snr()
                    )

                # Extract SNR and optional SER
                snr_val, ser_val = apply_waveform_realism(
                    res,
                    link_simulator,
                    seed=measurement_seed,
                )
                snr_values.append(snr_val)
                pwr_values.append(float(res['pwr_dBm']))
                if ser_values is not None:
                    ser_values.append(ser_val)

                # Collect feedback if enabled
                if enable_feedback and 'feedback_info' in res:
                    feedback_collector.add(
                        float(abs_angle),
                        float(deflection_clamped),
                        res['feedback_info']
                    )

                # For non-mock mode: stop after first marker is detected and measured
                if not use_mock:
                    logger.info(
                        "\n[MARKER DETECTED] Marker found at frame %s. Stopping sweep.",
                        frame_count,
                    )
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        # Validate results
        if not snr_values:
            # Provide diagnostic information
            detection_rate = (frames_with_markers / frame_count * 100) if frame_count > 0 else 0
            diagnostic_lines = [
                "",
                "[DIAGNOSTIC REPORT]",
                f"Total frames processed: {frame_count}",
                f"Frames with markers detected: {frames_with_markers}",
                f"Detection rate: {detection_rate:.1f}%",
                "",
                "Possible issues:",
            ]
            if detection_rate == 0:
                diagnostic_lines.extend([
                    "  - No ArUco markers detected in any frame",
                    "  - Check: Camera is connected and oriented correctly",
                    "  - Check: ArUco marker is clearly visible in camera view",
                    "  - Check: Lighting is adequate for marker detection",
                    f"  - Check: Marker size parameter ({marker_size}m) matches actual marker",
                    "  - Check: ArUco dictionary (DICT_4X4_50) matches your markers",
                    "",
                    "  Debug frames saved:",
                    "    - camera_frame_001.jpg, camera_frame_005.jpg, camera_frame_010.jpg, ...",
                    "  These show what the camera sees. Check them to:",
                    "    1. Verify camera is working",
                    "    2. See where to place the ArUco marker",
                    "    3. Adjust lighting/focus if needed",
                ])
            elif unique_poses == 0:
                diagnostic_lines.extend([
                    "  - Markers detected but poses not valid for RIS FOV constraints",
                    "  - Check: UE position is within RIS field of view",
                    f"  - Check: Angle change threshold ({angle_change_threshold}°) is not too strict",
                ])
            logger.warning("\n%s", "\n".join(diagnostic_lines))

            raise RuntimeError(
                f"No UE positions detected in {frame_count} frames. "
                f"Marker detection rate: {detection_rate:.1f}%. See diagnostic report above."
            )

        # Find best measurement
        if metric_selector is not None:
            best_idx = metric_selector.find_best_index(snr_values)
        else:
            best_idx = int(np.argmax(snr_values))

        best_local = local_angles[best_idx]
        best_snr = snr_values[best_idx]
        best_abs = ap_angle + best_local

        # Print results summary
        summary_lines = [
            "",
            "[OPENCV VISION RESULTS]",
            f"Frames processed: {frame_count}",
            f"Unique poses detected: {unique_poses}",
            f"Deflection angles (degrees): {[f'{a:.1f}' for a in local_angles]}",
            f"SNR values (dB): {[f'{s:.2f}' for s in snr_values]}",
            "",
            "Best Result:",
            f"  Local deflection angle: {best_local:.2f}°",
            f"  Absolute beam angle: {best_abs:.2f}°",
            f"  Best SNR: {best_snr:.4f} dB",
        ]
        logger.info("\n%s", "\n".join(summary_lines))

        # Save and display detected marker frame
        if last_detection_frame is not None:
            logger.info(
                "\n[MARKER VALIDATION DISPLAY]\n"
                "  Frame: %s\n"
                "  Camera coords - X: %.3fm, Y: %.3fm, Z: %.3fm, Dist: %.3fm\n"
                "  World coords - X: %.3f, Y: %.3f, Z: %.3f",
                last_detection_info['frame_count'],
                last_detection_info['x_cam'],
                last_detection_info['y_cam'],
                last_detection_info['z_cam'],
                last_detection_info['dist_cam'],
                last_detection_info['p_ue_world'][0],
                last_detection_info['p_ue_world'][1],
                last_detection_info['p_ue_world'][2],
            )

            # Save detected frame as image file
            marker_image_path = "aruco_marker_detected.png"
            cv2.imwrite(marker_image_path, last_detection_frame)
            logger.info(
                "\n[MARKER FRAME SAVED]\n"
                "  Path: %s\n"
                "  Shows: ArUco marker detection with green square outline",
                marker_image_path,
            )

            logger.info("\nPress any key to view the detected marker frame...")
            cv2.imshow("Detected Marker Frame - Validation", last_detection_frame)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        # Build result dictionary in standard format (matching ml_guided_sweep)
        result = {
            # Standard sweep keys
            'local_coarse': local_angles,
            'snr_coarse': snr_values,
            'pwr_coarse': pwr_values,
            'local_fine': [],
            'snr_fine': [],
            'best_angle': float(best_abs),
            'best_snr': float(best_snr),
            'best_local': float(best_local),
            'specular_angle': float(ap_angle),
            'num_angles_tested': unique_poses,
            'feedback_enabled': enable_feedback,
            'feedback_details': feedback_collector.get_details(),
            # Vision-specific data
            'raw_poses': raw_poses,
            'frames_processed': frame_count,
            'camera_id': camera_id,
            'aruco_dict_type': aruco_dict_type,
        }

        # Add SER if waveform simulation was used
        if use_waveform and ser_values:
            result['ser_coarse'] = ser_values
            result['ser_fine'] = []

        return result

    def _load_camera_calibration(self, K_path: Optional[str],
                                 dist_path: Optional[str]) -> Tuple[np.ndarray, np.ndarray]:
        """Load camera intrinsics and distortion coefficients.

        Args:
            K_path: Path to camera matrix (K) .npy file
            dist_path: Path to distortion coefficients .npy file

        Returns:
            Tuple of (K, dist_coeffs) as numpy arrays

        If paths not provided, uses default matrices.
        """
        if K_path is None:
            K = np.array([
                [500, 0, 320],
                [0, 500, 240],
                [0, 0, 1]
            ], dtype=np.float32)
        else:
            try:
                K = np.load(K_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Camera matrix file not found: {K_path}")

        if dist_path is None:
            dist_coeffs = np.zeros((4, 1), dtype=np.float32)
        else:
            try:
                dist_coeffs = np.load(dist_path)
            except FileNotFoundError:
                raise FileNotFoundError(f"Distortion coefficients file not found: {dist_path}")

        return K.astype(np.float32), dist_coeffs.astype(np.float32)

    def _camera_to_world(self, p_cam: np.ndarray, rvec: np.ndarray,
                        r_cw: np.ndarray, t_cw: np.ndarray) -> np.ndarray:
        """Transform point from camera frame to world frame.

        Assumes:
        - World coordinate system has origin at RIS center with RIS axes
        - Camera is mounted at RIS center with axes aligned to RIS axes
        - Therefore: camera-frame = RIS-frame = world-frame
        - Camera-to-world transform should be identity (R_cw=I, t_cw=0)

        Args:
            p_cam: Point in camera frame (3,) or (3, 1)
            rvec: Rotation vector (marker rotation, not used for world transform)
            r_cw: Rotation matrix camera-to-world (3, 3), should be identity
            t_cw: Translation vector camera-to-world (3,), should be [0, 0, 0]

        Returns:
            Point in world frame (3,) as numpy array

        Formula: p_world = R_cw @ p_cam + t_cw

        When R_cw=I and t_cw=0:
        p_world = I @ p_cam + 0 = p_cam (camera frame = world frame)
        """
        p_cam = np.array(p_cam).flatten()

        # Check if transform is identity (camera at RIS center, axes aligned)
        is_identity_transform = (np.allclose(r_cw, np.eye(3)) and
                                 np.allclose(t_cw, np.zeros(3)))

        # Apply transformation
        p_world = r_cw @ p_cam + t_cw

        return p_world

    def _compute_deflection_angle(self, ap, ris, p_ue_world: np.ndarray) -> float:
        """Compute RIS local deflection angle for beam steering.

        Local deflection angle is the relative steering angle from AP direction
        to UE direction as seen from the RIS position.

        Args:
            ap: Access Point node (has .pos attribute)
            ris: RIS node (has .pos attribute)
            p_ue_world: UE position in world coordinates (3,)

        Returns:
            Local deflection angle in degrees (relative steering from AP)
        """
        # Calculate angles from RIS to AP and to UE (in XY plane)
        ap_vec = ap.pos - ris.pos
        ue_vec = p_ue_world - ris.pos

        # Calculate azimuth angles (in XY plane)
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Local deflection is the angular difference (UE from AP)
        deflection_deg = ue_angle - ap_angle

        # Normalize to [-180, 180]
        while deflection_deg > 180:
            deflection_deg -= 360
        while deflection_deg < -180:
            deflection_deg += 360

        return float(deflection_deg)
