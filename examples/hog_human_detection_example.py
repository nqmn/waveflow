#!/usr/bin/env python3
"""
Example: HOG Human Detection Beam Steering

This example demonstrates how to use HOG (Histogram of Oriented Gradients)
to detect humans and automatically steer RIS beams to optimize signal reception.

Usage:
    python examples/hog_human_detection_example.py

Requirements:
    - Webcam connected to system
    - OpenCV installed (pip install opencv-python)
    - RISNet installed and working
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader


def build_demo_network():
    """Build a small RISNetwork compatible with the current sweep APIs."""
    network = RISNetwork(enable_messaging=False)
    network.add_ap("AP1", 0.0, 0.0, 5.0)
    network.add_ris("RIS1", 5.0, 0.0, 5.0, N=8, max_angle_deg=180)
    network.add_ue("UE1", 10.0, 0.0, 5.0)
    return network


def run_hog_sweep(**kwargs):
    """Execute the registered HOG sweep against the current network API."""
    network = build_demo_network()
    algorithm = SweepAlgorithmLoader.get_algorithm("hog", network)
    return algorithm.sweep(
        "AP1",
        "RIS1",
        "UE1",
        enable_feedback=False,
        **kwargs,
    )


def example_basic_hog_detection():
    """Basic HOG detection example."""
    print("=" * 70)
    print("EXAMPLE 1: Basic HOG Human Detection")
    print("=" * 70)

    print("\nStarting HOG-based beam sweep...")
    print("Position your body in front of the camera when prompted.")
    print("Press 'q' in the camera window to stop scanning.\n")

    result = run_hog_sweep(
        fov=60.0,
        step=5.0,
        max_frames=100,
        camera_id=0,
    )

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Algorithm: {result.get('algorithm', 'hog')}")
    print(f"Frames processed: {result.get('frames_processed', 0)}")
    print(f"Human detections: {result.get('detections_count', 0)}")
    print(f"Unique angles measured: {result.get('num_angles_tested', 0)}")

    if result.get("best_snr") is not None:
        best_idx = int(np.argmax(result["snr_coarse"]))
        print(f"\nBest beam angle: {result['best_local']:.2f} degrees")
        print(f"Best SNR achieved: {result['best_snr']:.2f} dB")
        print(f"Best power: {result['pwr_coarse'][best_idx]:.4f}")

        if result.get("local_coarse"):
            print(f"\nAll measured angles: {[f'{a:.1f}' for a in result['local_coarse']]}")
            print(
                f"All measured SNRs: {[f'{s:.1f}' for s in result['snr_coarse']]}"
            )
    else:
        print("\nNo successful measurements. Check camera and lighting.")


def example_with_video_recording():
    """HOG detection with video output."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: HOG Detection with Video Recording")
    print("=" * 70)

    print("\nStarting HOG detection with video recording...")
    print("Output will be saved to: hog_detection_output.avi\n")

    result = run_hog_sweep(
        fov=60.0,
        step=5.0,
        max_frames=100,
        camera_id=0,
        record_video=True,  # Record output video
    )

    print(f"\nProcessed {result.get('frames_processed')} frames")
    print(f"Video saved to: hog_detection_output.avi")


