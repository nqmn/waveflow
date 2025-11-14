"""
Generate training data for beam-prediction models using pure geometric deflection angle.

FORMULA (from risformula/formula.md):
======================================
Deflection angle (pure geometric):
  θ_rcv = |atan2(UE_y - RIS_y, UE_x - RIS_x) - atan2(AP_y - RIS_y, AP_x - RIS_x)|

This is the steering angle the RIS must apply to redirect from AP incident
direction to UE target direction (2D azimuth only).

DATASET CONSTRAINT:
- Only include geometries where: θ_rcv ≤ 60° (RIS FOV capability)
- Training labels (best_angle) = θ_rcv (the actual deflection angle)
- NO sweep(), NO physics engine
- Pure geometric sampling with strict feasibility
"""

import argparse
import csv
import os
import random
import sys
from pathlib import Path
from typing import Dict, Tuple
from multiprocessing import Pool
import time

import numpy as np

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)


FIELDNAMES = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'ue_x', 'ue_y', 'ue_z',
    'd_ap_ris', 'd_ris_ue',
    'aoa', 'aod',
    'best_angle'
]


def compute_distances(ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray) -> Tuple[float, float]:
    """
    Compute distances AP-to-RIS and RIS-to-UE.

    Args:
        ap_pos: AP position [x, y, z] in meters
        ris_pos: RIS position [x, y, z] in meters
        ue_pos: UE position [x, y, z] in meters

    Returns:
        Tuple: (d_ap_ris, d_ris_ue) in meters
    """
    d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))
    d_ris_ue = float(np.linalg.norm(ue_pos - ris_pos))
    return d_ap_ris, d_ris_ue


def compute_angles(ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray) -> Tuple[float, float]:
    """
    Compute AoA (Angle of Arrival) and AoD (Angle of Departure) from formula.md:

    AoA = Incident azimuth angle: atan2(AP_y - RIS_y, AP_x - RIS_x)
    AoD = Reflected azimuth angle: atan2(UE_y - RIS_y, UE_x - RIS_x)

    Both normalized to [0°, 360°) for consistency.

    Args:
        ap_pos: AP position [x, y, z] in meters
        ris_pos: RIS position [x, y, z] in meters
        ue_pos: UE position [x, y, z] in meters

    Returns:
        Tuple: (aoa, aod) in degrees, both in [0°, 360°)
    """
    # Extract 2D positions (XY plane only, consistent with deflection angle formula)
    ap_2d = ap_pos[:2]
    ris_2d = ris_pos[:2]
    ue_2d = ue_pos[:2]

    # Calculate azimuth angles in degrees
    aoa = np.degrees(np.arctan2(ap_2d[1] - ris_2d[1], ap_2d[0] - ris_2d[0]))
    aod = np.degrees(np.arctan2(ue_2d[1] - ris_2d[1], ue_2d[0] - ris_2d[0]))

    # Normalize to [0°, 360°)
    aoa = aoa % 360
    aod = aod % 360

    return aoa, aod


def compute_theta_rcv(ap_pos: np.ndarray, ris_pos: np.ndarray, ue_pos: np.ndarray) -> float:
    """
    Compute deflection angle from formula.md:

    θ_rcv = |atan2(UE-RIS) - atan2(AP-RIS)|

    This is the steering angle needed to redirect beam from AP incident
    direction to UE target direction.

    Args:
        ap_pos: AP position [x, y, z] in meters
        ris_pos: RIS position [x, y, z] in meters
        ue_pos: UE position [x, y, z] in meters

    Returns:
        Deflection angle in degrees [0°, 180°]
    """
    # Extract 2D positions (XY plane only)
    ap_2d = ap_pos[:2]
    ris_2d = ris_pos[:2]
    ue_2d = ue_pos[:2]

    # Calculate azimuth angles
    ap_angle = np.degrees(np.arctan2(ap_2d[1] - ris_2d[1], ap_2d[0] - ris_2d[0]))
    ue_angle = np.degrees(np.arctan2(ue_2d[1] - ris_2d[1], ue_2d[0] - ris_2d[0]))

    # Compute angle difference
    dtheta = ue_angle - ap_angle

    # Normalize to [-180°, 180°]
    dtheta = ((dtheta + 180) % 360) - 180

    # Return magnitude (always positive, 0° to 180°)
    return abs(dtheta)


def random_position(bounds: Dict[str, float]) -> np.ndarray:
    """
    Generate random position within bounds.

    Args:
        bounds: Dictionary with 'x_min', 'x_max', 'y_min', 'y_max', 'z_min', 'z_max'

    Returns:
        Position array [x, y, z]
    """
    return np.array([
        random.uniform(bounds['x_min'], bounds['x_max']),
        random.uniform(bounds['y_min'], bounds['y_max']),
        random.uniform(bounds['z_min'], bounds['z_max'])
    ])


