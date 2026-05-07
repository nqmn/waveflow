"""Shared headless scenario execution services and request types.

Canonical boundaries:

- topology file: persisted network layout/state consumable by ``NetworkIO``
- scenario request: declarative description of connect/sweep actions to run
- scenario result: typed wrapper around the executed action output

This module intentionally keeps execution headless so Flask, CLI, notebooks,
and direct Python callers can share the same service path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union
import yaml

from cli.helpers import NetworkIO
from core import RISNetwork
from controller import RISController


@dataclass
class ScenarioRunResult:
    """Headless connect execution result for a loaded topology."""

    topology_path: Path
    network: RISNetwork
    action: str
    ap_name: str
    ris_name: str
    ue_name: str
    result: Dict


@dataclass
class ScenarioSequenceResult:
    """Headless multi-action execution result for a loaded topology."""

    topology_path: Path
    network: RISNetwork
    steps: list[ScenarioRunResult]


@dataclass
class ConnectScenario:
    """Declarative connect action for a loaded topology."""

    ap_name: Optional[str] = None
    ris_name: Optional[str] = None
    ue_name: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SweepScenario:
    """Declarative sweep action for a loaded topology."""

    ap_name: Optional[str] = None
    ris_name: Optional[str] = None
    ue_name: Optional[str] = None
    kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScenarioRequest:
    """Minimal explicit request surface for a headless scenario run."""

    topology_path: Path
    connect: Optional[ConnectScenario] = None
    sweep: Optional[SweepScenario] = None
    actions: list[Union[ConnectScenario, SweepScenario]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScenarioRequest":
        """Build a scenario request from a plain dictionary."""
        if not isinstance(data, Mapping):
            raise ValueError("Scenario document must contain a top-level mapping.")
        if "topology_path" not in data:
            raise ValueError("Scenario document requires 'topology_path'.")

        topology_path_value = data["topology_path"]
        if topology_path_value is None or str(topology_path_value).strip() == "":
            raise ValueError("Scenario document requires a non-empty 'topology_path'.")
        topology_path = Path(topology_path_value)
        connect = None
        if data.get("connect") is not None:
            connect_data = data["connect"]
            if not isinstance(connect_data, Mapping):
                raise ValueError("Scenario 'connect' entry must be a mapping.")
            cls._validate_action_mapping(connect_data, label="connect")
            connect = ConnectScenario(**connect_data)

        sweep = None
        if data.get("sweep") is not None:
            sweep_data = data["sweep"]
            if not isinstance(sweep_data, Mapping):
                raise ValueError("Scenario 'sweep' entry must be a mapping.")
            cls._validate_action_mapping(sweep_data, label="sweep")
            sweep = SweepScenario(**sweep_data)

        actions = [cls._parse_action(item) for item in data.get("actions", [])]
        request = cls(topology_path=topology_path, connect=connect, sweep=sweep, actions=actions)
        request.validate()
        return request

    @classmethod
    def from_file(cls, path: str | Path) -> "ScenarioRequest":
        """Load a scenario request from a JSON or YAML document."""
        request_path = Path(path)
        suffix = request_path.suffix.lower()
        with open(request_path, "r", encoding="utf-8") as handle:
            if suffix == ".json":
                data = json.load(handle)
            elif suffix in {".yaml", ".yml"}:
                data = yaml.safe_load(handle)
            else:
                raise ValueError(f"Unsupported scenario document format: {request_path.suffix}")
        return cls.from_dict(data)

    @staticmethod
    def _parse_action(data: Dict[str, Any]) -> Union[ConnectScenario, SweepScenario]:
        if not isinstance(data, Mapping):
            raise ValueError("Each scenario action must be a mapping.")
        action_type = data.get("type", "connect")
        ScenarioRequest._validate_action_mapping(data, label=f"action '{action_type}'")
        action_data = {
            "ap_name": data.get("ap_name"),
            "ris_name": data.get("ris_name"),
            "ue_name": data.get("ue_name"),
            "kwargs": data.get("kwargs", {}),
        }
        if action_type == "connect":
            return ConnectScenario(**action_data)
        if action_type == "sweep":
            return SweepScenario(**action_data)
        raise ValueError(f"Unsupported scenario action type: {action_type}")

    @staticmethod
    def _validate_action_mapping(data: Mapping[str, Any], *, label: str) -> None:
        kwargs = data.get("kwargs", {})
        if kwargs is None:
            return
        if not isinstance(kwargs, Mapping):
            raise ValueError(f"Scenario {label} kwargs must be a mapping.")

    def validate(self) -> None:
        """Validate mutually exclusive request shapes."""
        if self.actions and (self.connect is not None or self.sweep is not None):
            raise ValueError(
                "ScenarioRequest cannot mix 'actions' with top-level 'connect' or 'sweep'."
            )
        if not self.actions and self.connect is None and self.sweep is None:
            raise ValueError("ScenarioRequest requires `connect`, `sweep`, or `actions`.")


class ScenarioExecutionService:
    """Shared execution service used by ScenarioRunner and client adapters."""

    def resolve_connect_names(
        self,
        net: RISNetwork,
        ap_name: Optional[str],
        ris_name: Optional[str],
        ue_name: Optional[str],
    ) -> tuple[str, str, str]:
        if ap_name is None:
            ap_name = self._first_node_name(net, "AccessPoint")
        if ris_name is None:
            ris_name = self._first_node_name(net, "RIS")
        if ue_name is None:
            ue_name = self._first_node_name(net, "UE")
        return ap_name, ris_name, ue_name

    @staticmethod
    def _first_node_name(net: RISNetwork, type_name: str) -> str:
        for name in sorted(net.nodes):
            if type(net.nodes[name]).__name__ == type_name:
                return name
        raise ValueError(f"No {type_name} nodes available in loaded topology.")

    def execute_connect(
        self,
        net: RISNetwork,
        topology_path: str | Path,
        *,
        ap_name: Optional[str] = None,
        ris_name: Optional[str] = None,
        ue_name: Optional[str] = None,
        **connect_kwargs,
    ) -> ScenarioRunResult:
        topology = Path(topology_path)
        ap_name, ris_name, ue_name = self.resolve_connect_names(net, ap_name, ris_name, ue_name)
        result = net.connect(ap_name, ris_name, ue_name, **connect_kwargs)
        return ScenarioRunResult(
            topology_path=topology,
            network=net,
            action="connect",
            ap_name=ap_name,
            ris_name=ris_name,
            ue_name=ue_name,
            result=result,
        )

    def execute_sweep(
        self,
        net: RISNetwork,
        topology_path: str | Path,
        *,
        ap_name: Optional[str] = None,
        ris_name: Optional[str] = None,
        ue_name: Optional[str] = None,
        **sweep_kwargs,
    ) -> ScenarioRunResult:
        topology = Path(topology_path)
        ap_name, ris_name, ue_name = self.resolve_connect_names(net, ap_name, ris_name, ue_name)
        result = net.sweep(ap_name, ris_name, ue_name, **sweep_kwargs)
        return ScenarioRunResult(
            topology_path=topology,
            network=net,
            action="sweep",
            ap_name=ap_name,
            ris_name=ris_name,
            ue_name=ue_name,
            result=result,
        )

    def execute_request(self, net: RISNetwork, request: ScenarioRequest) -> ScenarioRunResult:
        request.validate()

        if request.actions:
            steps = [self._execute_action(net, request.topology_path, action) for action in request.actions]
            return ScenarioSequenceResult(
                topology_path=Path(request.topology_path),
                network=net,
                steps=steps,
            )

        if request.sweep is not None:
            return self.execute_sweep(
                net,
                request.topology_path,
                ap_name=request.sweep.ap_name,
                ris_name=request.sweep.ris_name,
                ue_name=request.sweep.ue_name,
                **request.sweep.kwargs,
            )

        return self.execute_connect(
            net,
            request.topology_path,
            ap_name=request.connect.ap_name if request.connect else None,
            ris_name=request.connect.ris_name if request.connect else None,
            ue_name=request.connect.ue_name if request.connect else None,
            **(request.connect.kwargs if request.connect else {}),
        )

    def _execute_action(
        self,
        net: RISNetwork,
        topology_path: str | Path,
        action: Union[ConnectScenario, SweepScenario],
    ) -> ScenarioRunResult:
        if isinstance(action, ConnectScenario):
            return self.execute_connect(
                net,
                topology_path,
                ap_name=action.ap_name,
                ris_name=action.ris_name,
                ue_name=action.ue_name,
                **action.kwargs,
            )
        if isinstance(action, SweepScenario):
            return self.execute_sweep(
                net,
                topology_path,
                ap_name=action.ap_name,
                ris_name=action.ris_name,
                ue_name=action.ue_name,
                **action.kwargs,
            )
        raise TypeError(f"Unsupported scenario action: {type(action).__name__}")


class ScenarioRunner:
    """Load a topology and execute a minimal headless connect workflow."""

    def __init__(self, *, network_io: Optional[NetworkIO] = None, enable_controller: bool = True):
        self.network_io = network_io or NetworkIO()
        self.enable_controller = enable_controller
        self.service = ScenarioExecutionService()

    def _new_network(self) -> RISNetwork:
        net = RISNetwork(enable_messaging=False)
        if self.enable_controller:
            controller = RISController(net, net.environment)
            net.set_controller(controller)
        return net

    def load_topology(self, topology_path: str | Path) -> RISNetwork:
        net = self._new_network()
        self.network_io.load(net, str(Path(topology_path)))
        return net

    def _resolve_connect_names(self, net: RISNetwork,
                               ap_name: Optional[str],
                               ris_name: Optional[str],
                               ue_name: Optional[str]) -> tuple[str, str, str]:
        return self.service.resolve_connect_names(net, ap_name, ris_name, ue_name)

    @staticmethod
    def _first_node_name(net: RISNetwork, type_name: str) -> str:
        return ScenarioExecutionService._first_node_name(net, type_name)

    def run_connect(self, topology_path: str | Path, *,
                    ap_name: Optional[str] = None,
                    ris_name: Optional[str] = None,
                    ue_name: Optional[str] = None,
                    network: Optional[RISNetwork] = None,
                    **connect_kwargs) -> ScenarioRunResult:
        topology = Path(topology_path)
        net = network if network is not None else self.load_topology(topology)
        return self.service.execute_connect(
            net,
            topology,
            ap_name=ap_name,
            ris_name=ris_name,
            ue_name=ue_name,
            **connect_kwargs,
        )

    def run_sweep(self, topology_path: str | Path, *,
                  ap_name: Optional[str] = None,
                  ris_name: Optional[str] = None,
                  ue_name: Optional[str] = None,
                  network: Optional[RISNetwork] = None,
                  **sweep_kwargs) -> ScenarioRunResult:
        topology = Path(topology_path)
        net = network if network is not None else self.load_topology(topology)
        return self.service.execute_sweep(
            net,
            topology,
            ap_name=ap_name,
            ris_name=ris_name,
            ue_name=ue_name,
            **sweep_kwargs,
        )

    def run(self, request: ScenarioRequest) -> ScenarioRunResult:
        """Execute a declarative scenario request."""
        net = self.load_topology(request.topology_path)
        return self.service.execute_request(net, request)

    def _run_action(self, topology_path: str | Path,
                    action: Union[ConnectScenario, SweepScenario],
                    *, network: RISNetwork) -> ScenarioRunResult:
        return self.service._execute_action(network, topology_path, action)
