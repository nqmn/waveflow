#!/usr/bin/env python3
"""
Test rename feature for all nodes
"""

from risnet import RISnet
from risnet_cli import RISnetCLI


def test_rename():
    """Test node rename functionality"""
    net = RISnet()
    cli = RISnetCLI(net)

    commands = [
        # Create nodes with auto-names
        "add ap 0 0",
        "add ris 5 0",
        "add ue 10 3",
        "list",

        # Test rename on AP
        "AP1 info",
        "AP1 rename access_point",
        "access_point info",
        "list",

        # Test rename on RIS
        "R1 rename relay_surface",
        "relay_surface info",
        "list",

        # Test rename on UE
        "UE1 rename user_device",
        "user_device info",
        "list",

        # Test commands work with renamed nodes
        "access_point ping user_device",
        "access_point findpaths user_device",
        "access_point connect relay_surface user_device",

        # Try invalid renames
        "access_point rename relay_surface",  # Should fail - already taken
        "access_point rename invalid@name",   # Should fail - invalid characters
    ]

    print("Testing rename feature...\n")

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

    print("\n\nRename tests completed!")


if __name__ == '__main__':
    test_rename()
