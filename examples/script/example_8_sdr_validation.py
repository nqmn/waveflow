"""
Example 8: SDR-Validated Topology Replay

Loads the 5.8 GHz HackRF-inspired JSON topology, applies the saved
impairments (antenna gains, noise figures, extra indoor loss), and
runs the same analyses we executed manually via the CLI. Random fading
is still enabled, so expect minor run-to-run variations.

Manual RISNet CLI steps (equivalent to this script):
    # Start the interactive shell with the calibrated topology loaded
    risnet --topology examples/json/example_8_sdr_validation.json

    # Inside the RISNet prompt, run:
    list
    waveform_validate
    connect AP_TX RIS_PANEL UE_RX 45 0    # optional: seed=0 for reproducible SNR
    waveform_compare AP_TX RIS_PANEL UE_RX

Script Usage:
    python examples/script/example_8_sdr_validation.py
    python examples/script/example_8_sdr_validation.py --topology my_topology.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.network import RISNetwork
from core.validation import WaveformValidator
from controller.waveform_controller import WaveformController
from core.physics import Physics


DEFAULT_TOPOLOGY = (
    Path(__file__).resolve().parents[1] / "json" / "example_8_sdr_validation.json"
)


def build_network_from_json(path: Path) -> Tuple[RISNetwork, Dict[str, List[str]], Dict]:
    """Create RISNetwork instance from a topology JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    net = RISNetwork()
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
                amplifier_gain=node.get("amplifier_gain", 1.0),
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

    return net, nodes, data


def pick_first(nodes: Dict[str, List[str]], key: str) -> str:
    if not nodes[key]:
        raise RuntimeError(f"Topology is missing a {key.upper()} node.")
    return nodes[key][0]


def run(topology: Path) -> None:
    net, nodes, data = build_network_from_json(topology)
    ap_name = pick_first(nodes, "ap")
    ris_name = pick_first(nodes, "ris")
    ue_name = pick_first(nodes, "ue")

    print("\n" + "=" * 80)
    print("Example 8: SDR Validation Replay")
    print("=" * 80)
    print(f"Topology file : {topology}")
    print(f"Description   : {data.get('description', 'N/A')}")
    if data.get("metadata"):
        print(f"Source        : {data['metadata'].get('source', 'n/a')}")
    if data.get("impairments"):
        print("Global impairments:")
        for key, value in data["impairments"].items():
            print(f"  - {key}: {value}")

    print("\nLoaded nodes:")
    for name, node in net.nodes.items():
        print(f"  {name:<12} → {type(node).__name__} @ {node.pos.tolist()}")

    # 1) Topology + physics validation
    print("\n--- Validation ---")
    validator = WaveformValidator(net)
    topo_result = validator.validate_topology()
    print(f"Valid topology: {topo_result['valid']} "
          f"(APs={topo_result['num_aps']}, RIS={topo_result['num_ris']}, UEs={topo_result['num_ues']})")
    physics = validator.validate_basic_physics(ap_name, ris_name, ue_name)
    print(f"Physics valid : {physics['physics_valid']}")
    print(f"Distances     : AP→RIS={physics['distances']['ap_to_ris_m']:.2f} m, "
          f"RIS→UE={physics['distances']['ris_to_ue_m']:.2f} m")

    # 2) Connect budget
    print("\n--- AP→RIS→UE Connect ---")
    link = net.connect(ap_name, ris_name, ue_name, seed=0)
    print(f"Beam angle    : {link['beam_angle']:.2f}°")
    print(f"SNR           : {link['snr_dB']:.2f} dB")
    print(f"Rx power      : {link['pwr_dBm']:.2f} dBm")
    print(f"RIS gain      : {link['gain_dBi']:.2f} dBi")
    print(f"Quant loss    : {link['quant_loss_dB']:.2f} dB")

    # Direct (RIS-off) reference for comparison with the paper
    print("\n--- Direct vs RIS (System Level) ---")
    impairments = data.get("impairments", {}) or {}
    direct = net.direct_link(ap_name, ue_name)
    direct_evm = Physics.snr_to_evm(direct["snr_dB"])
    ris_evm = Physics.snr_to_evm(link["snr_dB"])
    snr_gain = link["snr_dB"] - direct["snr_dB"]

    reported = (data.get("metadata") or {}).get("reported_metrics")
    rssi_direct = direct['rx_power_dBm']
    rssi_ris = link['pwr_dBm']

    print(f"Direct path   : SNR={direct['snr_dB']:.2f} dB, "
          f"RSSI={rssi_direct:.2f} dBm, "
          f"EVM≈{direct_evm:.2f}%")
    print(f"RIS assisted  : SNR={link['snr_dB']:.2f} dB, "
          f"RSSI={rssi_ris:.2f} dBm, "
          f"EVM≈{ris_evm:.2f}%")
    print(f"Improvements  : ΔSNR={snr_gain:.2f} dB, "
          f"ΔRSSI={rssi_ris - rssi_direct:.2f} dB, "
          f"EVM ratio≈{direct_evm/ris_evm if ris_evm else float('inf'):.2f}×")

    if reported:
        print("\n--- Reported (Paper) Metrics ---")
        direct_rep = reported.get("direct", {})
        ris_rep = reported.get("ris", {})
        print(f"Direct (paper): SNR={direct_rep.get('snr_dB', 'n/a')} dB, "
              f"RSSI={direct_rep.get('rssi_dBm', 'n/a')} dBm, "
              f"EVM≈{direct_rep.get('evm_percent', 'n/a')}%")
        print(f"RIS (paper)   : SNR={ris_rep.get('snr_dB', 'n/a')} dB, "
              f"RSSI={ris_rep.get('rssi_dBm', 'n/a')} dBm, "
              f"EVM≈{ris_rep.get('evm_percent', 'n/a')}%")
        if {'snr_dB', 'rssi_dBm'} <= direct_rep.keys() and {'snr_dB', 'rssi_dBm'} <= ris_rep.keys():
            print(f"Paper ΔSNR    : {ris_rep['snr_dB'] - direct_rep['snr_dB']:.2f} dB "
                  f"(ΔRSSI {ris_rep['rssi_dBm'] - direct_rep['rssi_dBm']:.2f} dB)")

    # 3) System vs waveform comparison
    print("\n--- System vs Waveform ---")
    waveform_ctrl = WaveformController(net, net.environment)
    comparison = waveform_ctrl.compare_system_vs_waveform(ap_name, ris_name, ue_name)
    print(f"System SNR    : {comparison['system_level']['snr_dB']:.2f} dB")
    print(f"Waveform SNR  : {comparison['waveform_level']['snr_dB']:.2f} dB")
    print(f"Effective SNR : {comparison['waveform_level']['snr_effective_dB']:.2f} dB")
    print(f"Waveform Δ    : {comparison['difference']['snr_diff_dB']:.2f} dB "
          f"(penalty {comparison['difference']['waveform_penalty_dB']:.2f} dB)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay SDR validation topology analytics.")
    parser.add_argument(
        "--topology",
        type=Path,
        default=DEFAULT_TOPOLOGY,
        help="Path to topology JSON file (default: example_8_sdr_validation.json).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.topology)
