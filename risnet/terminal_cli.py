"""Optional Typer/Rich terminal commands for Waveflow."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional


def run(argv: Optional[List[str]] = None) -> int:
    """Run the optional Typer/Rich terminal command surface."""
    try:
        import typer
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        print(
            "The terminal UI requires optional dependencies. "
            "Install with: pip install -e '.[terminal]'",
            file=sys.stderr,
        )
        return 2

    console = Console()
    app = typer.Typer(
        add_completion=False,
        help="Modern terminal commands for Waveflow.",
        no_args_is_help=True,
    )

    def _new_network():
        from core import RISNetwork

        return RISNetwork(enable_messaging=False)

    def _new_network_with_controller():
        from controller.ris_controller import RISController
        from core import RISNetwork

        net = RISNetwork(enable_messaging=False)
        ctrl = RISController(net, net.environment)
        net.set_controller(ctrl)
        return net

    def _load_topology(net, topology: Optional[Path]) -> None:
        if topology is None:
            return
        from cli.helpers import NetworkIO
        NetworkIO().load(net, str(topology))

    def _node_type(node) -> str:
        return type(node).__name__

    def _render_network(net) -> None:
        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold")
        summary.add_column()
        summary.add_row("Nodes", str(len(net.nodes)))
        summary.add_row("Active links", str(len(getattr(net, "active_links", {}))))
        summary.add_row("Walls", str(len(getattr(net.environment, "walls", []))))
        console.print(Panel(summary, title="Waveflow Terminal", expand=False))

        table = Table(title="Nodes")
        table.add_column("Name", style="cyan")
        table.add_column("Type")
        table.add_column("Position")
        table.add_column("Details")

        for name in sorted(net.nodes):
            node = net.nodes[name]
            pos = tuple(float(v) for v in node.pos[:3])
            details = []
            if hasattr(node, "power_dBm"):
                details.append(f"power={node.power_dBm:.1f} dBm")
            if hasattr(node, "N"):
                details.append(f"N={node.N} bits={node.bits}")
            if hasattr(node, "max_angle_deg"):
                details.append(f"fov=±{node.max_angle_deg:g}°")
            table.add_row(name, _node_type(node), f"({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})", ", ".join(details))

        if not net.nodes:
            table.add_row("-", "empty", "-", "Use demo-connect or load a topology")

        console.print(table)

    def _render_connect_result(result: dict) -> None:
        table = Table(title="Link Result")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        for key in ("snr_dB", "pwr_dBm", "rssi_dBm", "beam_angle_deg", "gain_dBi", "quant_loss_dB"):
            if key in result:
                table.add_row(key, f"{float(result[key]):.3f}")
        console.print(table)

    # -------------------------------------------------------------------------
    # status
    # -------------------------------------------------------------------------

    @app.command("status")
    def status(
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load a saved network JSON before rendering status.",
        ),
    ) -> None:
        """Show network status with Rich tables."""
        net = _new_network()
        _load_topology(net, topology)
        _render_network(net)

    # -------------------------------------------------------------------------
    # list
    # -------------------------------------------------------------------------

    @app.command("list")
    def list_nodes(
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load a saved network JSON before listing.",
        ),
    ) -> None:
        """List all nodes in the network."""
        net = _new_network()
        _load_topology(net, topology)
        _render_network(net)

    # -------------------------------------------------------------------------
    # add
    # -------------------------------------------------------------------------

    @app.command("add")
    def add(
        node_type: str = typer.Argument(..., help="Node type: ap, ris, or ue."),
        name: Optional[str] = typer.Argument(None, help="Node name (auto-generated if omitted)."),
        x: float = typer.Option(0.0, "--x", help="X position."),
        y: float = typer.Option(0.0, "--y", help="Y position."),
        z: float = typer.Option(0.0, "--z", help="Z position."),
        n: int = typer.Option(16, "--n", help="RIS element count per side (RIS only)."),
        bits: int = typer.Option(2, "--bits", help="RIS phase bits (RIS only)."),
        power: float = typer.Option(20.0, "--power", help="TX power in dBm (AP only)."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load existing topology before adding.",
        ),
    ) -> None:
        """Add a node (ap, ris, or ue) to the network and display the result."""
        net = _new_network()
        _load_topology(net, topology)

        t = node_type.lower()
        auto_name = name
        if t == "ap":
            if auto_name is None:
                auto_name = f"AP{len([n for n in net.nodes if n.upper().startswith('AP')]) + 1}"
            net.add_ap(auto_name, x, y, z, power_dBm=power)
            console.print(f"[green]Added AP[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z})")
        elif t == "ris":
            if auto_name is None:
                auto_name = f"R{len([n for n in net.nodes if n.upper().startswith('R')]) + 1}"
            net.add_ris(auto_name, x, y, z, N=n, bits=bits)
            console.print(f"[green]Added RIS[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z}) N={n} bits={bits}")
        elif t == "ue":
            if auto_name is None:
                auto_name = f"UE{len([n for n in net.nodes if n.upper().startswith('UE')]) + 1}"
            net.add_ue(auto_name, x, y, z)
            console.print(f"[green]Added UE[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z})")
        else:
            console.print(f"[red]Unknown node type '{node_type}'. Use: ap, ris, ue[/red]")
            raise typer.Exit(1)

        _render_network(net)

    # -------------------------------------------------------------------------
    # connect
    # -------------------------------------------------------------------------

    @app.command("connect")
    def connect(
        ap: str = typer.Argument(..., help="AP node name."),
        ris: str = typer.Argument(..., help="RIS node name."),
        ue: str = typer.Argument(..., help="UE node name."),
        beam: Optional[float] = typer.Option(None, "--beam", help="Explicit beam angle in degrees."),
        seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for fading."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before connecting.",
        ),
    ) -> None:
        """Compute a cascaded AP→RIS→UE link and display metrics."""
        net = _new_network_with_controller()
        _load_topology(net, topology)
        try:
            result = net.connect(ap, ris, ue, beam_angle_deg=beam, seed=seed, use_get_snr=False)
            _render_connect_result(result)
        except Exception as exc:
            console.print(f"[red]Connect failed:[/red] {exc}")
            raise typer.Exit(1)

    # -------------------------------------------------------------------------
    # sweep
    # -------------------------------------------------------------------------

    @app.command("sweep")
    def sweep(
        ap: str = typer.Argument(..., help="AP node name."),
        ris: str = typer.Argument(..., help="RIS node name."),
        ue: str = typer.Argument(..., help="UE node name."),
        fov: float = typer.Option(60.0, "--fov", help="Field of view in degrees."),
        step: float = typer.Option(10.0, "--step", help="Coarse step size in degrees."),
        algo: str = typer.Option("coarse-fine", "--algo", help="Sweep algorithm name."),
        seed: int = typer.Option(0, "--seed", help="Random seed."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before sweeping.",
        ),
    ) -> None:
        """Run a beam sweep and display the best angle and SNR."""
        net = _new_network_with_controller()
        _load_topology(net, topology)
        try:
            result = net.sweep(ap, ris, ue, fov=fov, step=step, seed=seed)
            table = Table(title=f"Sweep Result ({algo})")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            table.add_row("Best angle (deg)", f"{result.get('best_local_fine', result.get('best_angle_deg', 'N/A')):.2f}")
            table.add_row("Best SNR (dB)", f"{result.get('best_snr_fine', result.get('best_snr_dB', 'N/A')):.2f}")
            coarse = result.get("snr_coarse", [])
            table.add_row("Coarse angles tested", str(len(coarse)))
            fine = result.get("snr_fine", [])
            table.add_row("Fine angles tested", str(len(fine)))
            console.print(table)
        except Exception as exc:
            console.print(f"[red]Sweep failed:[/red] {exc}")
            raise typer.Exit(1)

    # -------------------------------------------------------------------------
    # save / load
    # -------------------------------------------------------------------------

    @app.command("save")
    def save(
        filename: Optional[str] = typer.Argument(None, help="Output filename (default: .risnet_network.json)."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before saving.",
        ),
    ) -> None:
        """Save current network state to disk."""
        from cli.helpers import NetworkIO
        net = _new_network()
        _load_topology(net, topology)
        path = filename or ".risnet_network.json"
        NetworkIO().save(net, path)
        console.print(f"[green]Saved[/green] → {path}")

    @app.command("load")
    def load(
        filepath: str = typer.Argument(..., help="Path to saved network JSON."),
    ) -> None:
        """Load network state from disk and display it."""
        from cli.helpers import NetworkIO
        net = _new_network()
        NetworkIO().load(net, filepath)
        console.print(f"[green]Loaded[/green] ← {filepath}")
        _render_network(net)

    # -------------------------------------------------------------------------
    # clear
    # -------------------------------------------------------------------------

    @app.command("clear")
    def clear(
        target: str = typer.Argument("net", help="What to clear: net (default) or links."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before clearing.",
        ),
    ) -> None:
        """Clear the network (nodes + links) or active links only."""
        net = _new_network()
        _load_topology(net, topology)
        if target == "links":
            if hasattr(net, "active_links"):
                net.active_links.clear()
            console.print("[yellow]Active links cleared.[/yellow]")
        else:
            net.nodes.clear()
            if hasattr(net, "active_links"):
                net.active_links.clear()
            console.print("[yellow]Network cleared.[/yellow]")

    # -------------------------------------------------------------------------
    # demo-connect
    # -------------------------------------------------------------------------

    @app.command("demo-connect")
    def demo_connect(
        seed: int = typer.Option(42, "--seed", help="Seed for deterministic channel evaluation."),
        ap_x: float = typer.Option(0.0, "--ap-x", help="AP x position."),
        ap_y: float = typer.Option(0.0, "--ap-y", help="AP y position."),
        ris_x: float = typer.Option(5.0, "--ris-x", help="RIS x position."),
        ris_y: float = typer.Option(0.0, "--ris-y", help="RIS y position."),
        ue_x: float = typer.Option(10.0, "--ue-x", help="UE x position."),
        ue_y: float = typer.Option(0.0, "--ue-y", help="UE y position."),
    ) -> None:
        """Run a deterministic AP-RIS-UE demo link and print metrics."""
        from risnet.channels import LinkBudgetChannel

        net = _new_network()
        net.add_ap("ap1", ap_x, ap_y)
        net.add_ris("ris1", ris_x, ris_y, max_angle_deg=180)
        net.add_ue("ue1", ue_x, ue_y)

        evaluation = LinkBudgetChannel().evaluate(
            net, "ap1", "ris1", "ue1", seed=seed, use_get_snr=False,
        )

        _render_network(net)

        metrics = Table(title="Link Metrics")
        metrics.add_column("Metric", style="cyan")
        metrics.add_column("Value", justify="right")
        for key in ("snr_dB", "pwr_dBm", "rssi_dBm", "gain_dBi", "quant_loss_dB", "beam_angle"):
            metrics.add_row(key, f"{float(evaluation.result[key]):.3f}")
        console.print(metrics)

    # -------------------------------------------------------------------------
    # testall
    # -------------------------------------------------------------------------

    @app.command("testall")
    def testall() -> None:
        """Run the comprehensive test suite and display results."""
        from cli.test_suite import run_testall

        net = _new_network_with_controller()
        results = run_testall(net)
        for section in results.sections:
            console.rule(f"[bold]{section.title}[/bold]")
            for line in section.lines:
                console.print(line)

    # -------------------------------------------------------------------------
    # shell
    # -------------------------------------------------------------------------

    @app.command("shell")
    def shell(
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load a saved network JSON before opening the legacy shell.",
        ),
    ) -> None:
        """Open the interactive shell (access to all legacy commands)."""
        from cli.main_shell import RISNetCLI

        net = _new_network_with_controller()
        cli = RISNetCLI(net)
        if topology is not None:
            cli._load_network_from_file(str(topology))
        console.print("[bold cyan]Opening interactive shell. Type 'help' for all commands.[/bold cyan]")
        cli.cmdloop()

    # -------------------------------------------------------------------------
    # run  — delegate any legacy command verbatim
    # -------------------------------------------------------------------------

    @app.command("run")
    def run_cmd(
        command: List[str] = typer.Argument(..., help="Legacy CLI command and arguments."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before running the command.",
        ),
    ) -> None:
        """Run any legacy CLI command non-interactively.

        Examples:

          waveflow ui run signal AP1 R1 UE1 --breakdown

          waveflow ui run plot --type sweep

          waveflow ui run ap AP1 show
        """
        from cli.main_shell import RISNetCLI

        net = _new_network_with_controller()
        cli = RISNetCLI(net)
        if topology is not None:
            cli._load_network_from_file(str(topology))
        cmd_str = " ".join(command)
        try:
            cli.onecmd(cmd_str)
        except Exception as exc:
            console.print(f"[red]Command failed:[/red] {exc}")
            raise typer.Exit(1)

    try:
        app(args=list(argv or []), prog_name="waveflow ui")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0
