"""
Interactive CLI for RISNet with direct node access

Allows commands like:
  ap1 info              - Get AP info
  ris1 info             - Get RIS info
  ue1 info              - Get UE info
  ap1 ping ue1          - Ping from AP to UE
  ap1 iperf ue1         - Test throughput
  ap1 connect ris1 ue1  - Connect AP->RIS->UE
  ap1 findpaths ue1     - Find all paths
"""

import cmd
import sys
import numpy as np
from typing import Optional
import pprint


class RISnetCLI(cmd.Cmd):
    """Interactive CLI for RISNet simulator with node access"""

    intro = """
╔════════════════════════════════════════════════════════════╗
║           RISNet v2.0 - Interactive CLI                   ║
║                                                            ║
║  Add nodes: add ap ap1 0 0                                ║
║             add ris ris1 5 0                              ║
║             add ue ue1 10 3                               ║
║                                                            ║
║  Node access: <nodename> <command>                        ║
║    ap1 info            - Get node info                    ║
║    ap1 ping ue1        - Test connectivity                ║
║    ap1 iperf ue1       - Test throughput                  ║
║    ap1 connect ris1 ue1 - Connect via RIS                 ║
║    ap1 findpaths ue1   - Find all paths                   ║
║                                                            ║
║  Type 'help' or '?' for all commands                      ║
╚════════════════════════════════════════════════════════════╝
"""

    prompt = "risnet> "

    def __init__(self, net):
        """Initialize CLI with RISnet instance

        Args:
            net: RISnet instance
        """
        super().__init__()
        self.net = net
        self._started = False

        # Auto-naming counters
        self._ap_counter = 0
        self._ris_counter = 0
        self._ue_counter = 0

    def onecmd(self, line):
        """Override onecmd to handle node access syntax"""
        # First check if this is a node access command
        if line and not line.startswith('#'):
            parts = line.split(None, 1)
            if parts:
                potential_node = parts[0]
                # Check if it's a node name
                if (potential_node in self.net.aps or
                    potential_node in self.net.riss or
                    potential_node in self.net.ues):
                    # This is node access syntax
                    if len(parts) == 1:
                        # Just the node name, show info
                        line = f"nodeinfo {potential_node}"
                    else:
                        # Has a command after the node
                        line = f"nodecmd {line}"

        # Call parent's onecmd with potentially transformed line
        return super().onecmd(line)

    def do_add(self, arg):
        """add <ap|ris|ue> [name] <x> <y> [z] [N] [bits]

        Add a node to the network. Name is optional - auto-generated if omitted.

        Examples (with auto-names):
            add ap 0 0              # Creates AP1, AP2, AP3, ...
            add ris 5 0             # Creates R1, R2, R3, ...
            add ue 10 3             # Creates UE1, UE2, UE3, ...

        Examples (with explicit names):
            add ap ap1 0 0          # Creates AP named 'ap1'
            add ris ris1 5 0        # Creates RIS named 'ris1'
            add ue ue1 10 3         # Creates UE named 'ue1'

        RIS with parameters:
            add ris 5 0 0 16 2      # R1 at (5,0,0) with N=16, bits=2
        """
        try:
            parts = arg.split()
            if len(parts) < 3:
                print("Usage: add <ap|ris|ue> [name] <x> <y> [z] [N] [bits]")
                print("       (name is optional, auto-generated if omitted)")
                return

            node_type = parts[0].lower()

            # Determine if second argument is a name or coordinate
            second_arg = parts[1]
            # A name starts with a letter and may contain letters, digits, underscores
            # A coordinate is a number (possibly negative)
            try:
                float(second_arg)
                is_name = False  # It's a valid number, so it's a coordinate
            except ValueError:
                is_name = True   # Not a number, so it must be a name

            if is_name:
                # Explicit name provided
                name = second_arg
                x = float(parts[2])
                y = float(parts[3])
                z = float(parts[4]) if len(parts) > 4 and parts[4][0] not in ['N', 'n', 'b'] else 0.0
                idx = 5 if len(parts) > 4 and parts[4][0] not in ['N', 'n', 'b'] else 4
            else:
                # No name provided, auto-generate
                x = float(second_arg)
                y = float(parts[2])
                z = float(parts[3]) if len(parts) > 3 and parts[3][0] not in ['N', 'n', 'b'] else 0.0
                idx = 4 if len(parts) > 3 and parts[3][0] not in ['N', 'n', 'b'] else 3

                # Auto-generate name based on type
                if node_type == 'ap':
                    self._ap_counter += 1
                    name = f"AP{self._ap_counter}"
                elif node_type == 'ris':
                    self._ris_counter += 1
                    name = f"R{self._ris_counter}"
                elif node_type == 'ue':
                    self._ue_counter += 1
                    name = f"UE{self._ue_counter}"
                else:
                    print(f"Unknown node type: {node_type}")
                    return

            if node_type == 'ap':
                node = self.net.addAP(name, position=(x, y, z))
                print(f"✓ Added AP '{name}' at ({x}, {y}, {z})")

            elif node_type == 'ris':
                N = 16
                bits = 2

                # Parse optional positional or keyword arguments for N and bits
                if len(parts) > idx:
                    if '=' in parts[idx]:
                        # Keyword arguments
                        for part in parts[idx:]:
                            if '=' in part:
                                key, val = part.split('=')
                                if key.lower() == 'n':
                                    N = int(val)
                                elif key.lower() == 'bits':
                                    bits = int(val)
                    else:
                        # Positional arguments
                        N = int(parts[idx])
                        if len(parts) > idx + 1:
                            bits = int(parts[idx + 1])

                node = self.net.addRIS(name, position=(x, y, z), N=N, bits=bits)
                print(f"✓ Added RIS '{name}' at ({x}, {y}, {z}) [N={N}, bits={bits}]")

            elif node_type == 'ue':
                node = self.net.addUE(name, position=(x, y, z))
                print(f"✓ Added UE '{name}' at ({x}, {y}, {z})")
            else:
                print(f"Unknown node type: {node_type}")
                return

            return node

        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def do_list(self, arg):
        """list [ap|ris|ue]

        List all nodes or specific node type

        Examples:
            list           - List all nodes
            list ap        - List APs only
            list ris       - List RIS only
            list ue        - List UEs only
        """
        node_type = arg.lower() if arg else 'all'

        if node_type in ['all', 'ap']:
            if self.net.aps:
                print(f"\n📍 Access Points ({len(self.net.aps)}):")
                for name, ap in self.net.aps.items():
                    print(f"  {name:12} pos=({ap.pos[0]:6.1f}, {ap.pos[1]:6.1f}, {ap.pos[2]:6.1f})  "
                          f"power={ap.power_dBm:.1f} dBm  freq={ap.freq/1e9:.1f} GHz")
            else:
                if node_type != 'all':
                    print("No Access Points")

        if node_type in ['all', 'ris']:
            if self.net.riss:
                print(f"\n📡 RIS Surfaces ({len(self.net.riss)}):")
                for name, ris in self.net.riss.items():
                    print(f"  {name:12} pos=({ris.pos[0]:6.1f}, {ris.pos[1]:6.1f}, {ris.pos[2]:6.1f})  "
                          f"N={ris.N}x{ris.N}  bits={ris.bits}  angle={ris.max_angle_deg}°")
            else:
                if node_type != 'all':
                    print("No RIS surfaces")

        if node_type in ['all', 'ue']:
            if self.net.ues:
                print(f"\n📱 User Equipment ({len(self.net.ues)}):")
                for name, ue in self.net.ues.items():
                    print(f"  {name:12} pos=({ue.pos[0]:6.1f}, {ue.pos[1]:6.1f}, {ue.pos[2]:6.1f})")
            else:
                if node_type != 'all':
                    print("No User Equipment")

        if node_type not in ['all', 'ap', 'ris', 'ue']:
            print(f"Unknown type: {node_type}. Use 'ap', 'ris', 'ue', or 'all'")

    def do_nodeinfo(self, arg):
        """nodeinfo <nodename>

        Get detailed info about a node

        Examples:
            nodeinfo ap1
            nodeinfo ris1
            nodeinfo ue1
        """
        node_name = arg.strip()

        node = self._get_node(node_name)
        if not node:
            print(f"Error: Node '{node_name}' not found")
            return

        print(f"\n{'='*60}")
        print(f"Node: {node_name}")
        print(f"{'='*60}")
        print(f"Type: {node.__class__.__name__}")
        print(f"Position: ({node.pos[0]:.2f}, {node.pos[1]:.2f}, {node.pos[2]:.2f}) m")

        if hasattr(node, 'power_dBm'):
            print(f"Power: {node.power_dBm:.1f} dBm")
        if hasattr(node, 'freq'):
            print(f"Frequency: {node.freq/1e9:.1f} GHz")
        if hasattr(node, 'N'):
            print(f"Array Size: {node.N}x{node.N}")
        if hasattr(node, 'bits'):
            print(f"Phase Quantization: {node.bits} bits")
        if hasattr(node, 'max_angle_deg'):
            print(f"Max Steering Angle: {node.max_angle_deg}°")

        print(f"{'='*60}\n")

    def do_nodecmd(self, line):
        """Internal handler for node-based commands

        Syntax: <nodename> <command> [args]

        Commands:
            info              - Show node information
            ping <target>     - Test connectivity to target
            iperf <target>    - Estimate throughput to target
            findpaths <target> [algorithm] - Find all paths
            connect <ris> <target> - Connect via RIS
            position <x> <y> [z] - Update node position
            rename <newname>  - Rename the node
        """
        try:
            parts = line.split(None, 2)
            if len(parts) < 2:
                print("Usage: <nodename> <command> [args]")
                return

            node_name = parts[0]
            command = parts[1].lower()
            args = parts[2] if len(parts) > 2 else ""

            node = self._get_node(node_name)
            if not node:
                print(f"Error: Node '{node_name}' not found")
                return

            # Route to appropriate handler
            if command == 'info':
                self._cmd_nodeinfo(node_name, node)
            elif command == 'ping':
                self._cmd_ping(node_name, node, args)
            elif command == 'iperf':
                self._cmd_iperf(node_name, node, args)
            elif command == 'findpaths':
                self._cmd_findpaths(node_name, node, args)
            elif command == 'connect':
                self._cmd_connect(node_name, node, args)
            elif command == 'position':
                self._cmd_position(node_name, node, args)
            elif command == 'rename':
                self._cmd_rename(node_name, node, args)
            else:
                print(f"Unknown command: {command}")
                print("Available: info, ping, iperf, findpaths, connect, position, rename")

        except Exception as e:
            print(f"Error: {e}")

    def _cmd_nodeinfo(self, node_name, node):
        """Show node information"""
        print(f"\n{'='*60}")
        print(f"📌 Node: {node_name}")
        print(f"{'='*60}")
        print(f"  Type: {node.__class__.__name__}")
        print(f"  Position: ({node.pos[0]:.3f}, {node.pos[1]:.3f}, {node.pos[2]:.3f}) m")

        if hasattr(node, 'power_dBm'):
            print(f"  Power: {node.power_dBm:.1f} dBm")
        if hasattr(node, 'freq'):
            freq_ghz = node.freq / 1e9
            print(f"  Frequency: {freq_ghz:.1f} GHz")
        if hasattr(node, 'N'):
            print(f"  Array Size: {node.N} × {node.N}")
            print(f"  Total Elements: {node.N * node.N}")
        if hasattr(node, 'bits'):
            print(f"  Phase Quantization: {node.bits} bits")
            print(f"  Quantization Levels: {2**node.bits}")
        if hasattr(node, 'max_angle_deg'):
            print(f"  Max Steering Angle: {node.max_angle_deg}°")
        if hasattr(node, 'active_mode'):
            mode = "Active" if node.active_mode else "Passive"
            print(f"  Mode: {mode}")

        print(f"{'='*60}\n")

    def _cmd_ping(self, src_name, src_node, dst_arg):
        """Ping from src to dst"""
        if not dst_arg:
            print("Usage: <node> ping <target_node>")
            return

        dst_node = self._get_node(dst_arg)
        if not dst_node:
            print(f"Error: Target node '{dst_arg}' not found")
            return

        if not self.net.started:
            print("Starting network...")
            self.net.start()
            self._started = True

        try:
            result = self.net.ping(src_node, dst_node)

            print(f"\n{'='*60}")
            print(f"🔌 Ping: {src_name} → {dst_arg}")
            print(f"{'='*60}")

            if result['reachable']:
                print(f"  Status: ✓ Reachable")
                print(f"  SNR: {result['snr_dB']:.2f} dB")
                print(f"  Hops: {result['hops']}")
                print(f"  Path: {' → '.join(result['path'])}")
            else:
                print(f"  Status: ✗ Unreachable")
                print(f"  SNR: -∞ dB")

            print(f"{'='*60}\n")

        except Exception as e:
            print(f"Error during ping: {e}")

    def _cmd_iperf(self, src_name, src_node, dst_arg):
        """iPerf throughput test"""
        if not dst_arg:
            print("Usage: <node> iperf <target_node>")
            return

        dst_node = self._get_node(dst_arg)
        if not dst_node:
            print(f"Error: Target node '{dst_arg}' not found")
            return

        if not self.net.started:
            print("Starting network...")
            self.net.start()
            self._started = True

        try:
            result = self.net.iperf(src_node, dst_node)

            print(f"\n{'='*60}")
            print(f"📊 iPerf: {src_name} → {dst_arg}")
            print(f"{'='*60}")

            throughput = result['throughput_Mbps']
            snr = result['snr_dB']
            bw = result['bandwidth_MHz']

            print(f"  Throughput: {throughput:.2f} Mbps")
            print(f"  SNR: {snr:.2f} dB")
            print(f"  Bandwidth: {bw} MHz")
            print(f"  Capacity: {throughput:.2f} Mbps (Shannon limit)")

            print(f"{'='*60}\n")

        except Exception as e:
            print(f"Error during iPerf: {e}")

    def _cmd_findpaths(self, src_name, src_node, args):
        """Find all paths"""
        parts = args.split()

        if not parts:
            print("Usage: <node> findpaths <target_node> [algorithm]")
            return

        dst_arg = parts[0]
        algorithm = parts[1].lower() if len(parts) > 1 else 'dijkstra'

        if algorithm not in ['dijkstra', 'astar', 'greedy', 'exhaustive']:
            print(f"Unknown algorithm: {algorithm}")
            print("Available: dijkstra, astar, greedy, exhaustive")
            return

        dst_node = self._get_node(dst_arg)
        if not dst_node:
            print(f"Error: Target node '{dst_arg}' not found")
            return

        if not self.net.started:
            print("Starting network...")
            self.net.start()
            self._started = True

        try:
            paths = self.net.findPaths(src_node, dst_node, algorithm=algorithm)

            print(f"\n{'='*60}")
            print(f"🗺️  Paths: {src_name} → {dst_arg} [{algorithm.upper()}]")
            print(f"{'='*60}")

            if not paths:
                print("  No paths found")
            else:
                for i, path in enumerate(paths, 1):
                    path_str = ' → '.join(path['path'])
                    print(f"\n  Path {i}: {path_str}")
                    print(f"    Type: {path['type']}")
                    print(f"    SNR: {path['snr_dB']:.2f} dB")
                    print(f"    Hops: {path['hops']}")

            print(f"\n  Total paths found: {len(paths)}")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"Error finding paths: {e}")

    def _cmd_connect(self, src_name, src_node, args):
        """Connect via RIS"""
        parts = args.split()

        if len(parts) < 2:
            print("Usage: <ap> connect <ris> <ue>")
            return

        ris_name = parts[0]
        ue_name = parts[1]

        ris_node = self._get_node(ris_name)
        ue_node = self._get_node(ue_name)

        if not ris_node:
            print(f"Error: RIS node '{ris_name}' not found")
            return
        if not ue_node:
            print(f"Error: UE node '{ue_name}' not found")
            return

        if not self.net.started:
            print("Starting network...")
            self.net.start()
            self._started = True

        try:
            result = self.net.connect(src_node, ris_node, ue_node)

            print(f"\n{'='*60}")
            print(f"🔗 Connect: {src_name} → {ris_name} → {ue_name}")
            print(f"{'='*60}")
            print(f"  SNR: {result['snr_dB']:.2f} dB")
            print(f"  Power: {result['pwr_dBm']:.2f} dBm")
            print(f"  Beam Angle: {result['beam_angle']:.1f}°")
            print(f"  Status: ✓ Connected")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"Error during connect: {e}")

    def _cmd_position(self, node_name, node, args):
        """Update node position"""
        parts = args.split()

        if len(parts) < 2:
            print("Usage: <node> position <x> <y> [z]")
            return

        try:
            x = float(parts[0])
            y = float(parts[1])
            z = float(parts[2]) if len(parts) > 2 else node.pos[2]

            node.pos = np.array([x, y, z])

            # Update RIS geometry if it's a RIS
            if hasattr(node, 'update_geometry'):
                node.update_geometry()

            print(f"✓ Updated {node_name} position to ({x:.2f}, {y:.2f}, {z:.2f})")

        except (ValueError, IndexError) as e:
            print(f"Error: {e}")

    def _cmd_rename(self, node_name, node, args):
        """Rename a node"""
        new_name = args.strip()

        if not new_name:
            print("Usage: <node> rename <newname>")
            return

        if not new_name.replace('_', '').replace('-', '').isalnum():
            print("Error: Node name must contain only letters, digits, underscores, and hyphens")
            return

        # Check if new name is already taken
        if (new_name in self.net.aps or
            new_name in self.net.riss or
            new_name in self.net.ues):
            print(f"Error: Node name '{new_name}' is already in use")
            return

        # Find which dict the node is in and update it
        if node_name in self.net.aps:
            del self.net.aps[node_name]
            self.net.aps[new_name] = node
            node_dict = "AP"
        elif node_name in self.net.riss:
            del self.net.riss[node_name]
            self.net.riss[new_name] = node
            node_dict = "RIS"
        elif node_name in self.net.ues:
            del self.net.ues[node_name]
            self.net.ues[new_name] = node
            node_dict = "UE"
        else:
            print(f"Error: Node '{node_name}' not found")
            return

        # Update the node's name property
        node.name = new_name

        # Update in the main network nodes dict if it exists
        if node_name in self.net.network.nodes:
            del self.net.network.nodes[node_name]
            self.net.network.nodes[new_name] = node

        print(f"✓ Renamed {node_dict} '{node_name}' to '{new_name}'")
        print(f"  Use '{new_name}' for future commands (e.g., '{new_name} info')")

    def _get_node(self, name: str):
        """Get node by name from any node dict"""
        if name in self.net.aps:
            return self.net.aps[name]
        if name in self.net.riss:
            return self.net.riss[name]
        if name in self.net.ues:
            return self.net.ues[name]
        return None

    def do_start(self, arg):
        """start

        Start the network
        """
        if self.net.started:
            print("Network already started")
            return

        print("Starting network...")
        self.net.start()
        self._started = True
        print("✓ Network started")

    def do_stop(self, arg):
        """stop

        Stop the network
        """
        if not self.net.started and not self._started:
            print("Network not started")
            return

        print("Stopping network...")
        self.net.stop()
        self._started = False
        print("✓ Network stopped")

    def do_clear(self, arg):
        """clear

        Clear all nodes from the network
        """
        count = len(self.net.aps) + len(self.net.riss) + len(self.net.ues)
        if count == 0:
            print("No nodes to clear")
            return

        self.net.aps.clear()
        self.net.riss.clear()
        self.net.ues.clear()
        self.net.network.nodes.clear()

        print(f"✓ Cleared {count} nodes")

    def do_help(self, arg):
        """help [command]

        Show help for commands
        """
        if arg:
            super().do_help(arg)
        else:
            print("""
╔════════════════════════════════════════════════════════════╗
║                    RISNet CLI Help                         ║
╚════════════════════════════════════════════════════════════╝

NETWORK MANAGEMENT:
  add <type> <name> <x> <y> [z]  - Add node (ap/ris/ue)
  list [type]                    - List nodes
  start                          - Start network
  stop                           - Stop network
  clear                          - Remove all nodes

NODE OPERATIONS (syntax: <nodename> <command>):
  <node> info                    - Show node details
  <node> ping <target>           - Test connectivity
  <node> iperf <target>          - Test throughput
  <node> findpaths <target> [algo] - Find all paths
  <node> position <x> <y> [z]    - Update position
  <node> rename <newname>        - Rename the node
  <ap> connect <ris> <ue>        - Connect AP→RIS→UE

EXAMPLE SESSION:
  risnet> add ap ap1 0 0
  risnet> add ris ris1 5 0 N=16 bits=2
  risnet> add ue ue1 10 3
  risnet> list
  risnet> ap1 info
  risnet> ap1 rename access_point
  risnet> access_point ping ue1
  risnet> ap1 findpaths ue1 dijkstra
  risnet> ap1 connect ris1 ue1

Type 'help <command>' for more details
""")

    def do_exit(self, arg):
        """exit

        Exit the CLI
        """
        if self._started:
            self.net.stop()
        print("Goodbye!")
        return True

    def do_quit(self, arg):
        """quit

        Quit the CLI
        """
        return self.do_exit(arg)

    def emptyline(self):
        """Override empty line behavior"""
        pass

    def default(self, line):
        """Handle unrecognized commands"""
        print(f"Unknown command: '{line}'")
        print("Type 'help' for available commands")
