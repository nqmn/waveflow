"""User Equipment (UE) node interactive shell"""

import cmd


class UENodeShell(cmd.Cmd):
    """Interactive shell for UE node management"""

    def __init__(self, ue_node):
        super().__init__()
        self.ue_node = ue_node
        self.prompt = f"{ue_node.name}> "
        self.intro = f"\n{'='*60}\nUser Equipment Shell: {ue_node.name}\n{'='*60}\n"
        self._print_status()
        print("\nAvailable commands: help, status, info, signal, connect, exit")
        print("Type 'help' for more information\n")

    def do_help(self, arg):
        """help [command] - Show help"""
        if arg:
            return super().do_help(arg)

        help_text = """
User Equipment (UE) Commands:
  help              - Show this help message
  status            - Show current UE status
  info              - Show detailed UE information
  signal [ap]       - Check signal strength from AP
  connect [ap]      - Connect to Access Point
  exit              - Exit UE shell
        """
        print(help_text)

    def do_status(self, arg):
        """status - Show UE status"""
        self._print_status()

    def do_info(self, arg):
        """info - Show detailed UE information"""
        print(f"\n{self.ue_node.name} Information:")
        print(f"  Name:           {self.ue_node.name}")
        print(f"  Type:           User Equipment")
        print(f"  Position:       ({self.ue_node.pos[0]:.2f}, {self.ue_node.pos[1]:.2f}, {self.ue_node.pos[2]:.2f}) meters")
        print(f"  Antenna Type:   Omnidirectional")
        print(f"  Receiver Type:  Passive")
        print(f"  Frequency Band: 5 GHz (WiFi 5)")
        print(f"  Max Bandwidth:  160 MHz")
        print(f"  MIMO Streams:   2x2")

    def do_signal(self, arg):
        """signal [ap] - Check signal strength from AP"""
        if not arg:
            print(f"{self.ue_node.name} Signal Information: Not connected")
        else:
            ap_name = arg
            print(f"✓ Signal strength from {ap_name}: -45 dBm (Strong)")

    def do_connect(self, arg):
        """connect [ap] - Connect to Access Point"""
        if not arg:
            print(f"{self.ue_node.name} Connection Status: Not connected")
        else:
            ap_name = arg
            print(f"✓ Connected to {ap_name}")
            print(f"  SNR: 15.5 dB")
            print(f"  Data Rate: 150 Mbps")

    def do_exit(self, arg):
        """exit - Exit UE shell"""
        print(f"Exiting {self.ue_node.name} shell\n")
        return True

    def _print_status(self):
        """Print UE node status"""
        print(f"\n{self.ue_node.name} Status:")
        print(f"  Position:      ({self.ue_node.pos[0]:.2f}, {self.ue_node.pos[1]:.2f}, {self.ue_node.pos[2]:.2f})")
        print(f"  Connection:    Not connected")
        print(f"  Signal Strength: N/A")
        print(f"  SNR:           N/A dB")
        print(f"  Battery:       100%")
