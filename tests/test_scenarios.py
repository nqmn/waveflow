"""Focused tests for the additive headless scenario runner."""

from pathlib import Path

import pytest

from app import create_app
from app.api import bp as api_bp_module
from controller import RISController
from core import RISNetwork
from risnet import (
    ConnectScenario,
    ScenarioExecutionService,
    ScenarioRequest,
    ScenarioRunResult,
    ScenarioRunner,
    ScenarioSequenceResult,
    SweepScenario,
)


EXAMPLE_SIMPLE = Path("examples/json/example_1_simple.json")
EXAMPLE_OBSTACLES = Path("examples/json/example_4_obstacles.json")
EXAMPLE_GRID = Path("examples/json/example_5_grid_topology.json")


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
    assert run.action == "connect"
    assert run.ap_name == "AP1"
    assert run.ris_name == "R1"
    assert run.ue_name == "UE1"
    assert "snr_dB" in run.result
    assert run.result["ue_present"] is True
    assert run.network.last_connect_result["ap"] == "AP1"


def test_scenario_runner_accepts_official_lightris_engine_name(tmp_path):
    topology_path = tmp_path / "headless_connect_lightris.json"
    topology_path.write_text(
        """
{
  "name": "Headless Connect LightRIS",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )

    runner = ScenarioRunner()

    run = runner.run_connect(
        topology_path,
        channel_model="lightris",
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )

    assert run.result["channel_model_requested"] == "lightris"
    assert run.result["channel_model_used"] == "lightris"
    assert run.result["channel_model_fallback_reason"] is None
    assert run.network.last_connect_result["metrics"]["channel_model_used"] == "lightris"


def test_scenario_runner_passes_official_simris_connect_kwargs(tmp_path):
    topology_path = tmp_path / "headless_connect_simris.json"
    topology_path.write_text(
        """
{
  "name": "Headless Connect SimRIS",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 25.0, 2.0], "freq": 28000000000.0},
    {"name": "R1", "type": "RIS", "pos": [40.0, 50.0, 2.0], "N": 8, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [38.0, 48.0, 1.0]}
  ]
}
""".strip()
    )

    runner = ScenarioRunner()

    run = runner.run_connect(
        topology_path,
        channel_model="simris",
        environment="indoor",
        scenario=1,
        tx_antennas=1,
        rx_antennas=1,
        num_realizations=1,
        use_get_snr=False,
        store_in_active_links=False,
    )

    assert run.result["channel_model_requested"] == "simris"
    assert run.result["channel_model_used"] == "simris"
    assert run.result["model"] == "simris_stochastic"
    assert run.result["H"].shape == (64, 1, 1)
    assert run.network.last_connect_result["metrics"]["channel_model_used"] == "simris"


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
    assert run.steps[0].action == "connect"
    assert run.steps[1].action == "connect"
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

    assert "requires `connect`, `sweep`, or `actions`" in str(exc_info.value)


def test_scenario_runner_executes_request_sweep(tmp_path):
    topology_path = tmp_path / "scenario_sweep.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Sweep",
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
        sweep=SweepScenario(kwargs={"fov": 60, "step": 10, "seed": 42}),
    )

    run = runner.run(request)

    assert isinstance(run, ScenarioRunResult)
    assert run.action == "sweep"
    assert run.ap_name == "AP1"
    assert run.ris_name == "R1"
    assert run.ue_name == "UE1"
    assert "best_snr_fine" in run.result


def test_scenario_runner_executes_mixed_action_list(tmp_path):
    topology_path = tmp_path / "scenario_mixed_actions.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Mixed Actions",
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
            SweepScenario(kwargs={"fov": 60, "step": 10, "seed": 42}),
        ],
    )

    run = runner.run(request)

    assert isinstance(run, ScenarioSequenceResult)
    assert [step.action for step in run.steps] == ["connect", "sweep"]
    assert run.steps[0].network is run.network
    assert run.steps[1].network is run.network


def test_scenario_request_from_dict_builds_mixed_actions(tmp_path):
    topology_path = tmp_path / "scenario_from_dict.json"
    topology_path.write_text(
        """
{
  "name": "Scenario From Dict",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )
    request = ScenarioRequest.from_dict(
        {
            "topology_path": str(topology_path),
            "actions": [
                {"type": "connect", "kwargs": {"seed": 42, "use_get_snr": False}},
                {"type": "sweep", "kwargs": {"fov": 60, "step": 10, "seed": 42}},
            ],
        }
    )

    assert request.topology_path == topology_path
    assert isinstance(request.actions[0], ConnectScenario)
    assert isinstance(request.actions[1], SweepScenario)


def test_scenario_request_from_json_file_executes(tmp_path):
    topology_path = tmp_path / "scenario_doc_topology.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Doc Topology",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )
    request_path = tmp_path / "scenario_request.json"
    request_path.write_text(
        f"""
{{
  "topology_path": "{topology_path}",
  "connect": {{
    "kwargs": {{"seed": 42, "use_get_snr": false}}
  }}
}}
""".strip()
    )
    runner = ScenarioRunner()
    request = ScenarioRequest.from_file(request_path)

    run = runner.run(request)

    assert isinstance(run, ScenarioRunResult)
    assert run.action == "connect"
    assert run.ap_name == "AP1"


