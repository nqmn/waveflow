"""Generate training data for beam-prediction models."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from core import RISNetwork
from core.angle_utils import compute_optimal_ris_normal


FIELDNAMES = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'ue_x', 'ue_y', 'ue_z',
    'ap_power_dBm', 'ap_freq',
    'ris_N', 'ris_bits',
    'ris_normal_deg',  # NEW: RIS normal angle (bisector of AP and UE)
    'best_angle', 'best_snr'
]


def random_position(bounds: Dict[str, float], grid_spacing: float = 1.0) -> np.ndarray:
    """
    Generate random position with stratified sampling using grid spacing.
    This ensures even coverage across the spatial domain instead of pure random.
    Grid spacing of 1m means we divide each dimension into 1m bins and sample within bins.
    """
    # Create grid bins of size grid_spacing
    x_bins = np.arange(bounds['x_min'], bounds['x_max'] + grid_spacing, grid_spacing)
    y_bins = np.arange(bounds['y_min'], bounds['y_max'] + grid_spacing, grid_spacing)
    z_bins = np.arange(bounds['z_min'], bounds['z_max'] + grid_spacing, grid_spacing)

    # Randomly select a bin for each dimension
    x_bin_idx = random.randint(0, len(x_bins) - 2)
    y_bin_idx = random.randint(0, len(y_bins) - 2)
    z_bin_idx = random.randint(0, len(z_bins) - 2)

    # Sample uniformly within the selected bin
    x = random.uniform(x_bins[x_bin_idx], x_bins[x_bin_idx + 1])
    y = random.uniform(y_bins[y_bin_idx], y_bins[y_bin_idx + 1])
    z = random.uniform(z_bins[z_bin_idx], z_bins[z_bin_idx + 1])

    return np.array([x, y, z])


def is_within_fov(offset_angle: float, max_angle: float) -> bool:
    """Check if an offset angle is within FOV constraint."""
    # Normalize offset to [-180, 180]
    offset = ((offset_angle + 180) % 360) - 180
    return abs(offset) <= max_angle


def compute_offset_from_normal(abs_angle: float, normal_angle: float) -> float:
    """Compute offset angle relative to RIS normal."""
    offset = abs_angle - normal_angle
    # Normalize to [-180, 180]
    return ((offset + 180) % 360) - 180


def generate_valid_geometry(bounds: Dict[str, float], ris_max_angle: float = 60.0,
                           grid_spacing: float = 1.0) -> tuple:
    """
    Generate AP, RIS, UE positions that satisfy FOV constraints.

    This ensures:
    1. AP is within RIS FOV (±ris_max_angle from RIS normal)
    2. UE is within RIS FOV (±ris_max_angle from RIS normal)
    3. No skipping needed, every sample is valid

    Returns: (ap_pos, ris_pos, ue_pos)
    """
    max_attempts = 100

    for attempt in range(max_attempts):
        # Generate RIS position
        ris_pos = random_position(bounds['ris'], grid_spacing=grid_spacing)

        # Generate AP position
        ap_pos = random_position(bounds['ap'], grid_spacing=grid_spacing)

        # Generate UE position
        ue_pos = random_position(bounds['ue'], grid_spacing=grid_spacing)

        # Compute angles from RIS perspective
        ap_vec = ap_pos - ris_pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
        ue_vec = ue_pos - ris_pos
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Compute optimal RIS normal as bisector
        ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)

        # Check if AP is within FOV relative to RIS normal
        ap_offset = compute_offset_from_normal(ap_angle, ris_normal)
        if not is_within_fov(ap_offset, ris_max_angle):
            continue  # AP outside FOV, try again

        # Check if UE is within FOV relative to RIS normal
        ue_offset = compute_offset_from_normal(ue_angle, ris_normal)
        if not is_within_fov(ue_offset, ris_max_angle):
            continue  # UE outside FOV, try again

        # Both AP and UE are within FOV
        return ap_pos, ris_pos, ue_pos

    # If we can't generate valid geometry after max_attempts, raise error
    raise RuntimeError(f"Failed to generate valid geometry after {max_attempts} attempts")


def build_sample(net: RISNetwork, bounds, ap_cfg, ris_cfg, ue_cfg, ris_max_angle: float = 60.0,
                 grid_spacing: float = 1.0):
    """
    Build a training sample with guaranteed valid FOV geometry.

    All generated samples are guaranteed to satisfy:
    - AP within RIS FOV (±ris_max_angle from RIS normal)
    - UE within RIS FOV (±ris_max_angle from RIS normal)
    - No FOV violation errors
    """
    net.nodes.clear()

    # Generate positions that satisfy FOV constraints
    ap_pos, ris_pos, ue_pos = generate_valid_geometry(
        bounds, ris_max_angle=ris_max_angle, grid_spacing=grid_spacing
    )

    net.add_ap('AP', *ap_pos, power_dBm=ap_cfg['power_dBm'], freq=ap_cfg['freq'])
    net.add_ris(
        'RIS', *ris_pos,
        N=ris_cfg['N'], bits=ris_cfg['bits'],
        max_angle_deg=ris_max_angle  # Explicitly set RIS max angle
    )
    net.add_ue('UE', *ue_pos)

    # Compute RIS normal as bisector of AP and UE (matches connect/sweep behavior)
    ap_vec = ap_pos - ris_pos
    ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
    ue_vec = ue_pos - ris_pos
    ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))
    ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)

    # Set RIS normal before sweep (ensures connect uses correct normal)
    net.get('RIS').normal_angle_deg = ris_normal

    result = net.sweep('AP', 'RIS', 'UE', fov=bounds['fov'], step=bounds['step'])

    best_angle = result['best_local_fine']
    snr = result['best_snr_fine']

    sample = {
        'ap_pos': ap_pos.tolist(),
        'ris_pos': ris_pos.tolist(),
        'ue_pos': ue_pos.tolist(),
        'ap_power_dBm': ap_cfg['power_dBm'],
        'ap_freq': ap_cfg['freq'],
        'ris_N': ris_cfg['N'],
        'ris_bits': ris_cfg['bits'],
        'ris_normal_deg': float(ris_normal),  # Include RIS normal in training data
        'best_angle': best_angle,
        'best_snr': snr
    }
    return sample


def flatten_sample(sample: Dict[str, Any]) -> Dict[str, float]:
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
        'ap_power_dBm': sample['ap_power_dBm'],
        'ap_freq': sample['ap_freq'],
        'ris_N': sample['ris_N'],
        'ris_bits': sample['ris_bits'],
        'ris_normal_deg': sample['ris_normal_deg'],  # NEW: Include RIS normal
        'best_angle': sample['best_angle'],
        'best_snr': sample['best_snr']
    }


def main():
    parser = argparse.ArgumentParser(description="Generate training data for beam ML models")
    parser.add_argument('--samples', type=int, default=5000, help='Number of random topologies')
    parser.add_argument('--output', type=Path,
                        default=Path('controller/beamsweeping/ml/data/beam_dataset.csv'),
                        help='Output CSV file')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    # Improved bounds: 1m grid spacing for better coverage
    # This ensures we have samples at regular intervals
    bounds = {
        'fov': 60.0,
        'step': 10.0,
        'ap': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ue': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
    }

    ap_cfg = {'power_dBm': 20.0, 'freq': 5.8e9}
    ris_cfg = {'N': 16, 'bits': 1}
    ue_cfg = {}

    net = RISNetwork()

    samples: List[Dict[str, Any]] = []
    grid_spacing = 1.0  # 1 meter spacing for stratified sampling
    ris_max_angle = 60.0  # RIS FOV: ±60°

    for idx in range(args.samples):
        try:
            sample = build_sample(net, bounds, ap_cfg, ris_cfg, ue_cfg,
                                ris_max_angle=ris_max_angle, grid_spacing=grid_spacing)
            samples.append(sample)
            if (idx + 1) % 500 == 0:
                print(f"Generated {idx + 1}/{args.samples} samples...")
        except Exception as exc:
            # Should rarely happen now, as generate_valid_geometry ensures valid FOV
            print(f"Error generating sample {idx + 1}: {exc}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for sample in samples:
            writer.writerow(flatten_sample(sample))

    print(f"Wrote {len(samples)} samples to {args.output}")


if __name__ == "__main__":
    main()
