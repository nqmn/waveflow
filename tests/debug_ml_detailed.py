#!/usr/bin/env python3
"""Detailed debug script to understand ML model performance vs training data"""

import json
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

# Get nodes
ap = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "accesspoint"][0]
ris = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "ris"][0]
ue = [n["name"] for n in data.get("nodes", []) if n["type"].lower() == "ue"][0]

print("\n" + "="*80)
print("DETAILED ML MODEL ANALYSIS")
print("="*80)
print(f"Topology: {topology_path}")
print(f"Nodes: AP={ap}, RIS={ris}, UE={ue}")

# Get actual node positions to understand geometry
ap_node = net.get(ap)
ris_node = net.get(ris)
ue_node = net.get(ue)

print(f"\nNetwork Geometry:")
print(f"  AP position:  {ap_node.pos}")
print(f"  RIS position: {ris_node.pos}")
print(f"  UE position:  {ue_node.pos}")

ris_to_ue = ue_node.pos - ris_node.pos
specular_angle = np.degrees(np.arctan2(ris_to_ue[1], ris_to_ue[0]))
print(f"  Specular angle (RIS to UE): {specular_angle:.2f}°")

# Test ML predictor
print("\n--- ML Predictor Comparison ---")
predictors = ['default', 'zero']
predictions = {}

for pred_name in predictors:
    try:
        predictor = MLPredictorLoader.get_predictor(pred_name, net)
        print(f"\n{predictor.name}:")
        angles = predictor.predict_local_angles(ap, ris, ue, fov=60.0, top_k=5)
        print(f"  Predictions: {angles}")
        predictions[pred_name] = angles
    except Exception as e:
        print(f"  Error: {e}")
        predictions[pred_name] = None

# Test how each suggestion performs
print("\n--- Evaluating ML Suggestions ---")

fov = 60.0
ris_to_ue = ue_node.pos - ris_node.pos
base_angle = np.degrees(np.arctan2(ris_to_ue[1], ris_to_ue[0]))

for pred_name, angles in predictions.items():
    if not angles:
        print(f"\n{pred_name}: No predictions")
        continue

    print(f"\n{pred_name} ({len(angles)} suggestions):")
    print(f"  {'Idx':<3} {'Local°':<10} {'Absolute°':<12} {'SNR(dB)':<10}")
    print("  " + "-"*40)

    for i, local_angle in enumerate(angles):
        abs_angle = base_angle + local_angle
        try:
            link = net.connect(ap, ris, ue, beam_angle_deg=abs_angle, seed=0)
            snr = link["snr_dB"]
            print(f"  {i:<3} {local_angle:>8.1f} {abs_angle:>11.1f} {snr:>9.2f}")
        except Exception as e:
            print(f"  {i:<3} {local_angle:>8.1f} {abs_angle:>11.1f} Error: {e}")

# Full sweep analysis
print("\n--- Full Linear Sweep (Ground Truth) ---")
algo = SweepAlgorithmLoader.get_algorithm("linear", net)
result = algo.sweep(ap, ris, ue, fov=60.0, step=10.0, ml_angles=None)

# Find where the best angle is
best_idx = int(np.argmax(result['snr_coarse']))
best_local = result['local_coarse'][best_idx]
best_snr = result['best_snr_fine']

print(f"Best local angle: {best_local:.1f}°")
print(f"Best SNR: {best_snr:.2f} dB")

# Analyze where ML prediction was wrong
if predictions.get('default'):
    ml_pred = predictions['default'][0]
    error = abs(ml_pred - best_local)
    print(f"\nML Prediction vs Ground Truth:")
    print(f"  ML predicted: {ml_pred:.1f}°")
    print(f"  Ground truth: {best_local:.1f}°")
    print(f"  Error: {error:.1f}°")

    # Check if this is a domain mismatch issue
    print(f"\n--- Domain Analysis ---")
    print(f"Is this topology in the training domain?")
    print(f"  AP power: {ap_node.power_dBm} dBm (training: typically 20 dBm)")
    print(f"  AP freq: {ap_node.freq/1e9:.1f} GHz (training: typically 5.8 GHz)")
    print(f"  RIS N: {ris_node.N} elements (training: typically 16)")
    print(f"  RIS bits: {ris_node.bits} (training: typically 1-2)")
    print(f"  Spatial extent: {np.linalg.norm(ris_node.pos - ap_node.pos):.1f} m AP-RIS, " +
          f"{np.linalg.norm(ue_node.pos - ris_node.pos):.1f} m RIS-UE")

print("\n" + "="*80)
