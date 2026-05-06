"""Focused tests for the additive headless scenario runner."""

from pathlib import Path

import pytest

from risnet import (
    ConnectScenario,
    ScenarioRequest,
    ScenarioRunResult,
    ScenarioRunner,
    ScenarioSequenceResult,
)


EXAMPLE_SIMPLE = Path("examples/json/example_1_simple.json")


def test_scenario_runner_loads_json_topology_without_flask_or_cli():
    runner = ScenarioRunner()

    net = runner.load_topology(EXAMPLE_SIMPLE)

    assert sorted(net.nodes) == ["AP1", "R1", "UE1"]
    assert type(net.get("AP1")).__name__ == "AccessPoint"
    assert type(net.get("R1")).__name__ == "RIS"
    assert type(net.get("UE1")).__name__ == "UE"


def test_scenario_runner_executes_connect_with_auto_resolved_names(tmp_path):
    topology_path = tmp_path / "headless_connect.json"
    topology_path.write_text(
        """
{
  "name": "Headless Connect",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )

    runner = ScenarioRunner()

    run = runner.run_connect(topology_path, seed=42, use_get_snr=False)

    assert isinstance(run, ScenarioRunResult)
    assert run.ap_name == "AP1"
    assert run.ris_name == "R1"
    assert run.ue_name == "UE1"
    assert "snr_dB" in run.result
    assert run.result["ue_present"] is True
    assert run.network.last_connect_result["ap"] == "AP1"


def test_scenario_runner_reports_missing_required_node_types():
    runner = ScenarioRunner()
    net = runner.load_topology(EXAMPLE_SIMPLE)
    del net.nodes["R1"]

    with pytest.raises(ValueError) as exc_info:
        runner._resolve_connect_names(net, None, None, None)

    assert "No RIS nodes available" in str(exc_info.value)


def test_scenario_runner_executes_request_schema(tmp_path):
    topology_path = tmp_path / "scenario_request.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Request",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )
    runner = ScenarioRunner()
    request = ScenarioRequest(
        topology_path=topology_path,
        connect=ConnectScenario(kwargs={"seed": 42, "use_get_snr": False}),
    )

    run = runner.run(request)

    assert run.ap_name == "AP1"
    assert run.ris_name == "R1"
    assert run.ue_name == "UE1"
    assert run.result["snr_dB"] == pytest.approx(
        runner.run_connect(topology_path, seed=42, use_get_snr=False).result["snr_dB"]
    )


def test_scenario_runner_executes_action_list_on_shared_network(tmp_path):
    topology_path = tmp_path / "scenario_actions.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Actions",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )
    runner = ScenarioRunner()
    request = ScenarioRequest(
        topology_path=topology_path,
        actions=[
            ConnectScenario(kwargs={"seed": 42, "use_get_snr": False}),
            ConnectScenario(kwargs={"seed": 42, "use_get_snr": False, "store_in_active_links": False}),
        ],
    )

    run = runner.run(request)

    assert isinstance(run, ScenarioSequenceResult)
    assert len(run.steps) == 2
    assert run.steps[0].network is run.network
    assert run.steps[1].network is run.network
    assert run.steps[0].result["snr_dB"] == pytest.approx(run.steps[1].result["snr_dB"])
    assert run.network.last_connect_result["ap"] == "AP1"


def test_scenario_request_requires_connect_or_actions(tmp_path):
    topology_path = tmp_path / "empty_request.json"
    topology_path.write_text(
        """
{"name": "Empty Request", "nodes": []}
""".strip()
    )
    runner = ScenarioRunner()

    with pytest.raises(ValueError) as exc_info:
        runner.run(ScenarioRequest(topology_path=topology_path))

    assert "requires either `connect` or `actions`" in str(exc_info.value)
