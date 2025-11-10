"""
Example: ML-Assisted Beam Selection on the SDR Validation Topology

This script reuses the coordinates from example_8_sdr_validation.json. It
compares the baseline brute-force sweep against the XGBoost-based beam prior
(`--ml` flag on the CLI) to illustrate how ML hints can narrow down promising
angles before running expensive measurements.

Usage:
    python examples/script/example_ml_beam_prior.py
    python examples/script/example_ml_beam_prior.py --topology path/to/topology.json
    python examples/script/example_ml_beam_prior.py --predictor zero --top-k 2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.network import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader, MLPredictorLoader

DEFAULT_TOPOLOGY = (
    Path(__file__).resolve().parents[1] / "json" / "example_8_sdr_validation.json"
)


def load_topology(path: Path) -> Tuple[RISNetwork, Dict[str, List[str]]]:
    net = RISNetwork()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if data.get("impairments"):
        net.set_impairments(data["impairments"])

    nodes = {"ap": [], "ris": [], "ue": []}

    for node in data.get("nodes", []):
        name = node["name"]
        pos = node.get("pos", [0.0, 0.0, 0.0])
        x, y = pos[0], pos[1]
        z = pos[2] if len(pos) > 2 else 0.0
        node_type = node["type"].lower()

        if node_type == "accesspoint":
            net.add_ap(
                name,
                x,
                y,
                z,
                power_dBm=node.get("power_dBm", 20.0),
                freq=node.get("freq", 5.8e9),
                bandwidth_MHz=node.get("bandwidth_MHz", 20.0),
                antenna_gain_dBi=node.get("antenna_gain_dBi", 3.0),
                noise_figure_dB=node.get("noise_figure_dB", 6.0),
            )
            nodes["ap"].append(name)
        elif node_type == "ris":
            net.add_ris(
                name,
                x,
                y,
                z,
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
            nodes["ris"].append(name)
        elif node_type == "ue":
            net.add_ue(
                name,
                x,
                y,
                z,
                antenna_gain_dBi=node.get("antenna_gain_dBi", 3.0),
                noise_figure_dB=node.get("noise_figure_dB", 6.0),
            )
            nodes["ue"].append(name)

    return net, nodes


def pick(nodes: Dict[str, List[str]], key: str) -> str:
    if not nodes[key]:
        raise RuntimeError(f"No {key.upper()} nodes found in topology")
    return nodes[key][0]


def baseline_sweep(net: RISNetwork, ap: str, ris: str, ue: str) -> Dict:
    algo = SweepAlgorithmLoader.get_algorithm("linear", net)
    result = algo.sweep(ap, ris, ue, fov=60, step=10, enable_feedback=False)
    base_angle = result.get("base_angle", 0.0)
    best_local = result["best_local_fine"]
    result["best_absolute"] = base_angle + best_local
    return result


def evaluate_ml_prior(net: RISNetwork, ap: str, ris: str, ue: str,
                      predictor_name: str, top_k: int) -> List[Dict]:
    predictor = MLPredictorLoader.get_predictor(predictor_name, net)
    fov = 60.0
    suggestions = predictor.predict_local_angles(ap, ris, ue, fov=fov, top_k=top_k)

    ris_pos = net.get(ris).pos
    ue_pos = net.get(ue).pos
    base_angle = np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0]))

    rows: List[Dict] = []
    for local_angle in suggestions:
        abs_angle = base_angle + local_angle
        link = net.connect(ap, ris, ue, beam_angle_deg=abs_angle, seed=0)
        rows.append({
            "local_angle": local_angle,
            "absolute_angle": abs_angle,
            "snr_dB": link["snr_dB"],
            "pwr_dBm": link["pwr_dBm"]
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="Compare baseline sweep vs ML prior")
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY,
                        help="Topology JSON file (defaults to example 8)")
    parser.add_argument("--predictor", type=str, default="default",
                        help="ML predictor key (default = XGBoost prior)")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Number of ML-suggested beams to evaluate")
    args = parser.parse_args()

    net, nodes = load_topology(args.topology)
    ap = pick(nodes, "ap")
    ris = pick(nodes, "ris")
    ue = pick(nodes, "ue")

    print("\n" + "=" * 80)
    print("ML-Assisted Beam Prior Example (Example 8 Coordinates)")
    print("=" * 80)
    print(f"Topology : {args.topology}")
    print(f"Nodes    : AP={ap}, RIS={ris}, UE={ue}")

    baseline = baseline_sweep(net, ap, ris, ue)
    print("\n--- Baseline Linear Sweep (ground truth) ---")
    print(f"Best local angle   : {baseline['best_local_fine']:.2f}°")
    print(f"Best absolute angle: {baseline['best_absolute']:.2f}°")
    print(f"Peak SNR           : {baseline['best_snr_fine']:.2f} dB")

    rows = evaluate_ml_prior(net, ap, ris, ue, args.predictor, args.top_k)
    print(f"\n--- ML Prior ({args.predictor}) Suggestions ---")
    if not rows:
        print("Predictor returned no suggestions.")
        return

    print(f"{'Rank':<5} {'Local(°)':<12} {'Absolute(°)':<14} {'SNR(dB)':<10} {'Power(dBm)':<12}")
    print("-" * 60)
    for idx, row in enumerate(rows, start=1):
        marker = " <-- best" if abs(row['absolute_angle'] - baseline['best_absolute']) < 1e-3 else ""
        print(f"{idx:<5} {row['local_angle']:>10.2f} {row['absolute_angle']:>12.2f} "
              f"{row['snr_dB']:>9.2f} {row['pwr_dBm']:>11.2f}{marker}")

    best_ml = max(rows, key=lambda r: r['snr_dB'])
    snr_gap = baseline['best_snr_fine'] - best_ml['snr_dB']
    angle_error = abs(baseline['best_absolute'] - best_ml['absolute_angle'])
    print("\n--- Comparison ---")
    print(f"Best ML suggestion : local {best_ml['local_angle']:.2f}°, "
          f"absolute {best_ml['absolute_angle']:.2f}°")
    print(f"SNR difference     : {snr_gap:.2f} dB vs full sweep")
    print(f"Angle error        : {angle_error:.2f}°")


if __name__ == "__main__":
    main()
