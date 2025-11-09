#!/usr/bin/env python3
"""Comprehensive evaluation of model performance on diverse topologies"""

import json
import os
import random
from pathlib import Path
import numpy as np
from core.network import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

def test_topology(net_config, predictor_fn, num_tests=10):
    """Test a model on random topologies with given configuration"""
    errors = []
    snr_gaps = []

    random.seed(42)
    np.random.seed(42)

    for test_num in range(num_tests):
        try:
            # Create random topology
            net = RISNetwork()

            ap_pos = np.array([
                random.uniform(0, 20),
                random.uniform(0, 20),
                random.uniform(0, 5)
            ])
            ris_pos = np.array([
                random.uniform(0, 20),
                random.uniform(0, 20),
                random.uniform(0, 5)
            ])
            ue_pos = np.array([
                random.uniform(0, 20),
                random.uniform(0, 20),
                random.uniform(0, 5)
            ])

            net_config_copy = net_config.copy()
            ap_power = net_config_copy.pop('ap_power')
            ris_bits = net_config_copy.pop('ris_bits')

            net.add_ap('AP', *ap_pos, power_dBm=ap_power, freq=5.8e9)
            net.add_ris('RIS', *ris_pos, N=16, bits=ris_bits, freq=5.8e9)
            net.add_ue('UE', *ue_pos)

            # Ground truth
            algo = SweepAlgorithmLoader.get_algorithm("linear", net)
            result = algo.sweep('AP', 'RIS', 'UE', fov=60.0, step=10.0)
            best_local = result['best_local_fine']
            best_snr = result['best_snr_fine']

            # Get ML prediction
            pred = predictor_fn(net)
            if not pred or len(pred) == 0:
                continue

            # Evaluate
            ris_to_ue = ue_pos - ris_pos
            base_angle = np.degrees(np.arctan2(ris_to_ue[1], ris_to_ue[0]))
            link = net.connect('AP', 'RIS', 'UE', beam_angle_deg=base_angle + pred[0], seed=0)
            ml_snr = link["snr_dB"]

            error = abs(pred[0] - best_local)
            snr_gap = best_snr - ml_snr

            errors.append(error)
            snr_gaps.append(snr_gap)

        except Exception as e:
            pass

    return errors, snr_gaps


print("\n" + "="*80)
print("MODEL PERFORMANCE EVALUATION")
print("="*80)

# Test configs
configs = [
    {"name": "10dBm, 1-bit", "ap_power": 10.0, "ris_bits": 1},
    {"name": "20dBm, 2-bit", "ap_power": 20.0, "ris_bits": 2},
    {"name": "10dBm, 2-bit", "ap_power": 10.0, "ris_bits": 2},
    {"name": "20dBm, 1-bit", "ap_power": 20.0, "ris_bits": 1},
]

models = {
    "Default (20dBm, 2-bit)": None,  # Will use default model
    "Generic (1000 random)": '/tmp/xgb_beam_predictor_new.json',
    "Custom (10dBm, 1-bit)": '/tmp/xgb_beam_predictor_custom_10dbm_1bit.json',
}

results_table = []

for config in configs:
    print(f"\n--- Testing on {config['name']} Topologies ---")

    for model_name, model_path in models.items():
        def predictor_fn(net):
            from controller.beamsweeping.ml.xgb import XGBPredictor
            if model_path:
                os.environ['RISNET_XGB_MODEL'] = model_path
            predictor = XGBPredictor(net)
            return predictor.predict_local_angles('AP', 'RIS', 'UE', fov=60.0, top_k=1)

        errors, snr_gaps = test_topology(config, predictor_fn, num_tests=10)

        if errors:
            avg_error = np.mean(errors)
            avg_snr_gap = np.mean(snr_gaps)
            print(f"  {model_name:<30} Error: {avg_error:>6.2f}° | SNR Gap: {avg_snr_gap:>6.3f} dB")
            results_table.append({
                'config': config['name'],
                'model': model_name,
                'error': avg_error,
                'snr_gap': avg_snr_gap
            })

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)

# Find best model for each config
for config in configs:
    config_results = [r for r in results_table if r['config'] == config['name']]
    if config_results:
        best = min(config_results, key=lambda x: x['error'])
        print(f"{config['name']:<15} → Use: {best['model']:<30} (error: {best['error']:.2f}°)")

print("\n" + "="*80)
