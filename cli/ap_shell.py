"""Access Point (AP) node interactive shell"""

import cmd


class APNodeShell(cmd.Cmd):
    """Interactive shell for AP node management"""

    def __init__(self, ap_node):
        super().__init__()
        self.ap_node = ap_node
        self.prompt = f"{ap_node.name}> "
        self.intro = f"\n{'='*60}\nAccess Point Shell: {ap_node.name}\n{'='*60}\n"
        self._print_status()
        print("\nAvailable commands: help, status, info, power, freq, bw, transmit, exit")
        print("Type 'help' for more information\n")

    def do_help(self, arg):
        """help [command] - Show help"""
        if arg:
            return super().do_help(arg)

        help_text = """
Access Point (AP) Commands:
  help              - Show this help message
  status            - Show current AP status
  info              - Show detailed AP information
  power [dBm]       - View or set transmit power
  freq [Hz]         - View or set carrier frequency
  bw [MHz]          - View or set signal bandwidth
  transmit [target] - Configure transmission target
  exit              - Exit AP shell
        """
        print(help_text)

    def do_status(self, arg):
        """status - Show AP status"""
        self._print_status()

    def do_info(self, arg):
        """info - Show detailed AP information"""
        print(f"\n{self.ap_node.name} Information:")
        print(f"  Name:           {self.ap_node.name}")
        print(f"  Type:           Access Point")
        print(f"  Position:       ({self.ap_node.pos[0]:.2f}, {self.ap_node.pos[1]:.2f}, {self.ap_node.pos[2]:.2f}) meters")
        print(f"  Antenna Type:   Omnidirectional")
        print(f"  Power:          {self.ap_node.power_dBm:.1f} dBm")
        print(f"  Frequency:      {self.ap_node.freq/1e9:.2f} GHz")
        print(f"  Bandwidth:      {self.ap_node.bandwidth_MHz:.1f} MHz")
        print(f"  MIMO Streams:   2x2")

    def do_power(self, arg):
        """power [dBm] - View or set transmit power"""
        if not arg:
            print(f"{self.ap_node.name} Transmit Power: {self.ap_node.power_dBm:.1f} dBm")
        else:
            try:
                power = float(arg)
                self.ap_node.power_dBm = power
                print(f"✓ Transmit power set to {power:.1f} dBm for {self.ap_node.name}")
            except ValueError:
                print("Invalid power value. Usage: power <dBm>")

    def do_freq(self, arg):
        """freq [Hz] - View or set carrier frequency"""
        if not arg:
            print(f"{self.ap_node.name} Frequency: {self.ap_node.freq/1e9:.3f} GHz")
        else:
            try:
                freq = float(arg)
                self.ap_node.freq = freq
                print(f"✓ Frequency set to {freq/1e9:.3f} GHz for {self.ap_node.name}")
            except ValueError:
                print("Invalid frequency. Usage: freq <Hz>")

    def do_bw(self, arg):
        """bw [MHz] - View or set signal bandwidth"""
        if not arg:
            print(f"{self.ap_node.name} Bandwidth: {self.ap_node.bandwidth_MHz:.1f} MHz")
        else:
            try:
                bw = float(arg)
                self.ap_node.bandwidth_MHz = bw
                print(f"✓ Bandwidth set to {bw:.1f} MHz for {self.ap_node.name}")
            except ValueError:
                print("Invalid bandwidth. Usage: bw <MHz>")

    def do_transmit(self, arg):
        """transmit [target] - Configure transmission target"""
        if not arg:
            print(f"{self.ap_node.name} Transmission: Not configured")
        else:
            target = arg
            print(f"✓ Transmission configured to target {target} from {self.ap_node.name}")

    def do_exit(self, arg):
        """exit - Exit AP shell"""
        print(f"Exiting {self.ap_node.name} shell\n")
        return True

    def _print_status(self):
        """Print AP node status"""
        print(f"\n{self.ap_node.name} Status:")
        print(f"  Position:      ({self.ap_node.pos[0]:.2f}, {self.ap_node.pos[1]:.2f}, {self.ap_node.pos[2]:.2f})")
        print(f"  Transmit Power: {self.ap_node.power_dBm:.1f} dBm")
        print(f"  Frequency:      {self.ap_node.freq/1e9:.2f} GHz")
        print(f"  Bandwidth:      {self.ap_node.bandwidth_MHz:.1f} MHz")
        print(f"  Status:         Active")
        print(f"  Connected UEs:  0")
