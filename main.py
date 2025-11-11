#!/usr/bin/env python3
"""
RISNet v2.0 - Advanced RIS Network Simulator
Modular entry point with clean separation of concerns

Usage:
    python main.py --web        # Run web interface
    python main.py --cli        # Run CLI interface (default)
    python main.py --topology FILE  # Load topology on startup
"""

import sys
import argparse
from core import RISNetwork
from controller.ris_controller import RISController
from app import create_app
from cli.main_shell import RISNetCLI


def run_web(net, controller, host='127.0.0.1', port=5000):
    """Run WSGI web interface"""
    from waitress import serve as waitress_serve
    from app.thread_safe_network import ThreadSafeNetwork, ThreadSafeController
    from app.state_manager import WebStateManager
    import signal

    # Wrap with thread-safe versions for concurrent web access
    net_safe = ThreadSafeNetwork(net)
    controller_safe = ThreadSafeController(controller)

    # Initialize state manager for persistence
    state_mgr = WebStateManager()
    state_mgr.load_network(net_safe)

    app = create_app(net_safe, controller_safe, state_mgr)

    print(f'Using Waitress WSGI server (production-ready)')
    print(f'Server running on http://{host}:{port}')
    print('Press Ctrl+C to quit')

    # Handle graceful shutdown
    def shutdown_handler(signum, frame):
        print('\nShutting down gracefully...')
        # Save network state before exit
        if state_mgr:
            state_mgr.save_network(net_safe)
            print('✓ Network state saved')
        print('Exiting RISNet web server')
        sys.exit(0)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    waitress_serve(app, host=host, port=port, threads=4)


def cleanup_cli(net, cli):
    """Clean up CLI resources"""
    print('\nClearing topology...')
    if net.nodes:
        net.nodes.clear()
        cli._save_network()
        print('✓ Topology cleared')
    print('Exiting RISNet CLI')


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='RISNet v2.0 Advanced RIS Network Simulator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --web                          # Run web interface
  python main.py --cli                          # Run CLI interface (default)
  python main.py --cli --topology topology.json # Load topology on startup
  python main.py testall --exec-only            # Run testall and exit
        """
    )
    parser.add_argument('--web', action='store_true',
                        help='Run web interface')
    parser.add_argument('--cli', action='store_true',
                        help='Run CLI interface (default)')
    parser.add_argument('--topology', type=str,
                        help='Load topology from JSON file')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='Web server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Web server port (default: 5000)')
    parser.add_argument('--exec-only', action='store_true',
                        help='Execute command(s) and exit without starting interactive CLI')
    parser.add_argument('command', nargs='*',
                        help='CLI command to execute')
    args = parser.parse_args()

    # Initialize core components
    net = RISNetwork()
    controller = RISController(net, net.environment)
    net.set_controller(controller)

    # Run web interface
    if args.web:
        print("\n" + "="*70)
        print("RISNet v2.0 - Web Interface")
        print("="*70 + "\n")
        run_web(net, controller, host=args.host, port=args.port)
        return

    # Run CLI interface
    print("\n" + "="*70)
    print("RISNet v2.0 - CLI Interface")
    print("="*70 + "\n")

    cli = RISNetCLI(net)

    # Load topology if provided
    if args.topology:
        cli._load_network_from_file(args.topology)
        print(f"✓ Topology loaded: {args.topology}\n")

    try:
        # Execute command if provided
        if args.command:
            command_str = ' '.join(args.command)
            try:
                exit_requested = bool(cli.onecmd(command_str))
            except Exception as e:
                print(f"Error: {e}")
                exit_requested = True

            # Continue to interactive CLI unless --exec-only or exit was requested
            if not args.exec_only and not exit_requested:
                print("\n" + "-" * 70)
                print("Continuing in interactive CLI (type 'help' for commands, 'quit' to exit)")
                print("-" * 70 + "\n")
                cli.cmdloop()
        else:
            # Default to interactive CLI
            cli.cmdloop()
    except KeyboardInterrupt:
        cleanup_cli(net, cli)


if __name__ == '__main__':
    main()