def generate_valid_geometry(bounds: Dict, ris_max_angle: float = 60.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Generate random AP, RIS, UE positions with θ_rcv ≤ ris_max_angle.

    This ensures the RIS can physically achieve the required steering angle
    within its ±60° (or other max_angle) FOV capability.

    Args:
        bounds: Dict with 'ap', 'ris', 'ue' sub-dicts containing bounds
        ris_max_angle: Maximum steering angle capability (±max_angle)

    Returns:
        Tuple: (ap_pos, ris_pos, ue_pos, theta_rcv)
    """
    max_attempts = 500  # Increased attempts to ensure boundary values are sampled

    for attempt in range(max_attempts):
        # Generate random positions
        ap_pos = random_position(bounds['ap'])
        ris_pos = random_position(bounds['ris'])
        ue_pos = random_position(bounds['ue'])

        # Calculate deflection angle
        theta_rcv = compute_theta_rcv(ap_pos, ris_pos, ue_pos)

        # Accept if within RIS capability (inclusive of boundary)
        if theta_rcv <= ris_max_angle:
            return ap_pos, ris_pos, ue_pos, theta_rcv

    raise RuntimeError(
        f"Failed to generate valid geometry after {max_attempts} attempts. "
        f"Try expanding position bounds or reducing max_angle."
    )


def build_sample(bounds: Dict, ris_max_angle: float = 60.0) -> Dict:
    """
    Build a single training sample.

    Args:
        bounds: Position bounds dict
        ris_max_angle: Maximum steering angle (°)

    Returns:
        Sample dict with positions, distances, angles, and best_angle
    """
    ap_pos, ris_pos, ue_pos, theta_rcv = generate_valid_geometry(bounds, ris_max_angle)

    # Compute derived features
    d_ap_ris, d_ris_ue = compute_distances(ap_pos, ris_pos, ue_pos)
    aoa, aod = compute_angles(ap_pos, ris_pos, ue_pos)

    # Round best_angle to nearest integer degree
    best_angle_rounded = float(round(theta_rcv))

    sample = {
        'ap_pos': ap_pos.tolist(),
        'ris_pos': ris_pos.tolist(),
        'ue_pos': ue_pos.tolist(),
        'd_ap_ris': d_ap_ris,
        'd_ris_ue': d_ris_ue,
        'aoa': aoa,
        'aod': aod,
        'best_angle': best_angle_rounded
    }
    return sample


def build_sample_worker(args_tuple: Tuple) -> Tuple:
    """
    Worker function for multiprocessing pool.

    Args:
        args_tuple: (idx, bounds, ris_max_angle, seed_offset)

    Returns:
        Tuple: (idx, sample, error)
    """
    idx, bounds, ris_max_angle, seed_offset = args_tuple

    # Set unique seed for each worker
    random.seed(seed_offset + idx)
    np.random.seed(seed_offset + idx)

    try:
        sample = build_sample(bounds, ris_max_angle)
        return idx, sample, None
    except Exception as exc:
        return idx, None, str(exc)


def flatten_sample(sample: Dict) -> Dict:
    """Flatten sample to CSV format."""
    return {
        'ap_x': sample['ap_pos'][0],
        'ap_y': sample['ap_pos'][1],
        'ap_z': sample['ap_pos'][2],
        'ris_x': sample['ris_pos'][0],
        'ris_y': sample['ris_pos'][1],
        'ris_z': sample['ris_pos'][2],
        'ue_x': sample['ue_pos'][0],
        'ue_y': sample['ue_pos'][1],
        'ue_z': sample['ue_pos'][2],
        'd_ap_ris': sample['d_ap_ris'],
        'd_ris_ue': sample['d_ris_ue'],
        'aoa': sample['aoa'],
        'aod': sample['aod'],
        'best_angle': sample['best_angle']
    }


def main():
    parser = argparse.ArgumentParser(description="Generate pure geometric beam dataset")
    parser.add_argument('--samples', type=int, default=5000, help='Number of samples to generate')
    parser.add_argument('--output', type=Path,
                       default=Path('controller/beamsweeping/ml/data/beam_dataset.csv'),
                       help='Output CSV file')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--cores', type=int, default=4, help='Number of CPU cores')
    args = parser.parse_args()

    # Position bounds (20m × 20m × 5m space)
    bounds = {
        'ap':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ue':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
    }

    # RIS FOV constraint
    ris_max_angle = 60.0

    print(f"Generating {args.samples} samples using {args.cores} cores...")
    start_time = time.time()

    # Prepare worker arguments
    worker_args = [
        (idx, bounds, ris_max_angle, args.seed)
        for idx in range(args.samples)
    ]

    samples_dict = {}
    error_count = 0
    completed = 0

    with Pool(processes=args.cores) as pool:
        for idx, sample, error in pool.imap_unordered(build_sample_worker, worker_args):
            completed += 1

            if error:
                print(f"[{completed:5d}/{args.samples}] Error in sample {idx}: {error}")
                error_count += 1
            elif completed % 100 == 0 or completed == args.samples:
                elapsed = time.time() - start_time
                rate = completed / elapsed
                remaining = (args.samples - completed) / rate if rate > 0 else 0
                print(f"[{completed:5d}/{args.samples}] {rate:.1f} samples/sec | ETA: {remaining:.0f}s")

            if sample is not None:
                samples_dict[idx] = sample

    elapsed_time = time.time() - start_time

    # Write to CSV
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(samples_dict)} samples to {args.output}...")

    with args.output.open('w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for idx in sorted(samples_dict.keys()):
            writer.writerow(flatten_sample(samples_dict[idx]))

    print(f"✓ Wrote {len(samples_dict)} samples to {args.output}")
    print(f"✗ Errors: {error_count}")
    print(f"⏱ Total time: {elapsed_time:.2f}s ({args.samples/elapsed_time:.1f} samples/sec)")

    # Statistics
    if samples_dict:
        angles = [s['best_angle'] for s in samples_dict.values()]
        print(f"\nDataset statistics:")
        print(f"  Min angle: {min(angles):.2f}°")
        print(f"  Max angle: {max(angles):.2f}°")
        print(f"  Mean angle: {np.mean(angles):.2f}°")
        print(f"  Median angle: {np.median(angles):.2f}°")
        print(f"  All angles ≤ 60°: {all(a <= 60.0 for a in angles)}")


if __name__ == "__main__":
    main()
