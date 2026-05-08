"""Optional Typer/Rich terminal commands for Waveflow."""

from __future__ import annotations

import io
import json
import math
import shlex
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Dict, List, Optional


def run(argv: Optional[List[str]] = None) -> int:
    """Run the optional Typer/Rich terminal command surface."""
    try:
        import typer
        from rich.console import Console
        from rich.live import Live
        from rich.panel import Panel
        from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        print(
            "The terminal UI requires optional dependencies. "
            "Install with: pip install -e '.[terminal]'",
            file=sys.stderr,
        )
        return 2

    # Typer resolves command annotations from module globals, not this local scope.
    globals()["typer"] = typer

    console = Console()
    app = typer.Typer(
        add_completion=False,
        help="Modern terminal commands for Waveflow.",
        no_args_is_help=True,
    )
    interactive_context: Dict[str, object] = {
        "net": None,
        "legacy_cli": None,
    }

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

    def _new_legacy_shell(topology: Optional[Path] = None, net=None):
        from cli.main_shell import RISNetCLI

        net = net or _new_network_with_controller()
        cli = RISNetCLI(net)
        if topology is not None:
            cli._load_network_from_file(str(topology))
        return cli

    def _resolve_context_net(topology: Optional[Path], *, with_controller: bool = False):
        if interactive_context["net"] is not None and topology is None:
            return interactive_context["net"]

        net = _new_network_with_controller() if with_controller else _new_network()
        _load_topology(net, topology)
        return net

    def _resolve_context_legacy_shell(topology: Optional[Path] = None):
        if interactive_context["legacy_cli"] is not None and topology is None:
            return interactive_context["legacy_cli"]

        return _new_legacy_shell(topology)

    def _load_topology(net, topology: Optional[Path]) -> None:
        if topology is None:
            return
        from cli.helpers import NetworkIO
        NetworkIO().load(net, str(topology))

    def _new_topology_helper(net):
        from cli.helpers import TopologyHelper

        return TopologyHelper(net)

    def _node_type(node) -> str:
        return type(node).__name__

    def _resolve_sweep_nodes_or_exit(net, ap: str, ris: str, ue: str) -> None:
        missing = [name for name in (ap, ris, ue) if net.get(name) is None]
        if not missing:
            return

        available = ", ".join(sorted(net.nodes)) if net.nodes else "none"
        if not net.nodes:
            detail = "No nodes are loaded. Pass --topology or add nodes before sweeping."
        else:
            detail = f"Available nodes: {available}"

        console.print(
            f"[red]Sweep failed:[/red] Invalid node name in sweep: {', '.join(missing)}. {detail}"
        )
        raise typer.Exit(1)

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

    def _render_status_view(net) -> None:
        if not net.nodes:
            console.print(Panel("No nodes in network", title="Network Status", border_style="yellow"))
        else:
            nodes_table = Table(title=f"Nodes ({len(net.nodes)})")
            nodes_table.add_column("Name", style="cyan")
            nodes_table.add_column("Type")
            nodes_table.add_column("Position")
            nodes_table.add_column("Details")

            for name, node in net.nodes.items():
                pos = tuple(float(v) for v in node.pos[:3])
                details: List[str] = []
                if hasattr(node, "freq"):
                    freq_ghz = float(node.freq) / 1e9 if node.freq else 0.0
                    details.append(f"freq={freq_ghz:.2f} GHz")
                if hasattr(node, "bandwidth_MHz"):
                    bw = float(node.bandwidth_MHz) if node.bandwidth_MHz else 0.0
                    details.append(f"bw={bw:.1f} MHz")
                if hasattr(node, "power_dBm"):
                    details.append(f"power={float(node.power_dBm):.1f} dBm")
                if hasattr(node, "N"):
                    details.append(f"elements={int(node.N)}")
                    if hasattr(node, "bits"):
                        details.append(f"bits={int(node.bits)}")
                if hasattr(node, "noise_figure_dB"):
                    details.append(f"noise={float(node.noise_figure_dB):.1f} dB")
                if hasattr(node, "antenna_gain_dBi"):
                    details.append(f"gain={float(node.antenna_gain_dBi):.1f} dBi")

                nodes_table.add_row(
                    name,
                    _node_type(node),
                    f"({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})",
                    ", ".join(details),
                )

            console.print(nodes_table)

            node_names = list(net.nodes.keys())
            if len(node_names) > 1:
                distances = Table(title="Distances")
                distances.add_column("Pair", style="cyan")
                distances.add_column("Distance (m)", justify="right")
                for idx, node1_name in enumerate(node_names):
                    for node2_name in node_names[idx + 1:]:
                        node1 = net.nodes[node1_name]
                        node2 = net.nodes[node2_name]
                        distance = math.sqrt(
                            sum((float(a) - float(b)) ** 2 for a, b in zip(node1.pos[:3], node2.pos[:3]))
                        )
                        distances.add_row(f"{node1_name} ↔ {node2_name}", f"{distance:.2f}")
                console.print(distances)

        active_links = net.get_active_links()
        if not active_links:
            console.print(Panel("No active links", title="Active Links", border_style="yellow"))
        else:
            links_table = Table(title=f"Active Links ({len(active_links)})")
            links_table.add_column("#", justify="right")
            links_table.add_column("Link", style="cyan")
            links_table.add_column("Source")
            links_table.add_column("SNR (dB)", justify="right")
            links_table.add_column("Power (dBm)", justify="right")
            links_table.add_column("Gain (dBi)", justify="right")
            links_table.add_column("Deflection (deg)", justify="right")
            links_table.add_column("Quant Penalty (dB)", justify="right")

            for idx, (link_name, link_info) in enumerate(active_links.items(), start=1):
                origin = link_info.get("source", "unknown")
                origin_label = origin.capitalize() if isinstance(origin, str) else str(origin)
                steering = link_info.get("beam_angle_local")
                if steering is None:
                    steering = link_info.get("deflection_angle_deg")
                penalty = abs(float(link_info.get("quant_loss_dB", 0.0)))
                links_table.add_row(
                    str(idx),
                    link_name,
                    origin_label,
                    f"{float(link_info['snr_dB']):.2f}",
                    f"{float(link_info['pwr_dBm']):.2f}",
                    f"{float(link_info['gain_dBi']):.2f}",
                    "N/A" if steering is None else f"{float(steering):.2f}",
                    f"{penalty:.2f}",
                )

            console.print(links_table)

    def _render_links_view(net) -> None:
        active_links = net.get_active_links()
        if not active_links:
            console.print(Panel("No active links", title="Active Links", border_style="yellow"))
            return

        console.print(Panel(f"{len(active_links)} active link(s)", title="Active Links", border_style="cyan"))
        ordered_links = sorted(active_links.items(), key=lambda item: item[0].casefold())
        for idx, (link_name, link_info) in enumerate(ordered_links, start=1):
            origin = link_info.get("source", "unknown")
            origin_label = origin.capitalize() if isinstance(origin, str) else str(origin)
            steering = link_info.get("beam_angle_local")
            if steering is None:
                steering = link_info.get("deflection_angle_deg")
            penalty = abs(float(link_info.get("quant_loss_dB", 0.0)))
            details = Table.grid(padding=(0, 2))
            details.add_column(style="bold cyan")
            details.add_column()
            details.add_row("Source", origin_label)
            details.add_row("SNR (dB)", f"{float(link_info['snr_dB']):.2f}")
            details.add_row("Power (dBm)", f"{float(link_info['pwr_dBm']):.2f}")
            details.add_row("Gain (dBi)", f"{float(link_info['gain_dBi']):.2f}")
            details.add_row("Deflection (deg)", "N/A" if steering is None else f"{float(steering):.2f}")
            details.add_row("Quant Penalty (dB)", f"{penalty:.2f}")
            console.print(Panel(details, title=f"[{idx}] {link_name}", border_style="cyan"))

    def _node_style(node) -> str:
        node_type = _node_type(node)
        if node_type == "AccessPoint":
            return "bold blue"
        if node_type == "RIS":
            return "bold yellow"
        if node_type == "UE":
            return "bold green"
        return "bold white"

    def _build_ascii_topology_data(net):
        if not net.nodes:
            return {
                "legend": [],
                "lines": ["Network is empty"],
            }

        positions = {name: node.pos for name, node in net.nodes.items()}
        xs = [float(pos[0]) for pos in positions.values()]
        ys = [float(pos[1]) for pos in positions.values()]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        x_range = max(x_max - x_min, 1.0)
        y_range = max(y_max - y_min, 1.0)

        x_min -= x_range * 0.1
        x_max += x_range * 0.1
        y_min -= y_range * 0.1
        y_max += y_range * 0.1

        x_range = x_max - x_min
        y_range = y_max - y_min

        width, height = 50, 20
        x_scale = (width - 2) / x_range if x_range > 0 else 1
        y_scale = (height - 2) / y_range if y_range > 0 else 1

        char_pool = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        name_to_char: Dict[str, str] = {}
        for idx, name in enumerate(sorted(net.nodes.keys())):
            name_to_char[name] = char_pool[idx] if idx < len(char_pool) else "?"

        grid = [[None for _ in range(width)] for _ in range(height)]
        for name, pos in positions.items():
            x_char = int((float(pos[0]) - x_min) * x_scale + 1)
            y_char = int((y_max - float(pos[1])) * y_scale + 1)
            x_char = max(1, min(x_char, width - 2))
            y_char = max(1, min(y_char, height - 2))
            grid[y_char][x_char] = name

        lines = ["Topology View (ASCII):", "=" * 52, "-" * 52]

        for row in grid:
            lines.append(row)

        lines.append("-" * 52)
        legend = [
            {
                "symbol": name_to_char[name],
                "name": name,
                "style": _node_style(net.nodes[name]),
            }
            for name in sorted(net.nodes.keys())
        ]
        return {
            "legend": legend,
            "lines": lines,
            "name_to_char": name_to_char,
        }

    def _render_list_view(net) -> None:
        topology = _build_ascii_topology_data(net)
        ascii_text = Text()
        lines = topology["lines"]
        for idx, line in enumerate(lines):
            if isinstance(line, str):
                style = "cyan" if line.startswith("=") or line.startswith("-") else None
                ascii_text.append(line, style=style)
            else:
                ascii_text.append("| ", style="cyan")
                for cell in line:
                    if cell is None:
                        ascii_text.append(".", style="dim")
                    else:
                        ascii_text.append(topology["name_to_char"][cell], style=_node_style(net.nodes[cell]))
                ascii_text.append(" |", style="cyan")
            if idx != len(lines) - 1:
                ascii_text.append("\n")
        console.print(Panel(ascii_text, title="List Output", border_style="cyan"))

        if topology["legend"]:
            legend = Text("Legend: ", style="bold")
            for idx, entry in enumerate(topology["legend"]):
                if idx:
                    legend.append("  ")
                legend.append(entry["symbol"], style=entry["style"])
                legend.append("=")
                legend.append(entry["name"], style=entry["style"])
            console.print(Panel(legend, title="Topology Legend", border_style="cyan"))

        coords = Table(title="Node Coordinates")
        coords.add_column("Name", style="cyan")
        coords.add_column("Type")
        coords.add_column("Position (x, y, z)", justify="right")
        for name in sorted(net.nodes.keys()):
            node = net.nodes[name]
            pos = tuple(float(v) for v in node.pos[:3])
            coords.add_row(
                name,
                _node_type(node),
                f"({pos[0]:6.2f}, {pos[1]:6.2f}, {pos[2]:6.2f})",
            )

        if not net.nodes:
            coords.add_row("-", "empty", "-")

        console.print(coords)

    def _render_connect_result(
        net,
        ap: str,
        ris: str,
        ue: str,
        result: dict,
        *,
        requested_angle_deg: Optional[float] = None,
        enable_feedback: bool = True,
        use_waveform: bool = True,
        modulation: str = "QPSK",
        seed: Optional[int] = None,
    ) -> None:
        ap_node = net.get(ap)
        ris_node = net.get(ris)
        ue_node = net.get(ue)

        def _fmt_pos(node) -> str:
            if node is None or not hasattr(node, "pos"):
                return "N/A"
            pos = tuple(float(v) for v in node.pos[:3])
            return f"({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"

        def _distance(a, b) -> Optional[float]:
            if a is None or b is None or not hasattr(a, "pos") or not hasattr(b, "pos"):
                return None
            deltas = [float(x) - float(y) for x, y in zip(a.pos[:3], b.pos[:3])]
            return math.sqrt(sum(delta * delta for delta in deltas))

        context = Table.grid(padding=(0, 2))
        context.add_column(style="bold cyan")
        context.add_column()
        context.add_row("AP", ap)
        context.add_row("RIS", ris)
        context.add_row("UE", ue)
        context.add_row("Feedback", "adaptive" if enable_feedback else "single-shot")
        context.add_row("Waveform", modulation if use_waveform else "disabled")
        context.add_row("Seed", "auto" if seed is None else str(seed))
        if result.get("channel_model_requested") is not None:
            context.add_row("Engine requested", str(result["channel_model_requested"]))
        if result.get("channel_model_used") is not None:
            context.add_row("Engine used", str(result["channel_model_used"]))
        if result.get("channel_model_fallback_reason"):
            context.add_row("Engine fallback", str(result["channel_model_fallback_reason"]))
        console.print(Panel(context, title="Connect Context", expand=False))

        geometry = Table(title="Connect Diagnostics")
        geometry.add_column("Metric", style="cyan")
        geometry.add_column("Value", justify="right")
        geometry.add_row("AP position", _fmt_pos(ap_node))
        geometry.add_row("RIS position", _fmt_pos(ris_node))
        geometry.add_row("UE position", _fmt_pos(ue_node))

        d_ap_ris = _distance(ap_node, ris_node)
        d_ris_ue = _distance(ris_node, ue_node)
        if d_ap_ris is not None:
            geometry.add_row("AP→RIS distance (m)", f"{d_ap_ris:.3f}")
        if d_ris_ue is not None:
            geometry.add_row("RIS→UE distance (m)", f"{d_ris_ue:.3f}")

        if requested_angle_deg is not None:
            geometry.add_row("Requested angle (deg)", f"{requested_angle_deg:.3f}")
        if result.get("incident_azimuth_deg") is not None:
            geometry.add_row("Incident azimuth (deg)", f"{float(result['incident_azimuth_deg']):.3f}")
        if result.get("reflected_azimuth_deg") is not None:
            geometry.add_row("Reflected azimuth (deg)", f"{float(result['reflected_azimuth_deg']):.3f}")
        if result.get("deflection_angle_deg") is not None:
            geometry.add_row("RIS deflection (deg)", f"{float(result['deflection_angle_deg']):.3f}")
        elif result.get("local_deflection_deg") is not None:
            geometry.add_row("RIS deflection (deg)", f"{float(result['local_deflection_deg']):.3f}")
        if result.get("max_angle_deg") is not None:
            geometry.add_row("RIS FOV limit (deg)", f"±{float(result['max_angle_deg']):.3f}")
        if result.get("fov_clamped") is not None:
            geometry.add_row("FOV clamped", "yes" if result.get("fov_clamped") else "no")
        console.print(geometry)

        table = Table(title="Link Result")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        value_keys = (
            ("snr_dB", "snr_dB"),
            ("pwr_dBm", "pwr_dBm"),
            ("rssi_dBm", "rssi_dBm"),
            ("beam_angle_deg", "beam_angle_deg"),
            ("beam_angle", "beam_angle_deg"),
            ("gain_dBi", "gain_dBi"),
            ("quant_loss_dB", "quant_loss_dB"),
        )
        seen = set()
        for source_key, label in value_keys:
            if source_key in result and label not in seen and result[source_key] is not None:
                table.add_row(label, f"{float(result[source_key]):.3f}")
                seen.add(label)
        console.print(table)

        recommendation = Table.grid(padding=(0, 2))
        recommendation.add_column(style="bold cyan")
        recommendation.add_column()
        steering = result.get("deflection_angle_deg")
        if steering is None:
            steering = result.get("local_deflection_deg")
        recommendation.add_row(
            "Steering command",
            "N/A" if steering is None else f"{float(steering):.3f}° local deflection",
        )
        recommendation.add_row(
            "Expected SNR",
            "N/A" if result.get("snr_dB") is None else f"{float(result['snr_dB']):.3f} dB",
        )
        if result.get("fov_clamped"):
            recommendation.add_row("Constraint", "Requested path exceeds RIS hardware FOV")
        console.print(Panel(recommendation, title="RIS Recommendation", expand=False))

    def _resolve_sweep_metrics(result: dict) -> dict:
        coarse_angles = list(result.get("local_coarse", []) or [])
        coarse_snrs = list(result.get("snr_coarse", []) or [])
        fine_angles = list(result.get("local_fine", []) or [])
        fine_snrs = list(result.get("snr_fine", []) or [])

        best_angle = (
            result.get("best_local_fine")
            if result.get("best_local_fine") is not None
            else result.get("best_local_angle_deg")
            if result.get("best_local_angle_deg") is not None
            else result.get("best_local")
            if result.get("best_local") is not None
            else result.get("best_angle_deg")
            if result.get("best_angle_deg") is not None
            else result.get("best_angle")
        )
        best_snr = (
            result.get("best_snr_fine")
            if result.get("best_snr_fine") is not None
            else result.get("best_snr_db")
            if result.get("best_snr_db") is not None
            else result.get("best_snr_dB")
            if result.get("best_snr_dB") is not None
            else result.get("best_snr")
        )

        rows = []
        for phase_name, angles, snrs in (
            ("coarse", coarse_angles, coarse_snrs),
            ("fine", fine_angles, fine_snrs),
        ):
            for idx, (angle, snr) in enumerate(zip(angles, snrs), start=1):
                try:
                    rows.append(
                        {
                            "phase": phase_name,
                            "index": idx,
                            "angle_deg": float(angle),
                            "snr_dB": float(snr),
                        }
                    )
                except (TypeError, ValueError):
                    continue

        if rows:
            rows.sort(key=lambda row: row["snr_dB"], reverse=True)

        return {
            "best_angle_deg": float(best_angle) if best_angle is not None else None,
            "best_snr_dB": float(best_snr) if best_snr is not None else None,
            "coarse_count": len(coarse_snrs),
            "fine_count": len(fine_snrs),
            "top_measurements": rows,
        }

    def _render_sweep_result(result: dict, algo: str, topk: int) -> None:
        summary = _resolve_sweep_metrics(result)

        table = Table(title=f"Sweep Result ({algo})")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right")
        table.add_row("Best angle (deg)", "N/A" if summary["best_angle_deg"] is None else f"{summary['best_angle_deg']:.2f}")
        table.add_row("Best SNR (dB)", "N/A" if summary["best_snr_dB"] is None else f"{summary['best_snr_dB']:.2f}")
        table.add_row("Coarse angles tested", str(summary["coarse_count"]))
        table.add_row("Fine angles tested", str(summary["fine_count"]))
        console.print(table)

        top_rows = summary["top_measurements"][:max(topk, 0)]
        if not top_rows:
            return

        top_table = Table(title=f"Top {len(top_rows)} Sweep Measurements")
        top_table.add_column("Rank", justify="right")
        top_table.add_column("Phase", style="cyan")
        top_table.add_column("Angle (deg)", justify="right")
        top_table.add_column("SNR (dB)", justify="right")

        for rank, row in enumerate(top_rows, start=1):
            top_table.add_row(
                str(rank),
                row["phase"],
                f"{row['angle_deg']:.2f}",
                f"{row['snr_dB']:.2f}",
            )
        console.print(top_table)

    def _print_shell_help() -> None:
        help_table = Table(title="Waveflow UI Shell")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description")
        help_table.add_row("status, list", "Show the current in-memory network.")
        help_table.add_row("add, connect, sweep", "Run native Typer/Rich commands against the current shell state.")
        help_table.add_row("env, ap, ris, ue", "Inspect or mutate environment and node settings.")
        help_table.add_row("signal, stream", "Run detailed signal inspection and payload streaming workflows.")
        help_table.add_row("save, load, clear", "Persist or mutate the current shell state.")
        help_table.add_row("links, plot, run", "Delegate through the established legacy handler when needed.")
        help_table.add_row("help [command]", "Show shell help or Typer help for a subcommand.")
        help_table.add_row("quit, exit", "Leave the shell.")
        console.print(help_table)
        console.print("[dim]Unknown commands are forwarded to the legacy interactive handler on the same network state.[/dim]")

    def _legacy_panel_title(command_name: str) -> str:
        return f"{command_name.replace('-', ' ').title()} Output"

    def _render_legacy_output(command_name: str, output: str) -> None:
        body = (output or "").strip("\n")
        renderable = Text.from_ansi(body) if body else Text("(no output)", style="dim")
        console.print(Panel(renderable, title=_legacy_panel_title(command_name), border_style="cyan"))

    def _invoke_legacy_shell_command(command_name: str, args: List[str], topology: Optional[Path] = None):
        cli = _resolve_context_legacy_shell(topology)
        cmd_str = " ".join([command_name, *args]).strip()
        buffer = io.StringIO()
        try:
            with redirect_stdout(buffer):
                should_exit = bool(cli.onecmd(cmd_str))
        except Exception as exc:
            console.print(f"[red]{command_name} failed:[/red] {exc}")
            raise typer.Exit(1)
        return should_exit, buffer.getvalue()

    def _run_legacy_shell_command(command_name: str, args: List[str], topology: Optional[Path] = None) -> None:
        _, output = _invoke_legacy_shell_command(command_name, args, topology)
        _render_legacy_output(command_name, output)

    def _render_live_sweep_frame(state: Dict[str, object]):
        layout = Table.grid(expand=False)
        layout.add_row(
            Panel.fit(
                state["progress"],
                title="Live Sweep",
                border_style="cyan",
            )
        )

        status = Table(title="Sweep Status")
        status.add_column("Metric", style="cyan")
        status.add_column("Value", justify="right")
        status.add_row("Algorithm", str(state.get("algorithm", "N/A")))
        status.add_row("Phase", str(state.get("phase", "pending")))
        status.add_row(
            "Current angle (deg)",
            "N/A" if state.get("current_angle_deg") is None else f"{float(state['current_angle_deg']):.2f}",
        )
        status.add_row(
            "Current SNR (dB)",
            "N/A" if state.get("current_snr_dB") is None else f"{float(state['current_snr_dB']):.2f}",
        )
        status.add_row(
            "Best angle (deg)",
            "N/A" if state.get("best_angle_deg") is None else f"{float(state['best_angle_deg']):.2f}",
        )
        status.add_row(
            "Best SNR (dB)",
            "N/A" if state.get("best_snr_dB") is None else f"{float(state['best_snr_dB']):.2f}",
        )
        layout.add_row(status)

        recent = Table(title="Recent Measurements")
        recent.add_column("Phase", style="cyan")
        recent.add_column("Angle (deg)", justify="right")
        recent.add_column("SNR (dB)", justify="right")
        for row in state.get("recent_rows", []):
            recent.add_row(row["phase"], row["angle"], row["snr"])
        layout.add_row(recent)
        return layout

    def _build_live_sweep_callback(algo: str):
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[phase]}[/bold blue]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        )
        task_id = progress.add_task("sweep", total=1, completed=0, phase="pending")
        state: Dict[str, object] = {
            "algorithm": algo,
            "phase": "pending",
            "current_angle_deg": None,
            "current_snr_dB": None,
            "best_angle_deg": None,
            "best_snr_dB": None,
            "recent_rows": [],
            "progress": progress,
            "progress_total": 1,
            "progress_completed": 0,
        }

        def callback(*, event: str, algorithm: str, **payload) -> None:
            phase = str(payload.get("phase", state["phase"]))
            state["algorithm"] = algorithm
            state["phase"] = phase
            if payload.get("local_angle_deg") is not None:
                state["current_angle_deg"] = float(payload["local_angle_deg"])
            if payload.get("snr_dB") is not None:
                state["current_snr_dB"] = float(payload["snr_dB"])
            if payload.get("best_angle_deg") is not None:
                state["best_angle_deg"] = float(payload["best_angle_deg"])
            if payload.get("best_snr_dB") is not None:
                state["best_snr_dB"] = float(payload["best_snr_dB"])

            total = max(int(payload.get("total", state["progress_total"])), 1)
            completed = int(payload.get("completed", state["progress_completed"]))
            state["progress_total"] = total
            state["progress_completed"] = completed
            progress.update(task_id, total=total, completed=completed, phase=phase)

            if event == "measurement":
                rows = list(state["recent_rows"])
                rows.insert(
                    0,
                    {
                        "phase": phase,
                        "angle": "N/A" if payload.get("local_angle_deg") is None else f"{float(payload['local_angle_deg']):.2f}",
                        "snr": "N/A" if payload.get("snr_dB") is None else f"{float(payload['snr_dB']):.2f}",
                    },
                )
                state["recent_rows"] = rows[:5]

        return progress, state, callback

    # -------------------------------------------------------------------------
    # env / ap / ris / ue
    # -------------------------------------------------------------------------

    @app.command("env", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def env_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before inspecting or modifying the environment.",
        ),
    ) -> None:
        """Inspect or update environment bounds through the established shell workflow."""
        _run_legacy_shell_command("env", list(ctx.args), topology)

    @app.command("ap", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def ap_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before inspecting or modifying AP settings.",
        ),
    ) -> None:
        """Inspect or update AP settings."""
        _run_legacy_shell_command("ap", list(ctx.args), topology)

    @app.command("ris", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def ris_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before inspecting or modifying RIS settings.",
        ),
    ) -> None:
        """Inspect or update RIS settings."""
        _run_legacy_shell_command("ris", list(ctx.args), topology)

    @app.command("ue", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def ue_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before inspecting or modifying UE settings.",
        ),
    ) -> None:
        """Inspect or update UE settings."""
        _run_legacy_shell_command("ue", list(ctx.args), topology)

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
        net = _resolve_context_net(topology)
        _render_status_view(net)

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
        net = _resolve_context_net(topology)
        _render_list_view(net)

    # -------------------------------------------------------------------------
    # add
    # -------------------------------------------------------------------------

    @app.command("add", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def add(
        ctx: typer.Context,
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
        net = _resolve_context_net(topology)
        topology_helper = _new_topology_helper(net)

        t = node_type.lower()
        auto_name = name
        if t == "random":
            import numpy as np

            parts = ([name] if name is not None else []) + list(ctx.args)
            num_ap = 1
            num_ris = 1
            num_ue = 1
            distance_range = (5.0, 7.0)

            idx = 0
            try:
                if idx < len(parts) and not parts[idx].startswith("--"):
                    num_ap = int(parts[idx])
                    idx += 1
                if idx < len(parts) and not parts[idx].startswith("--"):
                    num_ris = int(parts[idx])
                    idx += 1
                if idx < len(parts) and not parts[idx].startswith("--"):
                    num_ue = int(parts[idx])
                    idx += 1
            except ValueError as exc:
                console.print(f"[red]Invalid random-node count:[/red] {exc}")
                raise typer.Exit(1)

            while idx < len(parts):
                token = parts[idx]
                if token == "--distance" and idx + 1 < len(parts):
                    try:
                        min_dist, max_dist = map(float, parts[idx + 1].split("-"))
                    except (ValueError, IndexError):
                        console.print(
                            f"[red]Invalid distance format:[/red] {parts[idx + 1]}. Use min-max, e.g. 5-15."
                        )
                        raise typer.Exit(1)
                    distance_range = (min_dist, max_dist)
                    idx += 2
                    continue
                if token == "--no-ue":
                    num_ue = 0
                    idx += 1
                    continue
                console.print(f"[red]Unknown random add option:[/red] {token}")
                raise typer.Exit(1)

            if min(num_ap, num_ris, num_ue) < 0:
                console.print("[red]Node counts must be non-negative.[/red]")
                raise typer.Exit(1)
            if distance_range[0] < 0 or distance_range[1] < 0 or distance_range[0] > distance_range[1]:
                console.print("[red]Distance range must be positive and min <= max.[/red]")
                raise typer.Exit(1)

            ris_positions = []
            added = []
            for _ in range(num_ris):
                ris_name = topology_helper.generate_auto_name("ris")
                ris_x, ris_y = topology_helper.generate_position("ris")
                net.add_ris(ris_name, ris_x, ris_y, z, N=n, bits=bits)
                ris_positions.append((ris_name, ris_x, ris_y))
                added.append(ris_name)

            if num_ris > 0 and num_ap > 0:
                _, ris_x, ris_y = ris_positions[0]
                for _ in range(num_ap):
                    ap_distance = np.random.uniform(5.0, 15.0)
                    ap_angle_deg = np.random.uniform(-60.0, 60.0)
                    ap_angle_rad = np.radians(ap_angle_deg)
                    ap_x = ris_x + ap_distance * np.cos(ap_angle_rad)
                    ap_y = ris_y + ap_distance * np.sin(ap_angle_rad)
                    ap_name = topology_helper.generate_auto_name("ap")
                    net.add_ap(ap_name, ap_x, ap_y, z, power_dBm=power)
                    added.append(ap_name)
            else:
                for _ in range(num_ap):
                    ap_name = topology_helper.generate_auto_name("ap")
                    ap_x, ap_y = topology_helper.generate_position("ap")
                    net.add_ap(ap_name, ap_x, ap_y, z, power_dBm=power)
                    added.append(ap_name)

            for _ in range(num_ue):
                ue_name = topology_helper.generate_auto_name("ue")
                ue_x, ue_y = topology_helper.generate_position("ue", distance_range=distance_range)
                net.add_ue(ue_name, ue_x, ue_y, z)
                added.append(ue_name)

            console.print(
                "[green]Added random topology[/green] "
                f"({num_ap} AP, {num_ris} RIS, {num_ue} UE)"
            )
            if distance_range != (5.0, 7.0):
                console.print(
                    f"[cyan]UE distance range[/cyan] {distance_range[0]:.1f}m-{distance_range[1]:.1f}m"
                )
            console.print("[cyan]Nodes[/cyan] " + ", ".join(added) if added else "[cyan]Nodes[/cyan] none")
        elif t == "ap":
            if ctx.args:
                console.print(f"[red]Unexpected extra arguments for '{node_type}':[/red] {' '.join(ctx.args)}")
                raise typer.Exit(1)
            if auto_name is None:
                auto_name = f"AP{len([n for n in net.nodes if n.upper().startswith('AP')]) + 1}"
            net.add_ap(auto_name, x, y, z, power_dBm=power)
            console.print(f"[green]Added AP[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z})")
        elif t == "ris":
            if ctx.args:
                console.print(f"[red]Unexpected extra arguments for '{node_type}':[/red] {' '.join(ctx.args)}")
                raise typer.Exit(1)
            if auto_name is None:
                auto_name = f"R{len([n for n in net.nodes if n.upper().startswith('R')]) + 1}"
            net.add_ris(auto_name, x, y, z, N=n, bits=bits)
            console.print(f"[green]Added RIS[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z}) N={n} bits={bits}")
        elif t == "ue":
            if ctx.args:
                console.print(f"[red]Unexpected extra arguments for '{node_type}':[/red] {' '.join(ctx.args)}")
                raise typer.Exit(1)
            if auto_name is None:
                auto_name = f"UE{len([n for n in net.nodes if n.upper().startswith('UE')]) + 1}"
            net.add_ue(auto_name, x, y, z)
            console.print(f"[green]Added UE[/green] [cyan]{auto_name}[/cyan] at ({x}, {y}, {z})")
        else:
            console.print(f"[red]Unknown node type '{node_type}'. Use: ap, ris, ue, random[/red]")
            raise typer.Exit(1)

        _render_network(net)

    # -------------------------------------------------------------------------
    # connect
    # -------------------------------------------------------------------------

    @app.command("connect", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def connect(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before connecting.",
        ),
    ) -> None:
        """Run native connect with full legacy grammar compatibility."""
        from cli.connection_handler import ConnectionHandler
        from cli.helpers import sanitize_for_json

        net = _resolve_context_net(topology, with_controller=True)
        handler = ConnectionHandler(net)
        raw_parts = list(ctx.args)
        normalized_parts: List[str] = []
        beam_value: Optional[str] = None
        seed_value: Optional[str] = None

        idx = 0
        while idx < len(raw_parts):
            token = raw_parts[idx]
            if token == "--beam":
                if idx + 1 >= len(raw_parts):
                    console.print("[red]Missing value for --beam[/red]")
                    raise typer.Exit(1)
                beam_value = raw_parts[idx + 1]
                idx += 2
                continue
            if token == "--seed":
                if idx + 1 >= len(raw_parts):
                    console.print("[red]Missing value for --seed[/red]")
                    raise typer.Exit(1)
                seed_value = raw_parts[idx + 1]
                idx += 2
                continue
            normalized_parts.append(token)
            idx += 1

        if beam_value is not None:
            normalized_parts.append(beam_value)
        if seed_value is not None:
            normalized_parts.append(seed_value)

        arg = " ".join(normalized_parts)
        quiet_output: List[str] = []

        def _capture_print(*parts) -> None:
            if not parts:
                quiet_output.append("")
                return
            quiet_output.append(" ".join(str(part) for part in parts))

        ap, ris, ue, remaining_parts, error_msg = handler.parse_connect_arguments(arg)
        if error_msg:
            console.print(f"[red]{error_msg}[/red]")
            raise typer.Exit(1)

        flags_result = handler.parse_flags(remaining_parts)
        if flags_result["error_msg"]:
            console.print(f"[red]{flags_result['error_msg']}[/red]")
            raise typer.Exit(1)

        enable_feedback = flags_result["enable_feedback"]
        use_waveform = flags_result["use_waveform"]
        modulation = flags_result["modulation"]
        fov = flags_result["fov"]
        step = flags_result["step"]
        algo_name = flags_result["algo_name"]
        ml_predictor = flags_result["ml_predictor"]
        angle = flags_result["angle"]
        seed = flags_result["seed"]
        metric = flags_result.get("metric", "snr")
        enable_codebook_validation = flags_result["enable_codebook_validation"]
        codebook_increment = flags_result["codebook_increment"]
        codebook_neighbors = flags_result["codebook_neighbors"]
        include_predicted_angle = flags_result["include_predicted_angle"]
        codebook_start = flags_result["codebook_start"]
        codebook_end = flags_result["codebook_end"]
        codebook_step = flags_result["codebook_step"]
        use_mock = flags_result.get("use_mock", False)
        mock_trajectory = flags_result.get("mock_trajectory", "circular")
        r_cw = flags_result.get("r_cw", None)
        t_cw = flags_result.get("t_cw", None)
        tapering = flags_result.get("tapering", "uniform")
        channel_model = flags_result.get("channel_model")
        environment = flags_result.get("environment", "indoor")
        scenario = flags_result.get("scenario", 1)

        if fov is not None:
            out = handler.execute_sweep(
                ap,
                ris,
                ue,
                fov,
                step,
                algo_name,
                ml_predictor,
                enable_feedback,
                use_waveform,
                modulation,
                seed,
                metric=metric,
                enable_codebook_validation=enable_codebook_validation,
                codebook_increment=codebook_increment,
                codebook_neighbors=codebook_neighbors,
                include_predicted_angle=include_predicted_angle,
                codebook_start=codebook_start,
                codebook_end=codebook_end,
                codebook_step=codebook_step,
                use_mock=use_mock,
                mock_trajectory=mock_trajectory,
                r_cw=r_cw,
                t_cw=t_cw,
                tapering=tapering,
                print_func=_capture_print,
            )
            if out is None:
                if quiet_output:
                    console.print(f"[red]{quiet_output[-1]}[/red]")
                raise typer.Exit(1)
            try:
                best_angles_info = handler.print_sweep_results(
                    out,
                    fov,
                    step,
                    ap,
                    ris,
                    ue,
                    algo_name,
                    metric=metric,
                    print_func=lambda *args: None,
                )
                handler.create_sweep_record_and_link(
                    ap,
                    ris,
                    ue,
                    out,
                    best_angles_info,
                    fov,
                    step,
                    algo_name,
                    use_waveform,
                    modulation,
                )
                _render_sweep_result(out, algo_name, 5)
            except ValueError as exc:
                console.print(f"[red]Sweep failed:[/red] {exc}")
                raise typer.Exit(1)
            except Exception as exc:
                console.print(f"[red]Sweep failed:[/red] {exc}")
                raise typer.Exit(1)
            return

        res = handler.execute_single_connect(
            ap,
            ris,
            ue,
            angle,
            enable_feedback,
            use_waveform,
            modulation,
            seed,
            tapering=tapering,
            metric=metric,
            channel_model=channel_model,
            environment=environment,
            scenario=scenario,
            print_func=_capture_print,
        )
        if res is None:
            if quiet_output:
                console.print(f"[red]{quiet_output[-1]}[/red]")
            raise typer.Exit(1)

        _render_connect_result(
            net,
            ap,
            ris,
            ue,
            res,
            requested_angle_deg=angle,
            enable_feedback=enable_feedback,
            use_waveform=use_waveform,
            modulation=modulation,
            seed=seed,
        )
        connection_record = handler.create_connection_record(
            ap,
            ris,
            ue,
            res,
            angle,
            seed,
            enable_feedback,
            use_waveform,
            modulation,
        )
        net.last_connect_result = sanitize_for_json(connection_record)

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
        live: bool = typer.Option(True, "--live/--no-live", help="Render live Rich sweep progress when supported."),
        output_format: str = typer.Option("table", "--format", help="Output format: table or json."),
        topk: int = typer.Option(5, "--topk", min=0, help="Number of best sweep measurements to display in table mode."),
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before sweeping.",
        ),
    ) -> None:
        """Run a beam sweep and display the best angle and SNR."""
        from controller.beamsweeping import SweepAlgorithmLoader

        net = _resolve_context_net(topology, with_controller=True)
        _resolve_sweep_nodes_or_exit(net, ap, ris, ue)
        try:
            algorithm = SweepAlgorithmLoader.get_algorithm(algo, net)
            progress_callback = None
            if live and output_format == "table" and algo in {"linear", "coarse-fine"}:
                progress, state, progress_callback = _build_live_sweep_callback(algo)
                with Live(_render_live_sweep_frame(state), console=console, refresh_per_second=12) as live_display:
                    def live_callback(**payload):
                        progress_callback(**payload)
                        live_display.update(_render_live_sweep_frame(state))

                    result = algorithm.sweep(
                        ap,
                        ris,
                        ue,
                        fov=fov,
                        step=step,
                        seed=seed,
                        progress_callback=live_callback,
                    )
                    live_display.update(_render_live_sweep_frame(state))
            else:
                result = algorithm.sweep(
                    ap,
                    ris,
                    ue,
                    fov=fov,
                    step=step,
                    seed=seed,
                )
            if output_format == "json":
                console.print_json(
                    data={
                        "algorithm": algo,
                        "summary": _resolve_sweep_metrics(result),
                        "result": result,
                    }
                )
            elif output_format == "table":
                _render_sweep_result(result, algo, topk)
            else:
                console.print(f"[red]Unknown format '{output_format}'. Use: table, json[/red]")
                raise typer.Exit(1)
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
        net = _resolve_context_net(topology)
        path = filename or ".risnet_network.json"
        NetworkIO().save(net, path)
        console.print(f"[green]Saved[/green] → {path}")

    @app.command("load")
    def load(
        filepath: str = typer.Argument(..., help="Path to saved network JSON."),
    ) -> None:
        """Load network state from disk and display it."""
        from cli.helpers import NetworkIO
        net = _resolve_context_net(None)
        NetworkIO().load(net, filepath)
        console.print(f"[green]Loaded[/green] ← {filepath}")
        _render_network(net)

    # -------------------------------------------------------------------------
    # signal / stream
    # -------------------------------------------------------------------------

    @app.command("signal", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def signal_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before running signal inspection.",
        ),
    ) -> None:
        """Inspect signal metrics and per-hop breakdowns through the established workflow."""
        _run_legacy_shell_command("signal", list(ctx.args), topology)

    @app.command("stream", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def stream_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before running payload streaming.",
        ),
    ) -> None:
        """Run payload streaming through the established waveform workflow."""
        _run_legacy_shell_command("stream", list(ctx.args), topology)

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
        net = _resolve_context_net(topology)
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
    # links
    # -------------------------------------------------------------------------

    @app.command("links", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def links_cmd(
        ctx: typer.Context,
        topology: Optional[Path] = typer.Option(
            None, "--topology", "-t",
            exists=True, file_okay=True, dir_okay=False, readable=True,
            help="Load topology before inspecting links.",
        ),
    ) -> None:
        """Show active links or forward `links plot ...` to the legacy handler."""
        args = list(ctx.args)
        if args and args[0] == "plot":
            _run_legacy_shell_command("links", args, topology)
            return

        net = _resolve_context_net(topology)
        _render_links_view(net)

    # -------------------------------------------------------------------------
    # plot
    # -------------------------------------------------------------------------

    @app.command("plot", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def plot_cmd(
        ctx: typer.Context,
    ) -> None:
        """Plot saved sweep/connect results through the established legacy handler."""
        _run_legacy_shell_command("plot", list(ctx.args))

    # -------------------------------------------------------------------------
    # demo-connect
    # -------------------------------------------------------------------------

    @app.command("demo-connect")
    def demo_connect(
        seed: int = typer.Option(42, "--seed", help="Seed for deterministic channel evaluation."),
        channel_model: str = typer.Option("lightris", "--channel-model", help="Official channel engine: lightris or simris."),
        environment: str = typer.Option("indoor", "--environment", help="SimRIS environment when channel-model=simris."),
        scenario: int = typer.Option(1, "--scenario", help="SimRIS scenario when channel-model=simris."),
        ap_x: float = typer.Option(0.0, "--ap-x", help="AP x position."),
        ap_y: float = typer.Option(0.0, "--ap-y", help="AP y position."),
        ris_x: float = typer.Option(5.0, "--ris-x", help="RIS x position."),
        ris_y: float = typer.Option(0.0, "--ris-y", help="RIS y position."),
        ue_x: float = typer.Option(10.0, "--ue-x", help="UE x position."),
        ue_y: float = typer.Option(0.0, "--ue-y", help="UE y position."),
    ) -> None:
        """Run a deterministic AP-RIS-UE demo link and print metrics."""
        net = _new_network()
        net.add_ap("ap1", ap_x, ap_y)
        net.add_ris("ris1", ris_x, ris_y, max_angle_deg=180)
        net.add_ue("ue1", ue_x, ue_y)

        result = net.connect(
            "ap1",
            "ris1",
            "ue1",
            seed=seed,
            use_get_snr=False,
            store_in_active_links=False,
            channel_model=channel_model,
            environment=environment,
            scenario=scenario,
        )

        _render_network(net)

        metrics = Table(title="Link Metrics")
        metrics.add_column("Metric", style="cyan")
        metrics.add_column("Value", justify="right")
        metrics.add_row("channel_model_requested", str(result.get("channel_model_requested")))
        metrics.add_row("channel_model_used", str(result.get("channel_model_used")))
        if result.get("channel_model_fallback_reason"):
            metrics.add_row("channel_model_fallback_reason", str(result.get("channel_model_fallback_reason")))
        for key in ("snr_dB", "pwr_dBm", "rssi_dBm", "gain_dBi", "quant_loss_dB", "beam_angle"):
            metrics.add_row(key, f"{float(result[key]):.3f}")
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
    # testphysics
    # -------------------------------------------------------------------------

    @app.command("testphysics")
    def testphysics() -> None:
        """Run the physics model validation suite and display results."""
        from cli.physics_suite import run_testphysics

        results = run_testphysics()
        for section in results.sections:
            icon = "✓" if section.passed else "✗"
            style = "bold green" if section.passed else "bold red"
            console.rule(f"[{style}]{icon} {section.title}[/{style}]")
            for check in section.checks:
                colour = "green" if check.passed else "red"
                console.print(f"  [{colour}]{'✓' if check.passed else '✗'}[/{colour}] {check.name}: {check.detail}")
            for line in section.extra_lines:
                console.print(line)

        if results.all_passed:
            console.print("\n[bold green]✓ All physics checks passed![/bold green]")
        else:
            console.print("\n[bold red]✗ Some checks FAILED — see above.[/bold red]")
            raise SystemExit(1)

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
        net = _new_network_with_controller()
        cli = _new_legacy_shell(net=net)
        if topology is not None:
            cli._load_network_from_file(str(topology))

        interactive_context["net"] = net
        interactive_context["legacy_cli"] = cli
        console.print("[bold cyan]Opening Waveflow UI shell.[/bold cyan] Type `help` for commands.")
        console.print("[dim]Native commands keep shell state in memory; unsupported commands fall back to the legacy handler.[/dim]")
        try:
            while True:
                try:
                    line = console.input("[bold cyan]waveflow[/bold cyan][white] ui[/white][dim]> [/dim]")
                except EOFError:
                    console.print()
                    break
                except KeyboardInterrupt:
                    console.print("\n[yellow]Use `quit` or `exit` to leave the shell.[/yellow]")
                    continue

                stripped = line.strip()
                if not stripped:
                    continue
                if stripped in {"quit", "exit"}:
                    break
                if stripped in {"help", "?"}:
                    _print_shell_help()
                    continue

                try:
                    tokens = shlex.split(stripped)
                except ValueError as exc:
                    console.print(f"[red]Parse failed:[/red] {exc}")
                    continue

                if not tokens:
                    continue
                if tokens[0] == "shell":
                    console.print("[yellow]Already inside `waveflow ui shell`.[/yellow]")
                    continue
                if tokens[0] == "help":
                    if len(tokens) == 1:
                        _print_shell_help()
                    else:
                        try:
                            app(args=[tokens[1], "--help"], prog_name="waveflow ui")
                        except SystemExit:
                            pass
                    continue

                try:
                    app(args=tokens, prog_name="waveflow ui")
                except SystemExit as exc:
                    code = int(exc.code or 0)
                    if code == 0:
                        continue
                    try:
                        should_exit, output = _invoke_legacy_shell_command(tokens[0], tokens[1:])
                    except Exception as legacy_exc:
                        console.print(f"[red]Command failed:[/red] {legacy_exc}")
                    else:
                        _render_legacy_output(tokens[0], output)
                        if should_exit:
                            break
        finally:
            interactive_context["net"] = None
            interactive_context["legacy_cli"] = None

    # -------------------------------------------------------------------------
    # run  — delegate any legacy command verbatim
    # -------------------------------------------------------------------------

    @app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def run_cmd(
        ctx: typer.Context,
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
        passthrough = list(command) + list(ctx.args)
        if not passthrough:
            console.print("[red]Command failed:[/red] Missing legacy command.")
            raise typer.Exit(1)
        _run_legacy_shell_command(passthrough[0], passthrough[1:], topology)

    args = list(argv or [])
    if not args:
        args = ["shell"]

    try:
        app(args=args, prog_name="waveflow ui")
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0
