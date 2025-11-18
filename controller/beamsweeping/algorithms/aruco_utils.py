"""
ArUco marker utilities for vision-based beam sweep

Provides functions for generating, saving, and managing ArUco markers
used in camera-based pose estimation and detection.
"""

import cv2
import numpy as np
import os
from pathlib import Path
from typing import Optional, List, Dict


def generate_aruco_marker(marker_id: int,
                         size: int = 200,
                         dict_type: str = "DICT_5X5_100") -> np.ndarray:
    """Generate a single ArUco marker image

    Args:
        marker_id: Unique identifier for the marker (0-49 for DICT_4X4_50)
        size: Output image size in pixels (size x size square)
        dict_type: ArUco dictionary type (default: DICT_4X4_50)
                  Other options: DICT_5X5_100, DICT_6X6_250, DICT_7X7_1000

    Returns:
        numpy.ndarray: Grayscale image of the ArUco marker

    Raises:
        ValueError: If marker_id is invalid for the dictionary
        AttributeError: If dict_type is not a valid OpenCV ArUco dictionary

    Example:
        >>> marker_img = generate_aruco_marker(0, size=200)
        >>> print(marker_img.shape)
        (200, 200)
    """
    try:
        aruco_dict = cv2.aruco.getPredefinedDictionary(
            getattr(cv2.aruco, dict_type)
        )
    except AttributeError:
        raise AttributeError(f"Invalid ArUco dictionary type: {dict_type}")

    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size)

    if marker_img is None:
        raise ValueError(f"Failed to generate marker with ID {marker_id} for {dict_type}")

    return marker_img


def save_aruco_marker(marker_id: int,
                     output_path: str,
                     size: int = 200,
                     dict_type: str = "DICT_5X5_100") -> bool:
    """Save a single ArUco marker to a file

    Args:
        marker_id: Unique identifier for the marker
        output_path: Full path where the marker image will be saved
        size: Output image size in pixels
        dict_type: ArUco dictionary type

    Returns:
        bool: True if save successful, False otherwise

    Example:
        >>> success = save_aruco_marker(0, "markers/aruco_id_0.png")
        >>> print(f"Saved: {success}")
        Saved: True
    """
    try:
        marker_img = generate_aruco_marker(marker_id, size, dict_type)

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        cv2.imwrite(str(output_file), marker_img)

        if output_file.exists():
            return True
        else:
            return False

    except Exception as e:
        print(f"Error saving marker {marker_id}: {e}")
        return False


