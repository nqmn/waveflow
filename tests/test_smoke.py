"""Packaging, CLI, and minimal runtime smoke tests."""

import os
import subprocess
import sys

from core import RISNetwork
from risnet import RISnet


def test_imports_from_installed_package():
    assert RISNetwork is not None
    assert RISnet is not None


def test_minimal_connect_smoke():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 5, 0, max_angle_deg=180)
    net.add_ue("ue1", 10, 0)

    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    assert "snr_dB" in result
    assert "pwr_dBm" in result
    assert result["ue_present"] is True


def test_module_help_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "--help"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "RISNet v2.0 Advanced RIS Network Simulator" in result.stdout


def test_console_help_from_outside_repo():
    bin_dir = os.path.dirname(sys.executable)
    risnet_executable = os.path.join(bin_dir, "risnet")

    result = subprocess.run(
        [risnet_executable, "help", "--exec-only"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Available commands:" in result.stdout
