"""Command-line entry point for the installed package."""

import argparse
import sys


def _run_terminal(argv=None):
    from risnet.terminal_cli import run

    return run(list(argv or []))


def _run_web(net, controller, host="127.0.0.1", port=5000):
    from app import create_app
    from app.state_manager import WebStateManager
    from app.thread_safe_network import ThreadSafeController, ThreadSafeNetwork
    from waitress import serve as waitress_serve

    net_safe = ThreadSafeNetwork(net)
    controller_safe = ThreadSafeController(controller)

    state_mgr = WebStateManager()

    app = create_app(net_safe, controller_safe, state_mgr)

    print("Using Waitress WSGI server (production-ready)")
    print(f"Server running on http://{host}:{port}")
    print("Press Ctrl+C to quit")

    waitress_serve(app, host=host, port=port, threads=4)


def main(argv=None):
    """Run the Waveflow CLI or web interface."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv and raw_argv[0] == "ui":
        return _run_terminal(raw_argv[1:])

    parser = argparse.ArgumentParser(
        description="Waveflow v2.0 Advanced Wireless and RIS Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  waveflow --web                          # Run web interface
  waveflow --cli                          # Run CLI interface (default)
  waveflow --terminal status              # Run modern Typer/Rich terminal status
  waveflow ui demo-connect                # Run modern Typer/Rich demo link
  waveflow --cli --topology topology.json # Load topology on startup
  waveflow testall --exec-only            # Run testall and exit
        """,
    )
    parser.add_argument("--web", action="store_true", help="Run web interface")
    parser.add_argument("--cli", action="store_true", help="Run CLI interface (default)")
    parser.add_argument("--terminal", action="store_true", help="Run Typer/Rich terminal commands")
    parser.add_argument("--topology", type=str, help="Load topology from JSON file")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument(
        "--exec-only",
        action="store_true",
        help="Execute command(s) and exit without starting interactive CLI",
    )
    parser.add_argument("command", nargs="*", help="CLI command to execute")
    args = parser.parse_args(raw_argv)

    if args.terminal:
        if args.web:
            parser.error("--terminal cannot be combined with --web")
        return _run_terminal(args.command)

    from controller.ris_controller import RISController
    from core import RISNetwork

    net = RISNetwork()
    controller = RISController(net, net.environment)
    net.set_controller(controller)

    if args.web:
        print("\n" + "=" * 70)
        print("Waveflow v2.0 - Web Interface")
        print("=" * 70 + "\n")
        _run_web(net, controller, host=args.host, port=args.port)
        return 0

    print("\n" + "=" * 70)
    print("Waveflow v2.0 - CLI Interface")
    print("=" * 70 + "\n")

    from cli.main_shell import RISNetCLI

    cli = RISNetCLI(net)

    if args.topology:
        cli._load_network_from_file(args.topology)
        print(f"Topology loaded: {args.topology}\n")

    if args.command:
        command_str = " ".join(args.command)
        try:
            exit_requested = bool(cli.onecmd(command_str))
        except Exception as exc:
            print(f"Error: {exc}")
            return 1

        if args.exec_only or exit_requested:
            return 0

        print("\n" + "-" * 70)
        print("Continuing in interactive CLI (type 'help' for commands, 'quit' to exit)")
        print("-" * 70 + "\n")

    cli.cmdloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
