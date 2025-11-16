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
import itertools
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple
from multiprocessing import Pool
import time

import numpy as np

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.link_budget import build_config, compute_ris_link_metrics


FIELDNAMES = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'ue_x', 'ue_y', 'ue_z',
    'd_ap_ris', 'd_ris_ue',
    'aoa_sin', 'aoa_cos', 'aod_sin', 'aod_cos',
    'dx', 'dy', 'dz', 'az_sin', 'az_cos', 'el_sin', 'el_cos',
    'ap_az_sin', 'ap_az_cos', 'ap_el_sin', 'ap_el_cos',
    'spec_sin', 'spec_cos',
    'align_cos', 'align_sin',
    'snr_dB', 'rssi_dBm',
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


def stratified_positions(bounds: Dict[str, float], bins: Tuple[int, int, int], rng: random.Random) -> List[np.ndarray]:
    """Generate one representative position per stratified bin."""
    if bins[0] <= 0 or bins[1] <= 0 or bins[2] <= 0:
        raise ValueError("Bin counts must be positive integers")

    x_edges = np.linspace(bounds['x_min'], bounds['x_max'], bins[0] + 1)
    y_edges = np.linspace(bounds['y_min'], bounds['y_max'], bins[1] + 1)
    z_edges = np.linspace(bounds['z_min'], bounds['z_max'], bins[2] + 1)

    positions = []
    for ix in range(bins[0]):
        for iy in range(bins[1]):
            for iz in range(bins[2]):
                x = rng.uniform(x_edges[ix], x_edges[ix + 1])
                y = rng.uniform(y_edges[iy], y_edges[iy + 1])
                z = rng.uniform(z_edges[iz], z_edges[iz + 1])
                positions.append(np.array([x, y, z]))
    return positions


def generate_stratified_samples(
    bounds: Dict,
    ris_max_angle: float,
    num_samples: int,
    bins_config: Dict[str, Tuple[int, int, int]],
    seed: int,
    physics_config: Dict[str, float],
) -> Dict[int, Dict]:
    """Produce stratified samples using precomputed AP/RIS/UE bins."""
    rng = random.Random(seed)

    ap_positions = stratified_positions(bounds['ap'], bins_config['ap'], rng)
    ris_positions = stratified_positions(bounds['ris'], bins_config['ris'], rng)
    ue_positions = stratified_positions(bounds['ue'], bins_config['ue'], rng)

    rng.shuffle(ap_positions)
    rng.shuffle(ris_positions)
    rng.shuffle(ue_positions)

    ap_cycle = itertools.cycle(ap_positions)
    ris_cycle = itertools.cycle(ris_positions)
    ue_cycle = itertools.cycle(ue_positions)

    samples = {}
    attempts = 0
    max_attempts = max(num_samples * 20, len(ap_positions) * len(ris_positions) * len(ue_positions) * 2)

    while len(samples) < num_samples and attempts < max_attempts:
        ap_pos = next(ap_cycle)
        ris_pos = next(ris_cycle)
        ue_pos = next(ue_cycle)

        theta_rcv = compute_theta_rcv(ap_pos, ris_pos, ue_pos)
        if theta_rcv <= ris_max_angle:
            d_ap_ris, d_ris_ue = compute_distances(ap_pos, ris_pos, ue_pos)
            aoa, aod = compute_angles(ap_pos, ris_pos, ue_pos)
            sample = {
                'ap_pos': ap_pos.tolist(),
                'ris_pos': ris_pos.tolist(),
                'ue_pos': ue_pos.tolist(),
                'd_ap_ris': d_ap_ris,
                'd_ris_ue': d_ris_ue,
                'aoa': aoa,
                'aod': aod,
                'best_angle': float(round(theta_rcv)),
            }
            _add_angle_trigs(sample, aoa, aod)
            _add_ap_ris_orientation(sample)
            _add_physics_metrics(sample, physics_config)
            samples[len(samples)] = sample
        attempts += 1

    return samples


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
    _add_angle_trigs(sample, aoa, aod)
    _add_ap_ris_orientation(sample)
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
        'aoa_sin': sample['aoa_sin'],
        'aoa_cos': sample['aoa_cos'],
        'aod_sin': sample['aod_sin'],
        'aod_cos': sample['aod_cos'],
        'dx': sample['dx'],
        'dy': sample['dy'],
        'dz': sample['dz'],
        'az_sin': sample['az_sin'],
        'az_cos': sample['az_cos'],
        'el_sin': sample['el_sin'],
        'el_cos': sample['el_cos'],
        'ap_az_sin': sample['ap_az_sin'],
        'ap_az_cos': sample['ap_az_cos'],
        'ap_el_sin': sample['ap_el_sin'],
        'ap_el_cos': sample['ap_el_cos'],
        'spec_sin': sample['spec_sin'],
        'spec_cos': sample['spec_cos'],
        'align_cos': sample['align_cos'],
        'align_sin': sample['align_sin'],
        'snr_dB': sample['snr_dB'],
        'rssi_dBm': sample['rssi_dBm'],
        'best_angle': sample['best_angle']
    }


