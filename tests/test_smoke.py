"""Packaging, CLI, and minimal runtime smoke tests."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

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
            "--topology",
            str(topology),
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

    assert "Sweep Result" in result.stdout
    assert "Top 3 Sweep Measurements" in result.stdout
    assert "Best SNR (dB)" in result.stdout
