"""Packaging, CLI, and minimal runtime smoke tests."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from cli.connection_handler import ConnectionHandler
from cli.helpers import NetworkIO
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


def test_bare_ui_opens_native_interactive_shell_and_accepts_commands():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui"],
        cwd="/home/user/project/risnet",
        input="status\nquit\n",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Opening Waveflow UI shell." in result.stdout
    assert "waveflow ui>" in result.stdout.lower()


def test_native_ui_shell_keeps_state_and_supports_legacy_passthrough():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "shell"],
        cwd="/home/user/project/risnet",
        input=(
            "load examples/json/example_1_simple.json\n"
            "add ue UE2 --x 11 --y 4\n"
            "status\n"
            "signal AP1 R1 UE1 --breakdown\n"
            "quit\n"
        ),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Loaded" in result.stdout
    assert "Added UE" in result.stdout
    assert "Nodes         4" in result.stdout
    assert "AP→RIS" in result.stdout
    assert "RIS→UE" in result.stdout


def test_native_ui_shell_connect_without_args_uses_native_renderer():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "shell"],
        cwd="/home/user/project/risnet",
        input=(
            "load examples/json/example_1_simple.json\n"
            "connect\n"
            "quit\n"
        ),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Connect Diagnostics" in result.stdout
    assert "Link Result" in result.stdout
    assert "RIS Recommendation" in result.stdout
    assert "snr_dB" in result.stdout
    assert "Missing argument 'AP'" not in result.stdout


def test_typer_rich_status_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "--terminal", "status"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Network Status" in result.stdout
    assert "No nodes in network" in result.stdout
    assert "Active Links" in result.stdout


def test_typer_rich_env_wrapper_uses_topology():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "env",
            "--topology",
            "examples/json/example_1_simple.json",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Env Output" in result.stdout
    assert "Environment:" in result.stdout
    assert "Bounds:" in result.stdout


def test_typer_rich_node_wrappers_show_details():
    ap_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "ap",
            "--topology",
            "examples/json/example_1_simple.json",
            "AP1",
            "show",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )
    ris_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "ris",
            "--topology",
            "examples/json/example_1_simple.json",
            "R1",
            "show",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )
    ue_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "ue",
            "--topology",
            "examples/json/example_1_simple.json",
            "UE1",
            "show",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "AP1 (Access Point)" in ap_result.stdout
    assert "R1 (RIS)" in ris_result.stdout
    assert "UE1 (UE)" in ue_result.stdout


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


def test_typer_rich_demo_connect_accepts_official_simris_engine():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "demo-connect",
            "--seed",
            "42",
            "--channel-model",
            "simris",
            "--environment",
            "indoor",
            "--scenario",
            "1",
            "--ap-y",
            "25",
            "--ris-x",
            "40",
            "--ris-y",
            "50",
            "--ue-x",
            "38",
            "--ue-y",
            "48",
        ],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "channel_model_requested" in result.stdout
    assert "simris" in result.stdout


def test_native_ui_connect_surfaces_engine_fallback_metadata():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "connect",
            "--topology",
            "examples/json/example_1_simple.json",
            "AP1",
            "R1",
            "UE1",
            "--channel-model",
            "simris",
            "--beam",
            "45",
            "--seed",
            "42",
            "--no-feedback",
            "--no-waveform",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Engine requested" in result.stdout
    assert "Engine used" in result.stdout
    assert "Engine fallback" in result.stdout
    assert "simris" in result.stdout
    assert "lightris" in result.stdout


def test_typer_rich_signal_wrapper_supports_breakdown():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "signal",
            "--topology",
            "examples/json/example_1_simple.json",
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

    assert "Signal Output" in result.stdout
    assert "AP→RIS" in result.stdout
    assert "RIS→UE" in result.stdout


def test_typer_rich_stream_wrapper_surfaces_missing_file(tmp_path):
    topology = _write_saved_network_state(tmp_path / "stream_state.json")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "stream",
            "--topology",
            str(topology),
            "AP1",
            "R1",
            "UE1",
            "--file",
            "missing_payload.bin",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Stream Output" in result.stdout
    assert "error:" in result.stdout.lower()


def _write_saved_network_state(path: Path) -> Path:
    net = RISNetwork(enable_messaging=False)
    net.add_ap("AP1", 0.0, 0.0, 0.0)
    net.add_ris("R1", 5.0, 0.0, 0.0, 16, 2, max_angle_deg=180.0)
    net.add_ue("UE1", 10.0, 0.0, 0.0)
    net.connect("AP1", "R1", "UE1", seed=42, use_get_snr=False)
    NetworkIO().save(net, str(path))
    return path


def test_typer_rich_add_random_from_outside_repo():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "add", "random"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added random topology" in result.stdout
    assert "Nodes" in result.stdout
    assert "AP1" in result.stdout
    assert "R1" in result.stdout
    assert "UE1" in result.stdout


def test_typer_rich_add_random_accepts_counts():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "add", "random", "2", "1", "3"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added random topology (2 AP, 1 RIS, 3 UE)" in result.stdout
    assert "Nodes         6" in result.stdout
    assert "AP2" in result.stdout
    assert "UE3" in result.stdout


def test_typer_rich_add_random_accepts_distance_range():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "add", "random", "--distance", "8-12"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added random topology (1 AP, 1 RIS, 1 UE)" in result.stdout
    assert "UE distance range 8.0m-12.0m" in result.stdout


def test_typer_rich_add_random_accepts_no_ue():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "add", "random", "1", "1", "--no-ue"],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added random topology (1 AP, 1 RIS, 0 UE)" in result.stdout
    assert "Nodes         2" in result.stdout
    assert "UE1" not in result.stdout


def test_typer_rich_list_from_outside_repo_uses_topology():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "list",
            "--topology",
            "examples/json/example_1_simple.json",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "List Output" in result.stdout
    assert "Topology View (ASCII)" in result.stdout
    assert "Topology Legend" in result.stdout
    assert "Node Coordinates" in result.stdout
    assert "AccessPoint" in result.stdout
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

    assert "Connect Diagnostics" in result.stdout
    assert "Link Result" in result.stdout
    assert "RIS Recommendation" in result.stdout
    assert "snr_dB" in result.stdout


def test_typer_rich_connect_accepts_legacy_positional_angle_syntax():
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
            "30",
            "--topology",
            "examples/json/example_1_simple.json",
            "42",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Connect Diagnostics" in result.stdout
    assert "Link Result" in result.stdout
    assert "Requested angle (deg)" in result.stdout
    assert "beam_angle_deg" in result.stdout
    assert "30.000" in result.stdout


def test_native_ui_shell_connect_accepts_legacy_sweep_syntax_without_fallback():
    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "shell"],
        cwd="/home/user/project/risnet",
        input=(
            "load examples/json/example_1_simple.json\n"
            "connect AP1 R1 UE1 --sweep 60 10 --algo linear\n"
            "quit\n"
        ),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Sweep Result (linear)" in result.stdout
    assert "Best SNR (dB)" in result.stdout
    assert "BEAM SWEEP (via unified connect command)" not in result.stdout


def test_typer_rich_save_and_load_round_trip(tmp_path):
    saved = tmp_path / "waveflow_ui_saved.json"

    save_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "save",
            str(saved),
            "--topology",
            "examples/json/example_1_simple.json",
        ],
        cwd="/home/user/project/risnet",
        check=True,
        capture_output=True,
        text=True,
    )

    assert saved.exists()
    assert "Saved" in save_result.stdout

    load_result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "load", str(saved)],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Loaded" in load_result.stdout
    assert "Waveflow Terminal" in load_result.stdout
    assert "AP1" in load_result.stdout


def test_typer_rich_links_from_saved_state(tmp_path):
    state_file = _write_saved_network_state(tmp_path / "state_with_links.json")

    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "links", "--topology", str(state_file)],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Active Links" in result.stdout
    assert "Source" in result.stdout
    assert "AP1→R1→UE1" in result.stdout


def test_typer_rich_clear_links_from_saved_state(tmp_path):
    state_file = _write_saved_network_state(tmp_path / "state_to_clear.json")

    result = subprocess.run(
        [sys.executable, "-m", "risnet", "ui", "clear", "links", "--topology", str(state_file)],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Active links cleared." in result.stdout


def test_typer_rich_plot_connect_from_saved_state(tmp_path):
    state_file = _write_saved_network_state(tmp_path / "state_for_plot.json")
    output_path = tmp_path / "connect_plot.png"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "risnet",
            "ui",
            "plot",
            str(state_file),
            "--type",
            "connect",
            "--out",
            str(output_path),
        ],
        cwd="/tmp",
        check=True,
        capture_output=True,
        text=True,
    )

    assert output_path.exists()
    assert "Plot saved to" in result.stdout


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