def test_scenario_request_from_yaml_file_executes_mixed_actions(tmp_path):
    topology_path = tmp_path / "scenario_doc_topology.yaml.json"
    topology_path.write_text(
        """
{
  "name": "Scenario Doc YAML Topology",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1", "type": "RIS", "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1, "max_angle_deg": 90.0},
    {"name": "UE1", "type": "UE", "pos": [10.0, 5.0, 0.0]}
  ]
}
""".strip()
    )
    request_path = tmp_path / "scenario_request.yaml"
    request_path.write_text(
        f"""
topology_path: {topology_path}
actions:
  - type: connect
    kwargs:
      seed: 42
      use_get_snr: false
  - type: sweep
    kwargs:
      fov: 60
      step: 10
      seed: 42
""".strip()
    )
    runner = ScenarioRunner()
    request = ScenarioRequest.from_file(request_path)

    run = runner.run(request)

    assert isinstance(run, ScenarioSequenceResult)
    assert [step.action for step in run.steps] == ["connect", "sweep"]


def test_scenario_execution_service_matches_runner_for_connect():
    runner = ScenarioRunner()
    net = runner.load_topology(EXAMPLE_SIMPLE)

    service_run = ScenarioExecutionService().execute_connect(
        net,
        EXAMPLE_SIMPLE,
        seed=42,
        use_get_snr=False,
    )
    runner_run = runner.run_connect(EXAMPLE_SIMPLE, seed=42, use_get_snr=False)

    assert service_run.action == "connect"
    assert service_run.result["snr_dB"] == pytest.approx(runner_run.result["snr_dB"])


def test_scenario_execution_service_matches_runner_for_sweep():
    runner = ScenarioRunner()
    net = runner.load_topology(EXAMPLE_SIMPLE)

    service_run = ScenarioExecutionService().execute_sweep(
        net,
        EXAMPLE_SIMPLE,
        fov=60,
        step=10,
        seed=42,
    )
    runner_run = runner.run_sweep(EXAMPLE_SIMPLE, fov=60, step=10, seed=42)

    assert service_run.action == "sweep"
    assert service_run.result["best_snr_fine"] == pytest.approx(runner_run.result["best_snr_fine"])


def test_scenario_request_rejects_mixed_actions_and_top_level_connect():
    with pytest.raises(ValueError) as exc_info:
        ScenarioRequest.from_dict(
            {
                "topology_path": "examples/json/example_1_simple.json",
                "connect": {"kwargs": {"seed": 42}},
                "actions": [{"type": "connect", "kwargs": {"seed": 42}}],
            }
        )

    assert "cannot mix 'actions'" in str(exc_info.value)


def test_scenario_request_rejects_non_mapping_kwargs():
    with pytest.raises(ValueError) as exc_info:
        ScenarioRequest.from_dict(
            {
                "topology_path": "examples/json/example_1_simple.json",
                "connect": {"kwargs": ["not", "a", "mapping"]},
            }
        )

    assert "kwargs must be a mapping" in str(exc_info.value)


def test_scenario_request_requires_non_empty_topology_path():
    with pytest.raises(ValueError) as exc_info:
        ScenarioRequest.from_dict({"topology_path": "", "connect": {"kwargs": {}}})

    assert "non-empty 'topology_path'" in str(exc_info.value)


def test_scenario_runner_loads_obstacle_topology_fixture():
    runner = ScenarioRunner()

    net = runner.load_topology(EXAMPLE_OBSTACLES)

    assert sorted(net.nodes) == ["AP1", "R1", "UE1"]
    assert len(net.environment.walls) > 0


def test_scenario_runner_loads_grid_topology_fixture():
    runner = ScenarioRunner()

    net = runner.load_topology(EXAMPLE_GRID)

    assert sorted(net.nodes) == ["AP1", "R1", "R2", "R3", "R4", "UE1"]


def test_api_connect_route_executes_via_shared_scenario_service(monkeypatch):
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0.0, 2.0, 0.0)
    net.add_ris("ris1", 5.0, 2.0, 0.0, N=16, bits=1, max_angle_deg=90.0)
    net.add_ue("ue1", 10.0, 5.0, 0.0)
    controller = RISController(net, net.environment)
    net.set_controller(controller)
    app = create_app(net, controller)

    calls = {"count": 0}
    original = api_bp_module._scenario_service.execute_connect

    def wrapped_execute_connect(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(api_bp_module._scenario_service, "execute_connect", wrapped_execute_connect)

    response = app.test_client().get("/api/connect?ap=ap1&ris=ris1&ue=ue1&angle=0")

    assert response.status_code == 200
    assert calls["count"] == 1
    assert "snr_dB" in response.get_json()


def test_api_sweep_route_executes_via_shared_scenario_service(monkeypatch):
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0.0, 2.0, 0.0)
    net.add_ris("ris1", 5.0, 2.0, 0.0, N=16, bits=1, max_angle_deg=90.0)
    net.add_ue("ue1", 10.0, 5.0, 0.0)
    controller = RISController(net, net.environment)
    net.set_controller(controller)
    app = create_app(net, controller)

    calls = {"count": 0}
    original = api_bp_module._scenario_service.execute_sweep

    def wrapped_execute_sweep(*args, **kwargs):
        calls["count"] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(api_bp_module._scenario_service, "execute_sweep", wrapped_execute_sweep)

    response = app.test_client().get("/api/sweep?ap=ap1&ris=ris1&ue=ue1")

    assert response.status_code == 200
    assert calls["count"] == 1
    assert "best_snr_fine" in response.get_json()
