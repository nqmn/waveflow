#!/usr/bin/env python3
"""
Example: Interactive CLI with Direct Node Access

This example shows how to use the RISNet CLI for interactive network simulation.
Run this to launch an interactive CLI where you can:
  - Add nodes (AP, RIS, UE)
  - Access nodes directly by name
  - Run connectivity and performance tests
  - Find optimal paths

Usage:
    python3 example_interactive_cli.py
"""

from risnet import RISnet
from risnet_cli import RISnetCLI


def main():
    """Launch interactive CLI"""
    print("""
╔════════════════════════════════════════════════════════════╗
║     RISNet Interactive CLI - Node Access Example           ║
╚════════════════════════════════════════════════════════════╝

This CLI allows you to create nodes and access them directly
by name, just like accessing physical devices in a network.

QUICK START:
  1. Add nodes:
     risnet> add ap ap1 0 0
     risnet> add ris ris1 5 0
     risnet> add ue ue1 10 3

  2. List nodes:
     risnet> list

  3. Access nodes by name:
     risnet> ap1 info
     risnet> ap1 ping ue1
     risnet> ap1 iperf ue1
     risnet> ap1 findpaths ue1

  4. Advanced operations:
     risnet> ap1 connect ris1 ue1
     risnet> ap1 position 0 0 0

Type 'help' for all commands or 'exit' to quit.
    """)

    # Create network and launch CLI
    net = RISnet()
    cli = RISnetCLI(net)

    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\nExiting...")


if __name__ == '__main__':
    main()
