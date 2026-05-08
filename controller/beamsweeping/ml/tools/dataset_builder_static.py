"""
Generate training data for beam-prediction models using FIXED AP and RIS positions.

Only varies UE position across the dataset while keeping AP and RIS constant.
This focuses the model on learning: given fixed source (AP) and relay (RIS),
how does UE position determine the required beam deflection angle?

FORMULA (from risformula/formula.md):
======================================
Deflection angle (pure geometric):
  θ_rcv = |atan2(UE_y - RIS_y, UE_x - RIS_x) - atan2(AP_y - RIS_y, AP_x - RIS_x)|

This is the steering angle the RIS must apply to redirect from AP incident
direction to UE target direction (2D azimuth only).

DATASET CONSTRAINT:
- Only include geometries where: θ_rcv ≤ 60° (RIS FOV capability)
- Training labels (best_angle) = θ_rcv (the actual deflection angle)
- Fixed AP and RIS positions for all samples
- Vary only UE position
- Pure geometric sampling with strict feasibility
"""

import argparse
import csv
import math
import os
import random
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.lightris import build_lightris_config, evaluate_lightris_metrics


# ============================================================================
# CONFIGURABLE PARAMETERS - Easy to change
# ============================================================================

# Fixed AP position [x, y, z] in meters
AP_POSITION = np.array([8.0, 10.0, 0.5], dtype=float)

# Fixed RIS position [x, y, z] in meters
RIS_POSITION = np.array([15.0, 10.0, 0.0], dtype=float)

# ============================================================================


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


def build_sample(ue_pos: np.ndarray, ap_pos: np.ndarray, ris_pos: np.ndarray,
                physics_config: Dict) -> Dict:
    """
    Build a single training sample with fixed AP/RIS and given UE position.

    Args:
        ue_pos: UE position [x, y, z]
        ap_pos: AP position [x, y, z]
        ris_pos: RIS position [x, y, z]
        physics_config: Physics configuration dict

    Returns:
        Sample dict with positions, distances, angles, and best_angle
    """
    # Compute derived features
    d_ap_ris, d_ris_ue = compute_distances(ap_pos, ris_pos, ue_pos)
    aoa, aod = compute_angles(ap_pos, ris_pos, ue_pos)
    theta_rcv = compute_theta_rcv(ap_pos, ris_pos, ue_pos)

    # Keep the continuous deflection angle as the label
    best_angle = float(theta_rcv)

    sample = {
        'ap_pos': ap_pos.tolist(),
        'ris_pos': ris_pos.tolist(),
        'ue_pos': ue_pos.tolist(),
        'd_ap_ris': d_ap_ris,
        'd_ris_ue': d_ris_ue,
        'aoa': aoa,
        'aod': aod,
        'best_angle': best_angle
    }
    _add_angle_trigs(sample, aoa, aod)
    _add_ap_ris_orientation(sample)
    _add_physics_metrics(sample, physics_config)
    return sample


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


def _add_physics_metrics(sample: Dict, physics_config: Dict) -> None:
    """Annotate the sample with SNR and RSSI using a shared RIS budget."""
    ap_pos = np.array(sample['ap_pos'], dtype=float)
    ris_pos = np.array(sample['ris_pos'], dtype=float)
    ue_pos = np.array(sample['ue_pos'], dtype=float)
    beam_angle = float(sample['aod'])

    metrics = evaluate_lightris_metrics(
        ap_pos=ap_pos,
        ris_pos=ris_pos,
        ue_pos=ue_pos,
        beam_angle_deg=beam_angle,
        physics_config=physics_config
    )

    sample['snr_dB'] = float(metrics['snr_dB'])
    sample['rssi_dBm'] = float(metrics['rssi_dBm'])


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


def generate_static_dataset(num_samples: int, ue_bounds: Dict,
                           ris_max_angle: float, seed: int,
                           ap_pos: np.ndarray, ris_pos: np.ndarray,
                           physics_config: Dict) -> Dict[int, Dict]:
    """
    Generate dataset with fixed AP/RIS and varying UE positions.

    Args:
        num_samples: Number of samples to generate
        ue_bounds: UE position bounds
        ris_max_angle: Maximum RIS steering angle (degrees)
        seed: Random seed
        ap_pos: Fixed AP position
        ris_pos: Fixed RIS position
        physics_config: Physics configuration

    Returns:
        Dictionary of samples indexed by sample ID
    """
    rng = random.Random(seed)
    samples = {}
    max_attempts = num_samples * 20

    attempts = 0
    while len(samples) < num_samples and attempts < max_attempts:
        ue_pos = random_position(ue_bounds)
        theta_rcv = compute_theta_rcv(ap_pos, ris_pos, ue_pos)

        if theta_rcv <= ris_max_angle:
            sample = build_sample(ue_pos, ap_pos, ris_pos, physics_config)
            samples[len(samples)] = sample
        attempts += 1

    return samples


