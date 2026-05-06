"""Minimal headless scenario runner built on the existing JSON topology format."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from cli.helpers import NetworkIO
from core import RISNetwork
from controller import RISController


@dataclass
class ScenarioRunResult:
    """Headless connect execution result for a loaded topology."""

    topology_path: Path
    network: RISNetwork
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
class ScenarioRequest:
    """Minimal explicit request surface for a headless scenario run."""

    topology_path: Path
    connect: Optional[ConnectScenario] = None
    actions: list[ConnectScenario] = field(default_factory=list)


class ScenarioRunner:
    """Load a topology and execute a minimal headless connect workflow."""

    def __init__(self, *, network_io: Optional[NetworkIO] = None, enable_controller: bool = True):
        self.network_io = network_io or NetworkIO()
        self.enable_controller = enable_controller

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

    def run_connect(self, topology_path: str | Path, *,
                    ap_name: Optional[str] = None,
                    ris_name: Optional[str] = None,
                    ue_name: Optional[str] = None,
                    network: Optional[RISNetwork] = None,
                    **connect_kwargs) -> ScenarioRunResult:
        topology = Path(topology_path)
        net = network if network is not None else self.load_topology(topology)
        ap_name, ris_name, ue_name = self._resolve_connect_names(net, ap_name, ris_name, ue_name)
        result = net.connect(ap_name, ris_name, ue_name, **connect_kwargs)
        return ScenarioRunResult(
            topology_path=topology,
            network=net,
            ap_name=ap_name,
            ris_name=ris_name,
            ue_name=ue_name,
            result=result,
        )

    def run(self, request: ScenarioRequest) -> ScenarioRunResult:
        """Execute a declarative scenario request."""
        if request.actions:
            net = self.load_topology(request.topology_path)
            steps = [
                self.run_connect(
                    request.topology_path,
                    ap_name=action.ap_name,
                    ris_name=action.ris_name,
                    ue_name=action.ue_name,
                    network=net,
                    **action.kwargs,
                )
                for action in request.actions
            ]
            return ScenarioSequenceResult(
                topology_path=Path(request.topology_path),
                network=net,
                steps=steps,
            )

        if request.connect is None:
            raise ValueError("ScenarioRequest requires either `connect` or `actions`.")

        return self.run_connect(
            request.topology_path,
            ap_name=request.connect.ap_name,
            ris_name=request.connect.ris_name,
            ue_name=request.connect.ue_name,
            **request.connect.kwargs,
        )
