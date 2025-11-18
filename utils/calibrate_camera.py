#!/usr/bin/env python3
"""
Camera Calibration Script for RISNet OpenCV Vision Sweep

This script helps calibrate your camera's position and orientation
relative to the world coordinate system.

Usage:
    python3 calibrate_camera.py
"""

import cv2
import numpy as np
import sys

def calibrate_camera_interactive():
    """
    Interactive camera calibration procedure.
    Asks user for camera position and orientation, then saves calibration files.
    """
    print("=" * 70)
    print("RISNet Camera Calibration Tool")
    print("=" * 70)
    print("\nThis tool will help you calibrate your camera's position and orientation")
    print("relative to the RISNet world coordinate system (X, Y, Z in meters).\n")

    # Step 1: Camera Position (translation)
    print("[STEP 1] Camera Position in World Coordinates")
    print("-" * 70)
    print("Enter the camera's physical position in the world frame (meters).")
    print("Example: If camera is 2.5m along X, 1.0m along Y, 0.5m along Z:")
    print("  X = 2.5, Y = 1.0, Z = 0.5\n")

    try:
        cam_x = float(input("  Camera X position (meters): "))
        cam_y = float(input("  Camera Y position (meters): "))
        cam_z = float(input("  Camera Z position (meters): "))
    except ValueError:
        print("Error: Please enter valid numbers")
        return False

    t_cw = np.array([cam_x, cam_y, cam_z], dtype=np.float64)

    # Step 2: Camera Orientation (rotation)
    print("\n[STEP 2] Camera Orientation (Rotation)")
    print("-" * 70)
    print("Enter rotation angles in degrees (Euler angles: roll, pitch, yaw).")
    print("These describe how the camera is rotated relative to the world frame.")
    print("Example: If camera is aligned with world frame: roll=0, pitch=0, yaw=0\n")

    try:
        roll = float(input("  Roll (rotation around X-axis, degrees): "))
        pitch = float(input("  Pitch (rotation around Y-axis, degrees): "))
        yaw = float(input("  Yaw (rotation around Z-axis, degrees): "))
    except ValueError:
        print("Error: Please enter valid numbers")
        return False

    # Convert Euler angles to rotation matrix
    roll_rad = np.radians(roll)
    pitch_rad = np.radians(pitch)
    yaw_rad = np.radians(yaw)

    # Rotation matrices for each axis
    Rx = np.array([
        [1, 0, 0],
        [0, np.cos(roll_rad), -np.sin(roll_rad)],
        [0, np.sin(roll_rad), np.cos(roll_rad)]
    ])

    Ry = np.array([
        [np.cos(pitch_rad), 0, np.sin(pitch_rad)],
        [0, 1, 0],
        [-np.sin(pitch_rad), 0, np.cos(pitch_rad)]
    ])

    Rz = np.array([
        [np.cos(yaw_rad), -np.sin(yaw_rad), 0],
        [np.sin(yaw_rad), np.cos(yaw_rad), 0],
        [0, 0, 1]
    ])

    # Combined rotation (ZYX order)
    r_cw = Rz @ Ry @ Rx

    # Step 3: Test with live camera
    print("\n[STEP 3] Camera Test")
    print("-" * 70)
    print("Testing camera feed. Press 'q' to close the preview window.\n")

    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Error: Could not open camera")
            return False

        print("Camera preview running...")
        print("Press 'q' to stop preview and proceed to save calibration")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Add text overlay
            cv2.putText(frame, "Camera Calibration Test", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(frame, f"Position: ({cam_x:.2f}, {cam_y:.2f}, {cam_z:.2f})", (10, 70),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, f"Rotation: (R:{roll:.1f}, P:{pitch:.1f}, Y:{yaw:.1f})", (10, 100),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(frame, "Press 'q' to continue", (10, frame.shape[0] - 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

            cv2.imshow("Camera Calibration", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    except Exception as e:
        print(f"Error during camera test: {e}")
        return False

    # Step 4: Save calibration
    print("\n[STEP 4] Save Calibration Files")
    print("-" * 70)

    try:
        np.save("rotation.npy", r_cw)
        np.save("translation.npy", t_cw)

        print("✓ Calibration files saved:")
        print(f"  rotation.npy - Camera-to-world rotation matrix")
        print(f"  translation.npy - Camera-to-world translation vector\n")

        print("Calibration Summary:")
        print(f"  Camera Position (t_cw): {t_cw}")
        print(f"  Camera Rotation (Euler): Roll={roll}°, Pitch={pitch}°, Yaw={yaw}°")
        print(f"  Rotation Matrix (r_cw):\n{r_cw}\n")

        print("✓ Calibration complete!")
        print("\nYou can now use the real camera with:")
        print("  connect --sweep --algo opencv --use-mock false")

        return True

    except Exception as e:
        print(f"Error saving calibration: {e}")
        return False


def main():
    """Main entry point"""
    try:
        if calibrate_camera_interactive():
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCalibration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
