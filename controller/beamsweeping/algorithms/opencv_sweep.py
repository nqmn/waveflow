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
              aruco_dict_type: str = "DICT_4X4_50",
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
              save_video: bool = True,
              video_output_path: str = "opencv_sweep_output.mp4",
              **kwargs) -> Dict:
        """Execute OpenCV-based vision sweep

        Requires: pip install opencv-python (for camera and ArUco support)

        IMPORTANT: When using OpenCV vision sweep, the UE position is determined
        from the detected ArUco marker in the camera feed, NOT from the network
        topology. This means:
        - Use: topology add random --no-ue (if you want to avoid confusion)
        - The detected marker position will override any UE position from the network
        - This ensures beam steering angle is based on actually detected positions

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
            save_video: Save camera feed with overlay to video file (default: True)
            video_output_path: Path to save output video file (default: "opencv_sweep_output.mp4")

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
        # For OpenCV vision sweep: UE may not exist yet (using --no-ue flag)
        # UE position will be determined from camera detection
        ap, ris, ue = validate_and_get_nodes(self.network, ap_name, ris_name, ue_name)

        # If UE doesn't exist, create a placeholder (will be updated from detection)
        if ue is None:
            print(f"\n[OPENCV VISION SWEEP] UE '{ue_name}' not found in network.")
            print(f"[OPENCV VISION SWEEP] Creating placeholder UE node (position will be set from camera detection).")
            try:
                self.network.add_ue(ue_name, 0.0, 0.0, 0.0)
                ue = self.network.nodes[ue_name]
                print(f"[OPENCV VISION SWEEP] Created placeholder UE '{ue_name}' at origin.")
            except Exception as e:
                raise ValueError(f"Could not create UE node: {e}") from e

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
            print(f"[OPENCV MOCK] Using synthetic camera with {mock_trajectory} trajectory")
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

        # Validate camera-to-world transformation
        if r_cw is None or t_cw is None:
            raise ValueError("Camera-to-world transformation (r_cw, t_cw) required")

        r_cw = np.array(r_cw, dtype=np.float64)
        t_cw = np.array(t_cw, dtype=np.float64)

        # Get RIS parameters
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)

        # Calculate AP and RIS angles for deflection computation
        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))

        # For mock camera, compute r_cw and t_cw if using identity
        # so that camera detection maps correctly to world coordinates
        if use_mock and np.allclose(r_cw, np.eye(3)) and np.allclose(t_cw, np.zeros(3)):
            # Position camera 3m in front of RIS, looking at RIS center
            # Camera X-axis points right, Y-axis points down, Z-axis points forward
            camera_distance = 3.0

            # Camera is positioned at RIS location + offset
            t_cw = np.array([ris.pos[0], ris.pos[1], ris.pos[2] + camera_distance])

            # Camera looks at RIS/UE (identity rotation = world aligned)
            r_cw = np.eye(3, dtype=np.float64)

            print(f"[MOCK CAMERA] Computed transformation:")
            print(f"  Camera position (t_cw): {t_cw}")
            print(f"  Camera rotation (r_cw): identity")

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

        # Setup video writer for recording output frames
        video_writer = None
        if save_video and not use_mock:
            try:
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30

                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                video_writer = cv2.VideoWriter(video_output_path, fourcc, fps, (frame_width, frame_height))
                print(f"[VIDEO] Recording to: {video_output_path}")
            except Exception as e:
                print(f"[VIDEO] Warning: Could not setup video writer: {e}")
                video_writer = None

        print(f"\n[OPENCV VISION SWEEP]")
        print(f"Camera ID: {camera_id}")
        print(f"ArUco Dict: {aruco_dict_type}")
        print(f"Marker Size: {marker_size}m")
        print(f"Max Frames: {max_frames}")
        print(f"Processing frames...")

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

                    frames_with_markers += 1
                    marker_detected = True

                    # Process first detected marker (UE position)
                    rvec, tvec, _ = cv2.aruco.estimatePoseSingleMarkers(
                        corners[0:1], marker_size, K, dist_coeffs
                    )

                    rvec = rvec[0]
                    tvec = tvec[0]

                    # Draw detected markers
                    cv2.aruco.drawDetectedMarkers(output_frame, corners, ids)

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
                    print(f"\n[COORDINATE TRANSFORMATION DETAILS]")
                    print(f"Frame {frame_count}:")
                    print(f"  Camera frame (from ArUco detector):")
                    print(f"    x_cam = {x_cam:.6f} m")
                    print(f"    y_cam = {y_cam:.6f} m")
                    print(f"    z_cam = {z_cam:.6f} m")
                    print(f"    distance = {dist_cam:.6f} m")
                    print(f"  Transform parameters:")
                    print(f"    R_cw (rotation matrix):")
                    print(f"      {r_cw}")
                    print(f"    t_cw (translation): {t_cw}")
                    is_identity = (np.allclose(r_cw, np.eye(3)) and
                                   np.allclose(t_cw, np.zeros(3)))
                    print(f"    Is identity transform: {is_identity}")
                    print(f"  World frame (RIS-centered):")
                    print(f"    x_world = {x_world:.6f}")
                    print(f"    y_world = {y_world:.6f}")
                    print(f"    z_world = {z_world:.6f}")

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

                # Write frame to video file if recording
                if video_writer is not None:
                    video_writer.write(output_frame)

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
                    ue.pos = p_ue_world.tolist()
                    print(f"\n[UE POSITION UPDATE]")
                    print(f"  UE position before (from network topology): {ue_pos_before}")
                    print(f"  UE position after (from camera detection): {ue.pos}")
                    print(f"  This ensures deflection angle is based on detected marker position")

                # Compute deflection angle from AP/RIS/UE geometry
                deflection_angle = self._compute_deflection_angle(ap, ris, p_ue_world)

                # Clamp to RIS FOV
                deflection_clamped = np.clip(deflection_angle, -ris_max_angle, ris_max_angle)

                # Log deflection calculation for first detection
                if unique_poses == 0:
                    print(f"\n[DEFLECTION ANGLE CALCULATION]")
                    print(f"  RIS position: {ris.pos}")
                    print(f"  AP position: {ap.pos}")
                    print(f"  UE position (world frame): {p_ue_world}")
                    print(f"  Vector RIS→AP: {ap.pos - ris.pos}")
                    print(f"  Vector RIS→UE: {p_ue_world - ris.pos}")
                    ap_vec = ap.pos - ris.pos
                    ue_vec = p_ue_world - ris.pos
                    ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
                    ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))
                    print(f"  AP azimuth angle: {ap_angle:.2f}°")
                    print(f"  UE azimuth angle: {ue_angle:.2f}°")
                    print(f"  Raw deflection angle: {deflection_angle:.2f}°")
                    print(f"  Clamped deflection angle: {deflection_clamped:.2f}°")

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
                    print(f"\n[MARKER DETECTED] Marker found at frame {frame_count}. Stopping sweep.")
                    break

        finally:
            cap.release()

            # Release video writer and print output path
            if video_writer is not None:
                video_writer.release()
                print(f"\n[VIDEO] Recording saved: {video_output_path}")
                print(f"[VIDEO] To view: ffplay {video_output_path}")

            cv2.destroyAllWindows()

        # Validate results
        if not snr_values:
            # Provide diagnostic information
            detection_rate = (frames_with_markers / frame_count * 100) if frame_count > 0 else 0
            print(f"\n[DIAGNOSTIC REPORT]")
            print(f"Total frames processed: {frame_count}")
            print(f"Frames with markers detected: {frames_with_markers}")
            print(f"Detection rate: {detection_rate:.1f}%")
            print(f"\nPossible issues:")
            if detection_rate == 0:
                print(f"  - No ArUco markers detected in any frame")
                print(f"  - Check: Camera is connected and oriented correctly")
                print(f"  - Check: ArUco marker is clearly visible in camera view")
                print(f"  - Check: Lighting is adequate for marker detection")
                print(f"  - Check: Marker size parameter ({marker_size}m) matches actual marker")
                print(f"  - Check: ArUco dictionary (DICT_4X4_50) matches your markers")
                print(f"\n  Debug frames saved:")
                print(f"    - camera_frame_001.jpg, camera_frame_005.jpg, camera_frame_010.jpg, ...")
                print(f"  These show what the camera sees. Check them to:")
                print(f"    1. Verify camera is working")
                print(f"    2. See where to place the ArUco marker")
                print(f"    3. Adjust lighting/focus if needed")
            elif unique_poses == 0:
                print(f"  - Markers detected but poses not valid for RIS FOV constraints")
                print(f"  - Check: UE position is within RIS field of view")
                print(f"  - Check: Angle change threshold ({angle_change_threshold}°) is not too strict")

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
        print(f"\n[OPENCV VISION RESULTS]")
        print(f"Frames processed: {frame_count}")
        print(f"Unique poses detected: {unique_poses}")
        print(f"Deflection angles (degrees): {[f'{a:.1f}' for a in local_angles]}")
        print(f"SNR values (dB): {[f'{s:.2f}' for s in snr_values]}")
        print(f"\nBest Result:")
        print(f"  Local deflection angle: {best_local:.2f}°")
        print(f"  Absolute beam angle: {best_abs:.2f}°")
        print(f"  Best SNR: {best_snr:.4f} dB")

        # Display detected marker frame for validation
        if last_detection_frame is not None:
            print(f"\n[MARKER VALIDATION DISPLAY]")
            print(f"  Frame: {last_detection_info['frame_count']}")
            print(f"  Camera coords - X: {last_detection_info['x_cam']:.3f}m, Y: {last_detection_info['y_cam']:.3f}m, Z: {last_detection_info['z_cam']:.3f}m, Dist: {last_detection_info['dist_cam']:.3f}m")
            print(f"  World coords - X: {last_detection_info['p_ue_world'][0]:.3f}, Y: {last_detection_info['p_ue_world'][1]:.3f}, Z: {last_detection_info['p_ue_world'][2]:.3f}")
            print(f"\nPress any key to view the detected marker frame...")
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
