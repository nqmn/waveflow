#!/usr/bin/env python3
"""
Camera Diagnostic Tool

Helps diagnose camera availability, permissions, and OpenCV compatibility.
Run this if you're having issues with camera access.

Usage:
    python tools/camera_diagnostic.py
"""

import sys
import os

try:
    import cv2
except ImportError:
    print("ERROR: OpenCV not installed")
    print("Install with: pip install opencv-python")
    sys.exit(1)

import subprocess


def check_opencv_info():
    """Display OpenCV information."""
    print("\n" + "=" * 70)
    print("OPENCV INFORMATION")
    print("=" * 70)
    print(f"OpenCV Version: {cv2.__version__}")
    print(f"Python Version: {sys.version.split()[0]}")


def check_v4l2_devices():
    """Check for V4L2 video devices."""
    print("\n" + "=" * 70)
    print("V4L2 VIDEO DEVICES (Linux only)")
    print("=" * 70)

    try:
        result = subprocess.run(["ls", "-la", "/dev/video*"],
                              shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        else:
            print("No /dev/video* devices found")
    except Exception as e:
        print(f"Could not check V4L2 devices: {e}")
        print("(This is expected on non-Linux systems)")


def check_camera_indices():
    """Test all camera indices 0-9."""
    print("\n" + "=" * 70)
    print("CAMERA DETECTION TEST (Indices 0-9)")
    print("=" * 70)

    found_any = False
    available_cameras = []

    for i in range(10):
        print(f"\nTesting camera {i}...", end=" ")
        try:
            cap = cv2.VideoCapture(i)

            # Check if opened
            is_open = cap.isOpened()

            if is_open:
                # Get properties
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)

                print(f"✓ AVAILABLE")
                print(f"  Resolution: {width}x{height}")
                print(f"  FPS: {fps}")

                # Try to read a frame
                ret, frame = cap.read()
                if ret:
                    print(f"  Can read frames: YES")
                    print(f"  Frame shape: {frame.shape}")
                else:
                    print(f"  Can read frames: NO (camera open but can't read)")

                found_any = True
                available_cameras.append(i)
            else:
                print("✗ Not available")

            cap.release()

        except Exception as e:
            print(f"✗ Error: {e}")

    print("\n" + "-" * 70)
    if found_any:
        print(f"✓ Found {len(available_cameras)} available camera(s): {available_cameras}")
        print(f"  Use 'connect --algo hog --camera_id {available_cameras[0]}' to select")
    else:
        print("✗ No cameras found")
        print("  Check:")
        print("    1. Camera is connected to system")
        print("    2. Camera permissions (may need: sudo usermod -a -G video $USER)")
        print("    3. Camera is not in use by another application")
        print("    4. Try reconnecting the camera")


def check_gstreamer():
    """Check GStreamer backend."""
    print("\n" + "=" * 70)
    print("GSTREAMER BACKEND")
    print("=" * 70)

    try:
        result = subprocess.run(["gst-launch-1.0", "--version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ GStreamer installed: {result.stdout.strip()}")
        else:
            print("✗ GStreamer not found")
    except Exception:
        print("✗ GStreamer not found or not in PATH")


def check_ffmpeg():
    """Check FFmpeg."""
    print("\n" + "=" * 70)
    print("FFMPEG")
    print("=" * 70)

    try:
        result = subprocess.run(["ffmpeg", "-version"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            first_line = result.stdout.split('\n')[0]
            print(f"✓ FFmpeg installed: {first_line}")
        else:
            print("✗ FFmpeg not found")
    except Exception:
        print("✗ FFmpeg not found or not in PATH")


def check_opencv_backends():
    """Display available OpenCV backends."""
    print("\n" + "=" * 70)
    print("OPENCV BUILD CONFIGURATION")
    print("=" * 70)

    # Try to get build info
    try:
        info = cv2.getBuildInformation()

        # Extract video capture backends
        if "Video I/O:" in info:
            print("Video I/O capabilities detected")

        # Look for specific backends
        backends = ["V4L", "V4L2", "GStreamer", "OpenGL", "FFMPEG"]
        for backend in backends:
            if backend in info:
                print(f"  ✓ {backend} support")
    except Exception as e:
        print(f"Could not get build info: {e}")


def diagnose_permissions():
    """Check file permissions for video devices."""
    print("\n" + "=" * 70)
    print("DEVICE PERMISSIONS")
    print("=" * 70)

    try:
        result = subprocess.run(["id"], capture_output=True, text=True)
        print(f"Current user: {result.stdout.strip()}")

        # Check if user is in video group
        result = subprocess.run(["groups"], capture_output=True, text=True)
        groups = result.stdout.strip()
        print(f"Groups: {groups}")

        if "video" in groups:
            print("✓ User is in 'video' group")
        else:
            print("✗ User is NOT in 'video' group")
            print("  To fix: sudo usermod -a -G video $USER")
            print("  Then logout and login again")

    except Exception as e:
        print(f"Could not check permissions: {e}")


def print_recommendations():
    """Print recommendations based on findings."""
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    print("""
If no cameras are found:

1. Check Physical Connection
   - Ensure camera is plugged into USB port
   - Try different USB ports
   - Try on a different computer if possible

2. Check Permissions (Linux)
   - Add user to video group: sudo usermod -a -G video $USER
   - Logout and login again
   - Restart after group change

3. Check Driver (Linux)
   - Install V4L2 drivers: sudo apt-get install v4l-utils
   - List cameras: v4l2-ctl --list-devices

4. Check Application Access
   - Ensure no other app is using the camera
   - Close Zoom, Chrome, etc.
   - Try: fuser /dev/video0  (to see what's using it)

5. Check OpenCV Build
   - May need to rebuild OpenCV with V4L2 support
   - Or install pre-built: pip install opencv-python

6. Try Alternative
   - Use mock camera for testing
   - Implement video file input instead

For RISNet HOG detection:
   - If camera found at index N: connect --algo hog --camera_id N
   - Camera auto-detection will search 0-9 if specified index fails
   - Check logs for which camera index is actually being used
""")


def main():
    """Run all diagnostics."""
    print("\n")
    print("*" * 70)
    print("CAMERA DIAGNOSTIC TOOL")
    print("*" * 70)

    check_opencv_info()
    check_v4l2_devices()
    check_camera_indices()
    check_gstreamer()
    check_ffmpeg()
    check_opencv_backends()
    diagnose_permissions()
    print_recommendations()

    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