def example_hog_parameters():
    """HOG detection with custom parameters."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Tuning HOG Parameters")
    print("=" * 70)

    print("\nComparing different HOG detection settings:\n")

    settings = [
        {
            "name": "High Sensitivity (Detect More)",
            "params": {
                "hog_scale": 1.02,
                "hog_win_stride": (4, 4),
                "min_box_area": 1000,
            },
        },
        {
            "name": "Balanced (Default)",
            "params": {
                "hog_scale": 1.05,
                "hog_win_stride": (8, 8),
                "min_box_area": 2000,
            },
        },
        {
            "name": "Low Sensitivity (Reduce False Positives)",
            "params": {
                "hog_scale": 1.10,
                "hog_win_stride": (16, 16),
                "min_box_area": 5000,
            },
        },
    ]

    for setting in settings:
        print(f"\nTesting: {setting['name']}")
        print(f"Parameters: {setting['params']}")

        result = run_hog_sweep(
            fov=60.0,
            step=5.0,
            max_frames=50,  # Shorter for comparison
            camera_id=0,
            **setting["params"],
        )

        print(f"  Detections: {result.get('detections_count', 0)}")
        print(f"  Angles measured: {result.get('num_angles_tested', 0)}")
        if result.get("best_snr"):
            print(f"  Best SNR: {result['best_snr']:.2f} dB")


def example_multi_position_tracking():
    """Track multiple human positions over time."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Multi-Position Human Tracking")
    print("=" * 70)

    print("\nTrack beam steering as you move around in front of camera.")
    print("Move slowly for better tracking results.\n")

    result = run_hog_sweep(
        fov=60.0,
        step=5.0,
        max_frames=200,  # Track for longer
        camera_id=0,
        angle_change_threshold=2.0,  # Require larger movement
        record_video=True,
    )

    print("\n" + "=" * 70)
    print("TRACKING RESULTS")
    print("=" * 70)

    if result.get("local_coarse"):
        angles = result["local_coarse"]
        snrs = result["snr_coarse"]

        print(f"Total positions tracked: {len(angles)}")
        print(f"Angle range: {min(angles):.1f}° to {max(angles):.1f}°")
        print(f"Angle span: {max(angles) - min(angles):.1f}°")

        print(f"\nSNR statistics:")
        print(f"  Best SNR: {max(snrs):.2f} dB")
        print(f"  Worst SNR: {min(snrs):.2f} dB")
        print(f"  Average SNR: {np.mean(snrs):.2f} dB")

        print(f"\nAngle sequence (degrees):")
        angle_str = " → ".join([f"{a:.1f}" for a in angles[:20]])
        if len(angles) > 20:
            angle_str += f" ... (and {len(angles) - 20} more)"
        print(f"  {angle_str}")


def example_comparison_hog_vs_aruco():
    """Compare HOG vs ArUco detection (requires both to work)."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: HOG vs ArUco Comparison")
    print("=" * 70)

    print("\nRunning both HOG and ArUco detection for comparison.\n")

    algorithms = [
        ("HOG Human Detection", "hog"),
        ("ArUco Marker Detection", "opencv"),
    ]

    results = {}

    for name, algo in algorithms:
        print(f"\nTesting: {name}")
        print(f"{'=' * 50}")

        try:
            network = build_demo_network()
            algorithm = SweepAlgorithmLoader.get_algorithm(algo, network)
            result = algorithm.sweep(
                "AP1",
                "RIS1",
                "UE1",
                enable_feedback=False,
                fov=60.0,
                step=5.0,
                max_frames=100,
                camera_id=0,
            )
            results[name] = result
            print(f"Success: {result.get('num_angles_tested', 0)} angles measured")
        except Exception as e:
            print(f"Failed: {e}")
            results[name] = None

    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)

    print(f"\n{'Algorithm':<30} {'Detections':<15} {'Best SNR':<15}")
    print("-" * 60)

    for name, result in results.items():
        if result:
            det = result.get("detections_count", result.get("num_angles_tested", 0))
            snr = result.get("best_snr", "N/A")
            print(f"{name:<30} {det:<15} {snr:<15}")
        else:
            print(f"{name:<30} {'Failed':<15} {'N/A':<15}")


def main():
    """Run all examples."""
    print("\n")
    print("*" * 70)
    print("RISNet HOG Human Detection Examples")
    print("*" * 70)

    examples = [
        ("1", "Basic HOG Detection", example_basic_hog_detection),
        ("2", "HOG with Video Recording", example_with_video_recording),
        ("3", "Parameter Tuning", example_hog_parameters),
        ("4", "Multi-Position Tracking", example_multi_position_tracking),
        ("5", "HOG vs ArUco Comparison", example_comparison_hog_vs_aruco),
    ]

    print("\nAvailable examples:")
    for num, title, _ in examples:
        print(f"  {num}. {title}")
    print("  q. Quit")

    while True:
        choice = input("\nSelect example (1-5, q to quit): ").strip().lower()

        if choice == "q":
            print("Exiting.")
            break
        elif choice in ["1", "2", "3", "4", "5"]:
            example = next((e for e in examples if e[0] == choice), None)
            if example:
                try:
                    example[2]()
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user.")
                except Exception as e:
                    print(f"\nError: {e}")
                    import traceback

                    traceback.print_exc()
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
