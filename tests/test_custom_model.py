#!/usr/bin/env python3
"""Test the custom trained model on the test topology"""

import json
import os
from pathlib import Path
import numpy as np
from core.network import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

# Load example topology
topology_path = Path("examples/json/example_8_sdr_validation.json")
net = RISNetwork()

with open(topology_path, "r") as f:
    data = json.load(f)

if data.get("impairments"):
    net.set_impairments(data["impairments"])

for node in data.get("nodes", []):
    name = node["name"]
    pos = node.get("pos", [0.0, 0.0, 0.0])
    x, y = pos[0], pos[1]
    z = pos[2] if len(pos) > 2 else 0.0
    node_type = node["type"].lower()

    if node_type == "accesspoint":
        net.add_ap(
            name, x, y, z,
            power_dBm=node.get("power_dBm", 20.0),
            freq=node.get("freq", 5.8e9),
            bandwidth_MHz=node.get("bandwidth_MHz", 20.0),
            antenna_gain_dBi=node.get("antenna_gain_dBi", 3.0),
            noise_figure_dB=node.get("noise_figure_dB", 6.0),
        )
    elif node_type == "ris":
        net.add_ris(
            name, x, y, z,
            N=node.get("N", 16),
            bits=node.get("bits", 1),
            freq=node.get("freq", 5.8e9),
            max_angle_deg=node.get("max_angle_deg", 60.0),
            active_mode=node.get("active_mode", False),
            element_efficiency=node.get("element_efficiency", 0.95),
            phase_error_std_deg=node.get("phase_error_std_deg", 8.0),
            amp_std=node.get("amp_std", 0.15),
            coupling_enabled=node.get("coupling_enabled", True),
            K_db=node.get("K_db", 10.0),
            noise_floor=node.get("noise_floor", -90.0),
        )
    elif node_type == "ue":
        net.add_ue(
            name, x, y, z,
            antenna_gain_dBi=node.get("antenna_gain_dBi", 3.0),
            noise_figure_dB=node.get("noise_figure_dB", 6.0),
        )

ap = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "accesspoint"][0]
ris = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "ris"][0]
ue = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "ue"][0]

print("\n" + "="*80)
print("CUSTOM MODEL TEST (10dBm, 1-bit RIS)")
print("="*80)
print(f"Topology: {topology_path}")
print(f"Nodes: AP={ap}, RIS={ris}, UE={ue}")

# Get ground truth
print("\n--- Ground Truth (Full Sweep) ---")
algo = SweepAlgorithmLoader.get_algorithm("linear", net)
result_baseline = algo.sweep(ap, ris, ue, fov=60.0, step=10.0)
best_local = result_baseline['best_local_fine']
best_snr = result_baseline['best_snr_fine']
print(f"Best local angle: {best_local:.2f}°")
print(f"Best SNR: {best_snr:.2f} dB")

# Test custom model directly
print("\n--- Custom Model (trained on 10dBm, 1-bit) ---")
try:
    from controller.beamsweeping.ml.xgb import XGBPredictor

    os.environ['RISNET_XGB_MODEL'] = '/tmp/xgb_beam_predictor_custom_10dbm_1bit.json'
    predictor_custom = XGBPredictor(net)
    angles_custom = predictor_custom.predict_local_angles(ap, ris, ue, fov=60.0, top_k=5)
    print(f"Predictions (top 5): {angles_custom}")

    ris_pos = net.get(ris).pos
    ue_pos = net.get(ue).pos
    base_angle = np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))

    print(f"\nEvaluating predictions:")
    print(f"{'Rank':<5} {'Prediction(°)':<15} {'SNR(dB)':<12} {'Error(°)':<12}")
    print("-" * 50)

    best_ml_snr = -100
    for i, pred_angle in enumerate(angles_custom[:5]):
        link = net.connect(ap, ris, ue, beam_angle_deg=base_angle + pred_angle, seed=0)
        snr = link["snr_dB"]
        error = abs(pred_angle - best_local)
        best_ml_snr = max(best_ml_snr, snr)
        marker = " ← BEST" if error < 1.0 else ""
        print(f"{i+1:<5} {pred_angle:>13.2f} {snr:>10.2f} {error:>10.2f}{marker}")

    error_top = abs(angles_custom[0] - best_local)
    snr_top = net.connect(ap, ris, ue, beam_angle_deg=base_angle + angles_custom[0], seed=0)["snr_dB"]

    print(f"\n--- Summary ---")
    print(f"Top prediction error: {error_top:.2f}°")
    print(f"Top prediction SNR: {snr_top:.2f} dB")
    print(f"Ground truth SNR: {best_snr:.2f} dB")
    print(f"SNR gap: {best_snr - snr_top:.2f} dB")
    print(f"Model trained on domain match: ✓ (10dBm, 1-bit)")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