def save_aruco_markers(marker_ids: List[int],
                      output_dir: str,
                      size: int = 200,
                      dict_type: str = "DICT_5X5_100",
                      prefix: str = "aruco_id",
                      format: str = "png") -> Dict[int, str]:
    """Save multiple ArUco markers to files

    Args:
        marker_ids: List of marker IDs to generate
        output_dir: Directory where markers will be saved
        size: Output image size in pixels
        dict_type: ArUco dictionary type
        prefix: Prefix for generated filenames (default: "aruco_id")
        format: Image format (default: "png"), options: png, jpg, bmp

    Returns:
        dict: Mapping of marker_id to output file path

    Example:
        >>> ids = list(range(5))
        >>> paths = save_aruco_markers(ids, "markers/")
        >>> print(paths)
        {0: 'markers/aruco_id_0.png', 1: 'markers/aruco_id_1.png', ...}
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_markers = {}

    for marker_id in marker_ids:
        filename = f"{prefix}_{marker_id}.{format}"
        filepath = output_dir / filename

        if save_aruco_marker(marker_id, str(filepath), size, dict_type):
            saved_markers[marker_id] = str(filepath)
            print(f"Saved {filename}")
        else:
            print(f"Failed to save marker {marker_id}")

    return saved_markers


def create_marker_grid(marker_ids: List[int],
                      grid_size: int = 2,
                      marker_size: int = 100,
                      spacing: int = 10,
                      dict_type: str = "DICT_5X5_100") -> np.ndarray:
    """Create a composite image with multiple markers arranged in a grid

    Args:
        marker_ids: List of marker IDs to arrange in grid
        grid_size: Number of markers per row/column (creates grid_size x grid_size grid)
        marker_size: Size of each individual marker in pixels
        spacing: Spacing between markers in pixels
        dict_type: ArUco dictionary type

    Returns:
        numpy.ndarray: Composite image containing all markers

    Example:
        >>> grid = create_marker_grid([0, 1, 2, 3], grid_size=2, marker_size=150)
        >>> cv2.imwrite("marker_grid.png", grid)
    """
    if len(marker_ids) > grid_size * grid_size:
        raise ValueError(
            f"Too many markers ({len(marker_ids)}) for {grid_size}x{grid_size} grid"
        )

    total_size = grid_size * marker_size + (grid_size - 1) * spacing
    grid_img = np.ones((total_size, total_size), dtype=np.uint8) * 255

    for idx, marker_id in enumerate(marker_ids):
        row = idx // grid_size
        col = idx % grid_size

        y_start = row * (marker_size + spacing)
        x_start = col * (marker_size + spacing)

        try:
            marker_img = generate_aruco_marker(marker_id, marker_size, dict_type)
            grid_img[y_start:y_start + marker_size,
                    x_start:x_start + marker_size] = marker_img
        except Exception as e:
            print(f"Error placing marker {marker_id} in grid: {e}")

    return grid_img


def get_dictionary_info(dict_type: str = "DICT_4X4_50") -> Dict[str, int]:
    """Get information about an ArUco dictionary

    Args:
        dict_type: ArUco dictionary type

    Returns:
        dict: Dictionary info with keys:
            - max_id: Maximum valid marker ID
            - bits: Bits per marker
            - markers_in_dict: Total number of markers available

    Example:
        >>> info = get_dictionary_info("DICT_4X4_50")
        >>> print(f"Max ID: {info['max_id']}")
        Max ID: 49
    """
    dict_info = {
        "DICT_4X4_50": {"max_id": 49, "bits": 16, "markers_in_dict": 50},
        "DICT_5X5_100": {"max_id": 99, "bits": 25, "markers_in_dict": 100},
        "DICT_6X6_250": {"max_id": 249, "bits": 36, "markers_in_dict": 250},
        "DICT_7X7_1000": {"max_id": 999, "bits": 49, "markers_in_dict": 1000},
        "DICT_ARUCO_ORIGINAL": {"max_id": 1023, "bits": 10, "markers_in_dict": 1024},
    }

    if dict_type in dict_info:
        return dict_info[dict_type]
    else:
        raise ValueError(f"Unknown ArUco dictionary: {dict_type}")


def validate_marker_id(marker_id: int, dict_type: str = "DICT_5X5_100") -> bool:
    """Check if a marker ID is valid for the given dictionary

    Args:
        marker_id: Marker ID to validate
        dict_type: ArUco dictionary type

    Returns:
        bool: True if marker_id is valid for the dictionary

    Example:
        >>> is_valid = validate_marker_id(5, "DICT_4X4_50")
        >>> print(is_valid)
        True
    """
    try:
        info = get_dictionary_info(dict_type)
        return 0 <= marker_id <= info["max_id"]
    except ValueError:
        return False


if __name__ == "__main__":
    print("ArUco Marker Utilities")
    print("=" * 60)

    output_dir = "aruco_markers"

    print("\nGenerating ArUco markers (IDs 0-4)...")
    marker_ids = list(range(5))
    saved = save_aruco_markers(marker_ids, output_dir, size=200)

    print(f"\nSaved markers:")
    for marker_id, filepath in saved.items():
        print(f"  ID {marker_id}: {filepath}")

    print("\nCreating marker grid (2x2)...")
    grid = create_marker_grid([0, 1, 2, 3], grid_size=2, marker_size=150)
    grid_path = os.path.join(output_dir, "marker_grid.png")
    cv2.imwrite(grid_path, grid)
    print(f"Saved marker grid to: {grid_path}")

    print("\nDictionary info (DICT_4X4_50):")
    info = get_dictionary_info("DICT_4X4_50")
    for key, value in info.items():
        print(f"  {key}: {value}")