def _wrap_angle(angle: float) -> float:
    """Normalize angle to [-180°, 180°]."""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


def _absolute_angle(angle: float) -> float:
    """Normalize an angle to the [0°, 360°) range."""
    return angle % 360.0


def _signed_local_deflection(aoa_deg: float, aod_deg: float) -> float:
    """Return the signed deflection from the incident direction."""
    return _wrap_angle(aod_deg - aoa_deg)


def _add_ap_ris_orientation(sample: Dict) -> None:
    """Annotate the sample with AP→RIS offset + sin/cos of azimuth/elevation."""
    ap_pos = np.array(sample['ap_pos'], dtype=float)
    ris_pos = np.array(sample['ris_pos'], dtype=float)
    dx, dy, dz = (ris_pos - ap_pos).tolist()
    azimuth = math.atan2(dy, dx)
    elevation = math.atan2(dz, math.hypot(dx, dy))
    sample['dx'] = float(dx)
    sample['dy'] = float(dy)
    sample['dz'] = float(dz)
    sample['az_sin'] = float(math.sin(azimuth))
    sample['az_cos'] = float(math.cos(azimuth))
    sample['el_sin'] = float(math.sin(elevation))
    sample['el_cos'] = float(math.cos(elevation))
    sample['ap_az_sin'] = sample['az_sin']
    sample['ap_az_cos'] = sample['az_cos']
    sample['ap_el_sin'] = sample['el_sin']
    sample['ap_el_cos'] = sample['el_cos']
    aoa_rad = sample.get('_aoa_rad')
    if aoa_rad is None:
        aoa_rad = math.atan2(sample['aoa_sin'], sample['aoa_cos'])
    spec_rad = 2.0 * azimuth - aoa_rad
    sample['spec_sin'] = float(math.sin(spec_rad))
    sample['spec_cos'] = float(math.cos(spec_rad))
    sample.pop('_aoa_rad', None)
    sample['align_cos'] = float(sample['az_cos'] * sample['aoa_cos'] + sample['az_sin'] * sample['aoa_sin'])
    sample['align_sin'] = float(sample['az_sin'] * sample['aoa_cos'] - sample['az_cos'] * sample['aoa_sin'])


def _add_angle_trigs(sample: Dict, aoa_deg: float, aod_deg: float) -> None:
    """Cache sine/cosine of AoA/AoD for the dataset export."""
    rad = math.radians
    aoa_rad = rad(aoa_deg)
    sample['aoa_sin'] = float(math.sin(aoa_rad))
    sample['aoa_cos'] = float(math.cos(aoa_rad))
    sample['aod_sin'] = float(math.sin(rad(aod_deg)))
    sample['aod_cos'] = float(math.cos(rad(aod_deg)))
    sample['_aoa_rad'] = aoa_rad