def main():
    parser = argparse.ArgumentParser(
        description="Generate beam dataset with FIXED AP and RIS positions (varying UE)"
    )
    parser.add_argument('--samples', type=int, default=5000,
                       help='Number of samples to generate')
    parser.add_argument('--output', type=Path,
                       default=Path('controller/beamsweeping/ml/data/beam_dataset_static.csv'),
                       help='Output CSV file')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed')
    parser.add_argument('--verbose', action='store_true',
                       help='Show progress when generating large datasets')

    # UE bounds
    parser.add_argument('--ue-x-min', type=float, default=0.0,
                       help='UE X minimum (meters)')
    parser.add_argument('--ue-x-max', type=float, default=20.0,
                       help='UE X maximum (meters)')
    parser.add_argument('--ue-y-min', type=float, default=0.0,
                       help='UE Y minimum (meters)')
    parser.add_argument('--ue-y-max', type=float, default=20.0,
                       help='UE Y maximum (meters)')
    parser.add_argument('--ue-z-min', type=float, default=0.0,
                       help='UE Z minimum (meters)')
    parser.add_argument('--ue-z-max', type=float, default=5.0,
                       help='UE Z maximum (meters)')

    # Physics parameters
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
                       help='Additional noise/interference margin applied to noise floor (dB)')

    args = parser.parse_args()

    # UE bounds (variable)
    ue_bounds = {
        'x_min': args.ue_x_min,
        'x_max': args.ue_x_max,
        'y_min': args.ue_y_min,
        'y_max': args.ue_y_max,
        'z_min': args.ue_z_min,
        'z_max': args.ue_z_max,
    }

    # RIS FOV constraint
    ris_max_angle = 60.0

    physics_config = build_lightris_config({
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

    print(f"Generating {args.samples} samples with FIXED AP/RIS...")
    print(f"  AP position: ({AP_POSITION[0]:.1f}, {AP_POSITION[1]:.1f}, {AP_POSITION[2]:.1f})")
    print(f"  RIS position: ({RIS_POSITION[0]:.1f}, {RIS_POSITION[1]:.1f}, {RIS_POSITION[2]:.1f})")
    print(f"  UE bounds: X[{ue_bounds['x_min']:.1f}, {ue_bounds['x_max']:.1f}], "
          f"Y[{ue_bounds['y_min']:.1f}, {ue_bounds['y_max']:.1f}], "
          f"Z[{ue_bounds['z_min']:.1f}, {ue_bounds['z_max']:.1f}]")

    samples_dict = generate_static_dataset(
        args.samples,
        ue_bounds,
        ris_max_angle,
        args.seed,
        AP_POSITION,
        RIS_POSITION,
        physics_config
    )

    if len(samples_dict) < args.samples:
        print(f"Warning: Generated {len(samples_dict)} samples (requested {args.samples}). "
              f"Consider expanding UE bounds or reducing RIS FOV constraint.")

    # Write to CSV
    args.output.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(samples_dict)} samples to {args.output}...")

    with args.output.open('w', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        for idx in sorted(samples_dict.keys()):
            writer.writerow(flatten_sample(samples_dict[idx]))

    print(f"Wrote {len(samples_dict)} samples to {args.output}")

    # Statistics
    if samples_dict:
        angles = [s['best_angle'] for s in samples_dict.values()]
        print(f"\nDataset statistics:")
        print(f"  Min angle: {min(angles):.2f} degrees")
        print(f"  Max angle: {max(angles):.2f} degrees")
        print(f"  Mean angle: {np.mean(angles):.2f} degrees")
        print(f"  Median angle: {np.median(angles):.2f} degrees")
        print(f"  All angles <= 60 degrees: {all(a <= 60.0 for a in angles)}")


if __name__ == "__main__":
    main()
