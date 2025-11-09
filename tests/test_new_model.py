#!/usr/bin/env python3
"""Test the newly trained model vs the old one"""

import json
import os
from pathlib import Path
import numpy as np
from core.network import RISNetwork
from controller.beamsweeping import MLPredictorLoader, SweepAlgorithmLoader

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
print("MODEL COMPARISON: OLD vs NEW")
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

# Test old model
print("\n--- OLD Model (original pre-trained) ---")
try:
    predictor_old = MLPredictorLoader.get_predictor('default', net)
    angles_old = predictor_old.predict_local_angles(ap, ris, ue, fov=60.0, top_k=3)
    print(f"Predictions: {angles_old}")

    ris_pos = net.get(ris).pos
    ue_pos = net.get(ue).pos
    base_angle = np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))

    link_old = net.connect(ap, ris, ue, beam_angle_deg=base_angle + angles_old[0], seed=0)
    snr_old = link_old["snr_dB"]
    error_old = abs(angles_old[0] - best_local)

    print(f"Top prediction: {angles_old[0]:.2f}°")
    print(f"SNR at prediction: {snr_old:.2f} dB")
    print(f"Error vs ground truth: {error_old:.2f}°")
except Exception as e:
    print(f"Error: {e}")
    angles_old = None
    snr_old = None
    error_old = None

# Test new model
print("\n--- NEW Model (freshly trained) ---")
try:
    # Use environment variable to override model path
    os.environ['RISNET_XGB_MODEL'] = '/tmp/xgb_beam_predictor_new.json'

    # Need to recreate predictor to pick up environment variable
    from controller.beamsweeping.ml import XGBPredictor
    predictor_new = XGBPredictor(net)
    angles_new = predictor_new.predict_local_angles(ap, ris, ue, fov=60.0, top_k=3)
    print(f"Predictions: {angles_new}")

    link_new = net.connect(ap, ris, ue, beam_angle_deg=base_angle + angles_new[0], seed=0)
    snr_new = link_new["snr_dB"]
    error_new = abs(angles_new[0] - best_local)

    print(f"Top prediction: {angles_new[0]:.2f}°")
    print(f"SNR at prediction: {snr_new:.2f} dB")
    print(f"Error vs ground truth: {error_new:.2f}°")
except Exception as e:
    print(f"Error: {e}")
    angles_new = None
    snr_new = None
    error_new = None

# Comparison
if angles_old and angles_new:
    print("\n--- Comparison ---")
    print(f"{'Metric':<30} {'OLD':<15} {'NEW':<15} {'Improvement':<15}")
    print("-" * 75)
    print(f"{'Top Prediction (°)':<30} {angles_old[0]:>13.2f} {angles_new[0]:>13.2f} "
          f"{error_old - error_new:>13.2f}°")
    print(f"{'SNR at Prediction (dB)':<30} {snr_old:>13.2f} {snr_new:>13.2f} "
          f"{snr_new - snr_old:>13.2f} dB")
    print(f"{'Prediction Error (°)':<30} {error_old:>13.2f} {error_new:>13.2f} "
          f"{error_old - error_new:>13.2f}°")

print("\n" + "="*80)