def _add_physics_metrics(sample: Dict, physics_config: Dict[str, float]) -> None:
    """Annotate the sample with SNR and RSSI using a shared RIS budget."""
    ap_pos = np.array(sample['ap_pos'], dtype=float)
    ris_pos = np.array(sample['ris_pos'], dtype=float)
    ue_pos = np.array(sample['ue_pos'], dtype=float)
    beam_angle = float(sample['aod'])

    metrics = compute_ris_link_metrics(
        ap_pos=ap_pos,
        ris_pos=ris_pos,
        ue_pos=ue_pos,
        beam_angle_deg=beam_angle,
        physics_config=physics_config
    )

    sample['snr_dB'] = float(metrics['snr_dB'])
    sample['rssi_dBm'] = float(metrics['rssi_dBm'])



def _sample_ue_within_fov(ris_pos: np.ndarray, ap_pos: np.ndarray, rng: random.Random,
                          ris_max_angle: float, distance_range: Tuple[float, float],
                          z_range: Tuple[float, float] = (0.0, 1.0)) -> np.ndarray:
    ris_normal = 0.0
    ris_fov_min = ris_normal - ris_max_angle
    ris_fov_max = ris_normal + ris_max_angle

    # Calculate AP angle relative to RIS
    ap_angle = math.degrees(math.atan2(ap_pos[1] - ris_pos[1], ap_pos[0] - ris_pos[0]))
    ap_angle = _wrap_angle(ap_angle)
    ap_within_fov = ris_fov_min <= ap_angle <= ris_fov_max

    # Deflection constraint window
    min_from_ap = ap_angle - ris_max_angle
    max_from_ap = ap_angle + ris_max_angle
    intersect_min = max(ris_fov_min, min_from_ap)
    intersect_max = min(ris_fov_max, max_from_ap)

    if intersect_min <= intersect_max:
        min_angle = intersect_min
        max_angle = intersect_max
    else:
        if ap_within_fov:
            min_angle = ris_fov_min
            max_angle = ris_fov_max
        else:
            dist_to_min = abs(ap_angle - ris_fov_min)
            dist_to_max = abs(ap_angle - ris_fov_max)
            while dist_to_min > 180:
                dist_to_min = 360 - dist_to_min
            while dist_to_max > 180:
                dist_to_max = 360 - dist_to_max
            if dist_to_min <= dist_to_max:
                min_angle = max(ris_fov_min, ap_angle - ris_max_angle)
                max_angle = ris_fov_max
            else:
                min_angle = ris_fov_min
                max_angle = min(ris_fov_max, ap_angle + ris_max_angle)

    if min_angle > max_angle:
        min_angle = ris_fov_min
        max_angle = ris_fov_max

    ue_angle = rng.uniform(min_angle, max_angle)
    distance = rng.uniform(distance_range[0], distance_range[1])
    ue_x = ris_pos[0] + distance * math.cos(math.radians(ue_angle))
    ue_y = ris_pos[1] + distance * math.sin(math.radians(ue_angle))
    ue_z = rng.uniform(z_range[0], z_range[1])
    return np.array([ue_x, ue_y, ue_z])


def generate_ris_aware_sample(bounds: Dict, ris_max_angle: float,
                             distance_range: Tuple[float, float],
                             rng: random.Random,
                             physics_config: Dict[str, float]) -> Dict:
    """Generate a sample following the CLI’s `add random` RIS-aware placement."""
    ris_x = rng.uniform(bounds['ris']['x_min'], bounds['ris']['x_max'])
    ris_y = rng.uniform(bounds['ris']['y_min'], bounds['ris']['y_max'])
    ris_z = rng.uniform(0.0, 1.0)
    ris_pos = np.array([ris_x, ris_y, ris_z])

    ap_distance = rng.uniform(distance_range[0], distance_range[1])
    ap_angle = rng.uniform(-ris_max_angle, ris_max_angle)
    ap_x = ris_x + ap_distance * math.cos(math.radians(ap_angle))
    ap_y = ris_y + ap_distance * math.sin(math.radians(ap_angle))
    ap_z = rng.uniform(0.0, 1.0)
    ap_pos = np.array([ap_x, ap_y, ap_z])

    ue_pos = _sample_ue_within_fov(
        ris_pos, ap_pos, rng, ris_max_angle, distance_range, z_range=(0.0, 1.0)
    )
    theta_rcv = compute_theta_rcv(ap_pos, ris_pos, ue_pos)
    d_ap_ris, d_ris_ue = compute_distances(ap_pos, ris_pos, ue_pos)
    aoa, aod = compute_angles(ap_pos, ris_pos, ue_pos)

    sample = {
        'ap_pos': ap_pos.tolist(),
        'ris_pos': ris_pos.tolist(),
        'ue_pos': ue_pos.tolist(),
        'd_ap_ris': d_ap_ris,
        'd_ris_ue': d_ris_ue,
        'aoa': aoa,
        'aod': aod,
        'best_angle': float(round(theta_rcv)),
    }
    _add_angle_trigs(sample, aoa, aod)
    _add_ap_ris_orientation(sample)
    _add_physics_metrics(sample, physics_config)
    return sample
