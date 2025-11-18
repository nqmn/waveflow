#!/usr/bin/env python3
"""
Example script demonstrating ArUco marker generation utilities

This script shows various ways to use the aruco_utils module to generate
and manage ArUco markers for vision-based beam sweep testing.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.aruco_utils import (
    generate_aruco_marker,
    save_aruco_marker,
    save_aruco_markers,
    create_marker_grid,
    get_dictionary_info,
    validate_marker_id,
)

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV (cv2) not available. Display features will be skipped.")


def example_1_basic_generation():
    """Example 1: Generate and save a single marker"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Generate and Save a Single Marker")
    print("=" * 70)

    print("\nGenerating marker ID 0...")
    success = save_aruco_marker(
        marker_id=0,
        output_path="aruco_markers/aruco_id_0.png",
        size=200
    )

    if success:
        print("✓ Successfully saved: aruco_markers/aruco_id_0.png")
    else:
        print("✗ Failed to save marker")


def example_2_batch_generation():
    """Example 2: Generate multiple markers at once"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Generate Multiple Markers in Batch")
    print("=" * 70)

    print("\nGenerating markers 0-4...")
    marker_ids = list(range(5))
    paths = save_aruco_markers(
        marker_ids=marker_ids,
        output_dir="aruco_markers/batch/",
        size=200,
        prefix="aruco_id"
    )

    print(f"\nGenerated {len(paths)} markers:")
    for marker_id, filepath in sorted(paths.items()):
        print(f"  ID {marker_id}: {filepath}")


def example_3_marker_grid():
    """Example 3: Create a printable marker grid"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Create a Printable Marker Grid")
    print("=" * 70)

    if not CV2_AVAILABLE:
        print("OpenCV not available, skipping grid creation")
        return

    print("\nCreating a 2×2 grid of markers...")
    grid = create_marker_grid(
        marker_ids=[0, 1, 2, 3],
        grid_size=2,
        marker_size=150,
        spacing=10
    )

    output_path = "aruco_markers/marker_grid_2x2.png"
    cv2.imwrite(output_path, grid)
    print(f"✓ Grid saved to: {output_path}")
    print(f"  Grid size: {grid.shape}")


def example_4_in_memory_generation():
    """Example 4: Generate markers in memory without saving"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: In-Memory Marker Generation")
    print("=" * 70)

    print("\nGenerating markers 5-9 in memory...")
    markers = {}
    for marker_id in range(5, 10):
        try:
            marker = generate_aruco_marker(marker_id, size=200)
            markers[marker_id] = marker
            print(f"  ✓ Generated marker {marker_id}: shape {marker.shape}")
        except Exception as e:
            print(f"  ✗ Failed to generate marker {marker_id}: {e}")

    print(f"\nSuccessfully generated {len(markers)} markers in memory")


def example_5_validation():
    """Example 5: Validate marker IDs"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Validate Marker IDs")
    print("=" * 70)

    dict_type = "DICT_4X4_50"
    print(f"\nValidating marker IDs for {dict_type}:")

    test_ids = [0, 25, 49, 50, 100, -1]
    for marker_id in test_ids:
        is_valid = validate_marker_id(marker_id, dict_type)
        status = "✓ Valid" if is_valid else "✗ Invalid"
        print(f"  {status}: Marker ID {marker_id}")


def example_6_dictionary_info():
    """Example 6: Get dictionary information"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Dictionary Information")
    print("=" * 70)

    dictionaries = [
        "DICT_4X4_50",
        "DICT_5X5_100",
        "DICT_6X6_250",
        "DICT_7X7_1000",
    ]

    print("\nAvailable ArUco Dictionaries:")
    print("-" * 70)
    print(f"{'Dictionary':<25} {'Max ID':<10} {'Total':<10} {'Bits':<10}")
    print("-" * 70)

    for dict_type in dictionaries:
        try:
            info = get_dictionary_info(dict_type)
            print(f"{dict_type:<25} {info['max_id']:<10} "
                  f"{info['markers_in_dict']:<10} {info['bits']:<10}")
        except ValueError as e:
            print(f"{dict_type:<25} ERROR: {e}")

    print("-" * 70)


def example_7_large_batch():
    """Example 7: Generate a large batch of markers"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Generate Large Batch (All 50 markers in DICT_4X4_50)")
    print("=" * 70)

    print("\nGenerating all 50 markers from DICT_4X4_50...")
    marker_ids = list(range(50))
    paths = save_aruco_markers(
        marker_ids=marker_ids,
        output_dir="aruco_markers/all_50/",
        size=150,
        prefix="marker"
    )

    print(f"✓ Successfully generated {len(paths)} markers")
    print(f"  Output directory: aruco_markers/all_50/")


def example_8_custom_dictionary():
    """Example 8: Use different ArUco dictionary"""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Use Different ArUco Dictionary (DICT_5X5_100)")
    print("=" * 70)

    print("\nGenerating markers 0-4 with DICT_5X5_100...")
    marker_ids = [0, 1, 2, 3, 4]
    paths = save_aruco_markers(
        marker_ids=marker_ids,
        output_dir="aruco_markers/dict_5x5/",
        size=200,
        dict_type="DICT_5X5_100",
        prefix="marker_5x5"
    )

    print(f"✓ Generated {len(paths)} markers with DICT_5X5_100")
    for marker_id, filepath in sorted(paths.items()):
        print(f"  Marker {marker_id}: {filepath}")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("ARUCO MARKER GENERATION EXAMPLES")
    print("=" * 70)

    examples = [
        example_1_basic_generation,
        example_2_batch_generation,
        example_3_marker_grid,
        example_4_in_memory_generation,
        example_5_validation,
        example_6_dictionary_info,
        example_7_large_batch,
        example_8_custom_dictionary,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\n✗ Error in {example_func.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nGenerated files are located in:")
    print("  - aruco_markers/")
    print("\nFor more information, see: ARUCO_MARKER_GUIDE.md")


if __name__ == "__main__":
    main()
