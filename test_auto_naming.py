#!/usr/bin/env python3
"""
Test auto-naming feature for CLI nodes
"""

from risnet import RISnet
from risnet_cli import RISnetCLI


def test_auto_naming():
    """Test auto-generated node names"""
    net = RISnet()
    cli = RISnetCLI(net)

    commands = [
        # Auto-named nodes (no explicit names)
        "add ap 0 0",
        "add ap 2 0",
        "add ap 4 0",
        "add ris 5 0",
        "add ris 8 0",
        "add ue 10 3",
        "add ue 12 3",
        "list",

        # Also test explicit names still work
        "add ap explicit_ap 6 1",
        "add ris explicit_ris 7 1",
        "add ue explicit_ue 8 1",
        "list",

        # Test node access with auto-names
        "AP1 info",
        "AP2 info",
        "R1 info",
        "UE1 info",
        "AP1 ping UE1",
    ]

    print("Testing auto-naming feature...\n")

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

    print("\n\nAuto-naming tests completed!")


if __name__ == '__main__':
    test_auto_naming()
