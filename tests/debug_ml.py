#!/usr/bin/env python3
"""Debug script to analyze ML predictor behavior"""

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
print("ML PREDICTOR DIAGNOSTIC")
print("="*80)
print(f"Topology: {topology_path}")
print(f"Nodes: AP={ap}, RIS={ris}, UE={ue}")

# Test ML predictor
print("\n--- Testing XGBoost ML Predictor ---")
try:
    predictor = MLPredictorLoader.get_predictor('default', net)
    print(f"Predictor: {predictor.name}")
    print(f"Description: {predictor.description}")

    ml_angles = predictor.predict_local_angles(ap, ris, ue, fov=60.0, top_k=5)
    print(f"ML predictions (top 5): {ml_angles}")
except Exception as e:
    print(f"Error: {e}")
    ml_angles = None

# Now run sweep WITH and WITHOUT ML
print("\n--- Running sweep WITHOUT ML ---")
algo = SweepAlgorithmLoader.get_algorithm("linear", net)
result_no_ml = algo.sweep(ap, ris, ue, fov=60.0, step=10.0, ml_angles=None)

print(f"Best local angle: {result_no_ml['best_local_fine']:.2f}°")
print(f"Best SNR: {result_no_ml['best_snr_fine']:.2f} dB")
print(f"Coarse angles tested: {len([s for s in result_no_ml['snr_coarse'] if not np.isnan(s)])}")
print(f"Fine angles tested: {len(result_no_ml['snr_fine'])}")

if ml_angles:
    print("\n--- Running sweep WITH ML ---")
    algo2 = SweepAlgorithmLoader.get_algorithm("linear", net)
    result_with_ml = algo2.sweep(ap, ris, ue, fov=60.0, step=10.0, ml_angles=ml_angles)

    print(f"Best local angle: {result_with_ml['best_local_fine']:.2f}°")
    print(f"Best SNR: {result_with_ml['best_snr_fine']:.2f} dB")
    print(f"Coarse angles tested: {len([s for s in result_with_ml['snr_coarse'] if not np.isnan(s)])}")
    print(f"Fine angles tested: {len(result_with_ml['snr_fine'])}")

    print("\n--- Comparison ---")
    print(f"SNR difference: {result_with_ml['best_snr_fine'] - result_no_ml['best_snr_fine']:.3f} dB")
    print(f"Measurements saved (coarse): {len([s for s in result_no_ml['snr_coarse'] if not np.isnan(s)]) - len([s for s in result_with_ml['snr_coarse'] if not np.isnan(s)])}")

    # Debug: Check if ML angle was in the best SNR
    best_idx_ml = np.argmax(result_with_ml['snr_coarse'])
    ml_angle_was_best = abs(result_with_ml['local_coarse'][best_idx_ml] - ml_angles[0]) < 0.1
    print(f"ML top suggestion ({ml_angles[0]:.1f}°) was best angle: {ml_angle_was_best}")

print("\n" + "="*80)