def build_stratified_dataset(args, bounds, ris_max_angle, physics_config: Dict[str, float]):
    """Generate samples using stratified coverage."""
    bins_config = {
        'ap': tuple(args.ap_bins),
        'ris': tuple(args.ris_bins),
        'ue': tuple(args.ue_bins),
    }

    print(f"Generating {args.samples} stratified samples with bins AP{bins_config['ap']} RIS{bins_config['ris']} UE{bins_config['ue']}...")
    start_time = time.time()

    samples_dict = generate_stratified_samples(
        bounds,
        ris_max_angle,
        args.samples,
        bins_config,
        args.seed,
        physics_config
    )

    elapsed = time.time() - start_time
    if len(samples_dict) < args.samples:
        print(f"⚠️  Stratified generation produced {len(samples_dict)} samples (requested {args.samples}). Consider loosening the RIS FOV or increasing bins.")

    return samples_dict, 0, elapsed


def build_ris_aware_dataset(args, bounds, ris_max_angle, physics_config: Dict[str, float]):
    """Generate samples using the CLI’s RIS-aware placement logic."""
    rng = random.Random(args.seed)
    samples_dict = {}
    start_time = time.time()
    print(f"Generating {args.samples} RIS-aware samples (distance range {args.distance_min}-{args.distance_max} m)...")

    for idx in range(args.samples):
        sample = generate_ris_aware_sample(
            bounds,
            ris_max_angle,
            (args.distance_min, args.distance_max),
            rng,
            physics_config
        )
        samples_dict[idx] = sample
        if args.verbose and (idx + 1) % 1000 == 0:
            print(f"  Generated {idx + 1}/{args.samples} samples...")

    elapsed = time.time() - start_time
    return samples_dict, 0, elapsed


