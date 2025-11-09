#!/usr/bin/env python3
"""Generate training data matching example_8_sdr_validation.json parameters"""

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
    # Parameters matching example_8_sdr_validation.json
    # AP: 10 dBm, 5.8 GHz
    # RIS: 16 elements, 1 bit
    random.seed(42)
    np.random.seed(42)

    bounds = {
        'fov': 60.0,
        'step': 10.0,
        'ap': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ris': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
        'ue': {'x_min': 0, 'x_max': 20, 'y_min': 0, 'y_max': 20, 'z_min': 0, 'z_max': 5},
    }

    # Match example_8_sdr_validation.json
    ap_cfg = {'power_dBm': 10.0, 'freq': 5.8e9}  # 10 dBm instead of 20 dBm
    ris_cfg = {'N': 16, 'bits': 1}                # 1 bit instead of 2 bits
    ue_cfg = {}

    net = RISNetwork()

    samples: List[Dict[str, Any]] = []
    print("Generating 1000 training samples with parameters:")
    print(f"  AP Power: {ap_cfg['power_dBm']} dBm")
    print(f"  RIS Elements: {ris_cfg['N']}")
    print(f"  RIS Phase Bits: {ris_cfg['bits']}")
    print()

    for i in range(1000):
        if (i + 1) % 100 == 0:
            print(f"  Generated {i + 1}/1000 samples...")
        try:
            sample = build_sample(net, bounds, ap_cfg, ris_cfg, ue_cfg)
            samples.append(sample)
        except Exception as exc:
            print(f"Skipping sample {i} due to error: {exc}")

    output_path = Path('/tmp/beam_dataset_custom_10dbm_1bit.json')
    output_path.write_text(json.dumps(samples, indent=2))
    print(f"\nWrote {len(samples)} samples to {output_path}")


if __name__ == "__main__":
    main()
