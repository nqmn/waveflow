"""Packaging, CLI, and minimal runtime smoke tests."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from cli.connection_handler import ConnectionHandler
from cli.main_shell import RISNetCLI
from core import RISNetwork
from risnet import RISnet
from waveflow import RISnet as WaveflowRISnet


def test_imports_from_installed_package():
    assert RISNetwork is not None
    assert RISnet is not None
    assert WaveflowRISnet is RISnet


def test_minimal_connect_smoke():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 5, 0, max_angle_deg=180)
    net.add_ue("ue1", 10, 0)

    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    assert "snr_dB" in result
    assert "pwr_dBm" in result
    assert result["ue_present"] is True


def test_hog_example_module_imports_with_current_public_apis():
    example_path = Path(__file__).resolve().parents[1] / "examples" / "script" / "example_19_hog_human_detection.py"
    spec = importlib.util.spec_from_file_location("example_19_hog_human_detection", example_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    network = module.build_demo_network()

    assert network.get("AP1") is not None
    assert network.get("RIS1") is not None
    assert network.get("UE1") is not None


def test_module_help_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "waveflow", "--help"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Waveflow v2.0 Advanced Wireless and RIS Simulator" in result.stdout


def test_legacy_module_help_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "--help"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Waveflow v2.0 Advanced Wireless and RIS Simulator" in result.stdout


def test_console_help_from_outside_repo():
    import shutil
    risnet_executable = shutil.which("waveflow")
    if risnet_executable is None:
        import pytest
        pytest.skip("waveflow not found on PATH — run pip install -e .")

    result = subprocess.run(
        [risnet_executable, "help", "--exec-only"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Available commands:" in result.stdout


def test_typer_rich_status_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "--terminal", "status"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Waveflow Terminal" in result.stdout
    assert "Nodes" in result.stdout


def test_typer_rich_demo_connect_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "demo-connect", "--seed", "42"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Link Metrics" in result.stdout
    assert "snr_dB" in result.stdout


def test_typer_rich_add_random_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "add", "random"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added random topology" in result.stdout
    assert "Waveflow Terminal" in result.stdout
    assert "AP1" in result.stdout
    assert "R1" in result.stdout
    assert "UE1" in result.stdout


def test_typer_rich_connect_from_outside_repo_uses_topology():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "connect",
            "AP1",
            "R1",
            "UE1",
            "--topology",
            "examples/json/example_1_simple.json",
            "--seed",
            "42",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Link Result" in result.stdout
    assert "snr_dB" in result.stdout


def test_typer_rich_sweep_table_from_outside_repo():
    topology = Path("/tmp/waveflow_sweep_smoke_topology.json")
    topology.write_text(
        json.dumps(
            {
                "name": "Sweep Smoke Topology",
                "nodes": [
                    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
                    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 2, "max_angle_deg": 90.0},
                    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "sweep",
            "AP1",
            "R1",
            "UE1",
            "--algo",
            "linear",
            "--topology",
            str(topology),
            "--live",
            "--format",
            "table",
            "--topk",
            "3",
        ],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Live Sweep" in result.stdout
    assert "Sweep Result" in result.stdout
    assert "Top 3 Sweep Measurements" in result.stdout
    assert "Best SNR (dB)" in result.stdout


def test_example_1_simple_topology_supports_terminal_sweep():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "sweep",
            "AP1",
            "R1",
            "UE1",
            "--topology",
            "examples/json/example_1_simple.json",
            "--algo",
            "linear",
            "--no-live",
            "--format",
            "table",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Sweep Result" in result.stdout
    assert "Best SNR (dB)" in result.stdout


def test_typer_rich_run_passes_through_legacy_breakdown_flags():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "run",
            "--topology",
            "examples/json/example_1_simple.json",
            "signal",
            "AP1",
            "R1",
            "UE1",
            "--breakdown",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "AP→RIS" in result.stdout
    assert "RIS→UE" in result.stdout


def test_ris_aware_ue_falls_back_when_ap_is_unreachable(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 6.52, 8.86, 0.0)
    net.add_ris("ris1", 13.10, 10.42, 0.0, 16, 1)

    cli = RISNetCLI(net)
    cli.topology_helper.generate_position = lambda typ: (21.0, 22.0)

    x, y, used_ris_aware = cli._add_ue_within_ris_fov("ue1", distance=14.32)

    assert (x, y) == (21.0, 22.0)
    assert used_ris_aware is False


def test_connection_handler_accepts_de_style_numpy_measurements():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0.0, 0.0, 0.0)
    net.add_ris("ris1", 5.0, 2.0, 0.0, 16, 1)
    net.add_ue("ue1", 8.0, 8.0, 0.0)

    handler = ConnectionHandler(net)
    printed = []
    collector = lambda *parts: printed.append("" if not parts else " ".join(str(part) for part in parts))
    result = handler.print_sweep_results(
        {
            "local_coarse": [179.6],
            "snr_coarse": [-21.51],
            "local_fine": [],
            "snr_fine": [],
            "best_angle": 179.6,
            "best_snr_fine": -21.51,
            "beam_angle_deg": 179.6,
            "measurements": __import__("numpy").array([1 + 1j, 2 + 0j]),
            "estimated_position": __import__("numpy").array([7.5, 7.0, 0.0]),
        },
        fov=60.0,
        step=10.0,
        ap="ap1",
        ris="ris1",
        ue="ue1",
        algo_name="de",
        print_func=collector,
    )

    assert result["best_final_local"] == 179.6
    assert any("SINGLE-PHASE SWEEP" in line for line in printed)


def test_typer_rich_sweep_invalid_nodes_fails_before_live_ui():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "sweep", "ap", "ris", "ue"],
        cwd="/tmp",
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Sweep failed:" in result.stdout
    assert "Invalid node name in sweep: ap, ris, ue" in result.stdout
    assert "Live Sweep" not in result.stdout
