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
            pos = tuple(float(value) for value in node.pos[:3])
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

    @app.command("status")
    def status(
        topology: Optional[Path] = typer.Option(
            None,
            "--topology",
            "-t",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Load a saved network JSON before rendering status.",
        ),
    ) -> None:
        """Show network status with Rich tables."""
        net = _new_network()
        _load_topology(net, topology)
        _render_network(net)

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
            net,
            "ap1",
            "ris1",
            "ue1",
            seed=seed,
            use_get_snr=False,
        )

        _render_network(net)

        metrics = Table(title="Link Metrics")
        metrics.add_column("Metric", style="cyan")
        metrics.add_column("Value", justify="right")
        for key in ("snr_dB", "pwr_dBm", "rssi_dBm", "gain_dBi", "quant_loss_dB", "beam_angle"):
            metrics.add_row(key, f"{float(evaluation.result[key]):.3f}")
        console.print(metrics)

    @app.command("shell")
    def shell(
        topology: Optional[Path] = typer.Option(
            None,
            "--topology",
            "-t",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Load a saved network JSON before opening the legacy shell.",
        ),
    ) -> None:
        """Open the existing interactive shell from the terminal command surface."""
        from cli.main_shell import RISNetCLI

        net = _new_network()
        cli = RISNetCLI(net)
        if topology is not None:
            cli._load_network_from_file(str(topology))
        console.print("[bold cyan]Opening legacy interactive shell.[/bold cyan]")
        cli.cmdloop()

    try:
        app(args=list(argv or []), prog_name="waveflow terminal")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0
