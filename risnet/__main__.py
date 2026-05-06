"""Command-line entry point for the installed ``risnet`` package."""

import argparse
import sys


def _run_web(net, controller, host="127.0.0.1", port=5000):
    from app import create_app
    from app.state_manager import WebStateManager
    from app.thread_safe_network import ThreadSafeController, ThreadSafeNetwork
    from waitress import serve as waitress_serve

    net_safe = ThreadSafeNetwork(net)
    controller_safe = ThreadSafeController(controller)

    state_mgr = WebStateManager()
    state_mgr.load_network(net_safe)

    app = create_app(net_safe, controller_safe, state_mgr)

    print("Using Waitress WSGI server (production-ready)")
    print(f"Server running on http://{host}:{port}")
    print("Press Ctrl+C to quit")

    waitress_serve(app, host=host, port=port, threads=4)


def main(argv=None):
    """Run the RISNet CLI or web interface."""
    parser = argparse.ArgumentParser(
        description="RISNet v2.0 Advanced RIS Network Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  risnet --web                          # Run web interface
  risnet --cli                          # Run CLI interface (default)
  risnet --cli --topology topology.json # Load topology on startup
  risnet testall --exec-only            # Run testall and exit
        """,
    )
    parser.add_argument("--web", action="store_true", help="Run web interface")
    parser.add_argument("--cli", action="store_true", help="Run CLI interface (default)")
    parser.add_argument("--topology", type=str, help="Load topology from JSON file")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Web server host")
    parser.add_argument("--port", type=int, default=5000, help="Web server port")
    parser.add_argument(
        "--exec-only",
        action="store_true",
        help="Execute command(s) and exit without starting interactive CLI",
    )
    parser.add_argument("command", nargs="*", help="CLI command to execute")
    args = parser.parse_args(argv)

    from controller.ris_controller import RISController
    from core import RISNetwork

    net = RISNetwork()
    controller = RISController(net, net.environment)
    net.set_controller(controller)

    if args.web:
        print("\n" + "=" * 70)
        print("RISNet v2.0 - Web Interface")
        print("=" * 70 + "\n")
        _run_web(net, controller, host=args.host, port=args.port)
        return 0

    print("\n" + "=" * 70)
    print("RISNet v2.0 - CLI Interface")
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