def main():
    parser = argparse.ArgumentParser(description="Generate beam dataset (stratified or RIS-aware)")
    parser.add_argument('--samples', type=int, default=5000, help='Number of samples to generate')
    parser.add_argument('--output', type=Path,
                        default=Path('controller/beamsweeping/ml/data/beam_dataset.csv'),
                        help='Output CSV file')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--sampling-mode', choices=('stratified', 'ris-aware'),
                        default='ris-aware', help='Sampling strategy to use')
    parser.add_argument('--ap-bins', type=int, nargs=3, default=[13, 13, 3], metavar=('X', 'Y', 'Z'),
                        help='Bins per axis for AP stratification (default 13×13×3)')
    parser.add_argument('--ris-bins', type=int, nargs=3, default=[13, 13, 3], metavar=('X', 'Y', 'Z'),
                        help='Bins per axis for RIS stratification (default 13×13×3)')
    parser.add_argument('--ue-bins', type=int, nargs=3, default=[13, 13, 3], metavar=('X', 'Y', 'Z'),
                        help='Bins per axis for UE stratification (default 13×13×3)')
    parser.add_argument('--distance-min', type=float, default=5.0,
                        help='Minimum distance from RIS for AP/UE when using RIS-aware mode')
    parser.add_argument('--distance-max', type=float, default=7.0,
                        help='Maximum distance from RIS for AP/UE when using RIS-aware mode')
    parser.add_argument('--verbose', action='store_true',
                        help='Show progress when generating large datasets')
    parser.add_argument('--tx-power', type=float, default=15.0,
                        help='Transmit power per AP (dBm)')
    parser.add_argument('--ap-gain', type=float, default=16.0,
                        help='AP antenna gain (dBi)')
    parser.add_argument('--ue-gain', type=float, default=16.0,
                        help='UE antenna gain (dBi)')
    parser.add_argument('--bandwidth', type=float, default=1.0,
                        help='Signal bandwidth for SNR calculations (MHz)')
    parser.add_argument('--noise-figure', type=float, default=6.0,
                        help='Receiver noise figure (dB)')
    parser.add_argument('--frequency', type=float, default=5.8,
                        help='Carrier frequency (GHz)')
    parser.add_argument('--ris-elements', type=int, default=16,
                        help='RIS elements per side (square panel size)')
    parser.add_argument('--phase-bits', type=int, default=1,
                        help='RIS phase quantization bits')
    parser.add_argument('--element-efficiency', type=float, default=0.71,
                        help='RIS element amplitude efficiency (0-1)')
    parser.add_argument('--ris-amplifier-gain', type=float, default=1.0,
                        help='RIS amplifier gain (linear, 1.0 = passive)')
    parser.add_argument('--coherence-loss', type=float, default=0.0,
                        help='Additional coherent gain loss (dB) applied to AF')
    parser.add_argument('--taper-loss', type=float, default=1.0,
                        help='Array taper loss (dB)')
    parser.add_argument('--phase-error-loss', type=float, default=1.0,
                        help='Phase error loss (dB)')
    parser.add_argument('--nearfield-loss', type=float, default=1.0,
                        help='Near-field/nonsphericity loss (dB)')
    parser.add_argument('--reflection-loss', type=float, default=1.5,
                        help='Per-element reflection loss (dB)')
    parser.add_argument('--element-pattern', type=float, default=9.03,
                        help='RIS element pattern gain (dBi)')
    parser.add_argument('--other-losses', type=float, default=0.0,
                        help='Additional miscellaneous RIS losses (dB)')
    parser.add_argument('--noise-rise', type=float, default=0.0,
                        help='Additional noise/interference margin applied to the noise floor (dB)')
    args = parser.parse_args()

    # Position bounds (20m × 20m × 5m space)
    bounds = {
        'ap':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ue':  {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
    }

    # RIS FOV constraint
    ris_max_angle = 60.0

    physics_config = build_config({
        'tx_power_dBm': args.tx_power,
        'ap_antenna_gain_dBi': args.ap_gain,
        'ue_antenna_gain_dBi': args.ue_gain,
        'bandwidth_mhz': args.bandwidth,
        'noise_figure_dB': args.noise_figure,
        'frequency_ghz': args.frequency,
        'ris_elements_per_side': max(1, args.ris_elements),
        'phase_bits': max(0, args.phase_bits),
        'element_efficiency': max(0.0, min(1.0, args.element_efficiency)),
        'ris_amplifier_gain': max(0.0, args.ris_amplifier_gain),
        'coherence_loss_dB': max(0.0, args.coherence_loss),
        'taper_loss_dB': max(0.0, args.taper_loss),
        'phase_error_loss_dB': max(0.0, args.phase_error_loss),
        'nearfield_loss_dB': max(0.0, args.nearfield_loss),
        'reflection_loss_dB': max(0.0, args.reflection_loss),
        'element_pattern_gain_dBi': args.element_pattern,
        'other_loss_dB': max(0.0, args.other_losses),
        'noise_rise_dB': max(0.0, args.noise_rise),
    })

    if args.sampling_mode == 'ris-aware':
        samples_dict, error_count, elapsed_time = build_ris_aware_dataset(
            args, bounds, ris_max_angle, physics_config
        )
    else:
        samples_dict, error_count, elapsed_time = build_stratified_dataset(
            args, bounds, ris_max_angle, physics_config
        )

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
    rate = len(samples_dict) / elapsed_time if elapsed_time > 0 else 0
    print(f"⏱ Total time: {elapsed_time:.2f}s ({rate:.1f} samples/sec)")

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
