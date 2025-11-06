#!/usr/bin/env python3
"""
Test script for the new enhanced CLI with node access
"""

from risnet import RISnet
from risnet_cli import RISnetCLI
import sys

def test_cli_commands():
    """Test the new CLI with programmatic commands"""
    net = RISnet()
    cli = RISnetCLI(net)

    # Simulate CLI commands
    commands = [
        "add ap ap1 0 0",
        "add ris ris1 5 0 N=16 bits=2",
        "add ue ue1 10 3",
        "list",
        "ap1 info",
        "ris1 info",
        "ue1 info",
        "ap1 ping ue1",
        "ap1 iperf ue1",
        "ap1 findpaths ue1 dijkstra",
        "ap1 connect ris1 ue1",
    ]

    print("Running CLI command tests...\n")

    for cmd in commands:
        print(f"\n{'='*60}")
        print(f"Command: {cmd}")
        print(f"{'='*60}")
        try:
            cli.onecmd(cmd)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n\nAll tests completed!")


if __name__ == '__main__':
    test_cli_commands()
