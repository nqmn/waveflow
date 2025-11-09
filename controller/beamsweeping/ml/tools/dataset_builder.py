"""Generate training data for beam-prediction models."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from core import RISNetwork


def random_position(bounds: Dict[str, float]) -> np.ndarray:
    return np.array([
        random.uniform(bounds['x_min'], bounds['x_max']),
        random.uniform(bounds['y_min'], bounds['y_max']),
        random.uniform(bounds['z_min'], bounds['z_max'])
    ])


def build_sample(net: RISNetwork, bounds, ap_cfg, ris_cfg, ue_cfg):
    net.nodes.clear()

    ap_pos = random_position(bounds['ap'])
    ris_pos = random_position(bounds['ris'])
    ue_pos = random_position(bounds['ue'])

    net.add_ap('AP', *ap_pos, power_dBm=ap_cfg['power_dBm'], freq=ap_cfg['freq'])
    net.add_ris(
        'RIS', *ris_pos,
        N=ris_cfg['N'], bits=ris_cfg['bits']
    )
    net.add_ue('UE', *ue_pos)

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
        'best_angle': best_angle,
        'best_snr': snr
    }
    return sample


def main():
    parser = argparse.ArgumentParser(description="Generate training data for beam ML models")
    parser.add_argument('--samples', type=int, default=1000, help='Number of random topologies')
    parser.add_argument('--output', type=Path, default=Path('beam_dataset.json'), help='Output JSON file')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    bounds = {
        'fov': 60.0,
        'step': 10.0,
        'ap': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ue': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
    }

    ap_cfg = {'power_dBm': 20.0, 'freq': 5.8e9}
    ris_cfg = {'N': 16, 'bits': 2}
    ue_cfg = {}

    net = RISNetwork()

    samples: List[Dict[str, Any]] = []
    for _ in range(args.samples):
        try:
            sample = build_sample(net, bounds, ap_cfg, ris_cfg, ue_cfg)
            samples.append(sample)
        except Exception as exc:
            print(f"Skipping sample due to error: {exc}")

    args.output.write_text(json.dumps(samples, indent=2))
    print(f"Wrote {len(samples)} samples to {args.output}")


if __name__ == "__main__":
    main()
