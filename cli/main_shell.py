"""
Main RISNetCLI shell
Extracted from monolithic main.py for better modularity
"""

import cmd
import os
import shlex
import math
import pprint
try:
    import readline
except ImportError:
    # readline is Unix-only; Windows uses pyreadline or native cmd features
    readline = None
from datetime import datetime
from pathlib import Path
import numpy as np
from core import RIS, AccessPoint, UE
from controller.beamsweeping import SweepAlgorithmLoader, MLPredictorLoader
from cli import run_testall
from cli.ris_shell import RISNodeShell
from cli.ap_shell import APNodeShell
from cli.ue_shell import UENodeShell
from cli.helpers import TopologyHelper, NetworkIO, sanitize_for_json
from cli.video_stream import VideoStreamConfig, run_video_stream_workflow
from cli.connection_handler import ConnectionHandler


class RISNetCLI(cmd.Cmd):
    """Interactive CLI for RISNet simulator"""
    intro = "Welcome to RISNet CLI. Type help or ? to list commands."
    prompt = "risnet> "

    def __init__(self, net):
        super().__init__()
        self.net = net
        self.topology_helper = TopologyHelper(net)
        self.network_io = NetworkIO()
        self.connection_handler = ConnectionHandler(net)
        # Load network state on startup
        self._load_network()
        # Setup tab completion
        self._setup_completer()

    def _setup_completer(self):
        """Setup readline for tab completion"""
        # Get all available commands
        self.all_commands = [name[3:] for name in dir(self) if name.startswith('do_')]

        # Setup readline completer (only if readline is available)
        if readline:
            readline.set_completer(self._completer)
            # Enable tab completion
            readline.parse_and_bind('tab: complete')

    def _completer(self, text, state):
        """Custom completer for command and argument suggestions"""
        if not readline:
            return None
        if state == 0:
            # Get the current line
            line = readline.get_line_buffer()

            # If we're at the beginning (no space), complete commands
            if ' ' not in line or line.endswith(' '):
                # Complete command names
                self.completion_matches = [cmd for cmd in self.all_commands if cmd.startswith(text)]
            else:
                # For arguments, provide context-specific completion
                parts = line.split()
                cmd = parts[0]
                self.completion_matches = self._get_argument_completions(cmd, text)

        # Return completions one by one
        if state < len(self.completion_matches):
            return self.completion_matches[state]
        else:
            return None

    def _get_argument_completions(self, cmd, text):
        """Get argument completions based on command"""
        completions = []

        # Command-specific argument completions
        if cmd in ['connect', 'status', 'delete', 'edit']:
            # For connect command, provide special handling for flags
            if cmd == 'connect':
                line = readline.get_line_buffer() if readline else ''

                # Check if we're completing a --algo flag
                if '--algo' in line and text and not text.startswith('-'):
                    from controller.beamsweeping import SweepAlgorithmLoader
                    try:
                        algos = SweepAlgorithmLoader.list_algorithms()
                        # Get all algo names and aliases
                        all_names = list(algos.keys())
                        for aliases in [algos[a]['aliases'] for a in algos if algos[a]['aliases']]:
                            all_names.extend(aliases)
                        completions = [a for a in all_names if a.startswith(text)]
                    except:
                        pass

                # Check if we're completing a --ml-predictor flag
                elif '--ml-predictor' in line and text and not text.startswith('-'):
                    from controller.beamsweeping import MLPredictorLoader
                    try:
                        predictors = MLPredictorLoader.list_predictors()
                        predictor_names = list(predictors.keys())
                        completions = [p for p in predictor_names if p.startswith(text)]
                    except:
                        pass

                # Otherwise, suggest node names
                else:
                    node_names = list(self.net.nodes.keys()) if self.net.nodes else []
                    completions = [n for n in node_names if n.startswith(text)]
            else:
                # For other commands (status, delete, edit), suggest node names
                node_names = list(self.net.nodes.keys()) if self.net.nodes else []
                completions = [n for n in node_names if n.startswith(text)]

        elif cmd in ['load', 'plot']:
            # Suggest file names for load and plot commands
            try:
                cwd = os.getcwd()
                files = [f for f in os.listdir(cwd) if f.startswith(text)]
                completions = [f for f in files if f.endswith(('.json', '.csv', '.png', '.jpg'))]
            except:
                pass

        elif cmd in ['save']:
            # Suggest .json files
            try:
                cwd = os.getcwd()
                files = [f for f in os.listdir(cwd) if f.startswith(text) and f.endswith('.json')]
                completions = files
            except:
                pass

        elif cmd == 'add':
            # Complete node types and names
            if text.startswith('ap') or text.startswith('ris') or text.startswith('ue'):
                completions = ['ap', 'ris', 'ue']

        return completions

    # =====================================================================
    # Help Commands
    # =====================================================================

    def do_help(self, arg):
        """help [command] - Show available commands"""
        if arg:
            target = getattr(self, f'do_{arg}', None)
            if target and target.__doc__:
                print(target.__doc__.strip())
            else:
                print(f"No detailed help for '{arg}'")
            return

        print("Available commands:")
        command_docs = []
        for name in dir(self):
            if not name.startswith('do_'):
                continue
            cmd_name = name[3:]
            func = getattr(self, name)
            doc = (func.__doc__ or '').strip().splitlines()
            description = doc[0].strip() if doc else ''
            if not description:
                description = '(no description)'
            command_docs.append((cmd_name, description))

        if not command_docs:
            return

        max_len = max(len(cmd) for cmd, _ in command_docs)
        pad = max(12, max_len + 2)

        for cmd_name, description in sorted(command_docs):
            print(f"  {cmd_name:<{pad}}{description}")

    # =====================================================================
    # Node Management
    # =====================================================================

    def do_add(self, arg):
        """add <ap|ris|ue|random> [name] [--ris-aware [distance]]
        Auto-generates random positions and parameters.
        For UE: can optionally position within RIS deflection FOV to avoid clamping.

        Examples:
          add ap                    -> Creates AP1 (random position)
          add ap MyAP               -> Creates MyAP (random position)
          add ris                   -> Creates R1 (random position)
          add ue                    -> Creates UE1 (random position)
          add ue UE2 --ris-aware    -> Creates UE2 within RIS FOV (auto distance)
          add ue UE3 --ris-aware 8  -> Creates UE3 within RIS FOV at distance 8m
          add random                -> Adds 1 AP, 1 RIS, 1 UE (all random)
          add random 2 1 5          -> Adds 2 APs, 1 RIS, 5 UEs
          add random 1 2 4 --distance 8-12  -> Custom distance range
        """
        try:
            parts = shlex.split(arg)
            if len(parts) < 1:
                print("usage: add <ap|ris|ue|random> [name] [--ris-aware [distance]]")
                return

            typ = parts[0].lower()

            # Handle 'add random' subcommand
            if typ == 'random':
                self._handle_add_random(arg.replace('random', '', 1).strip())
                return
            name = None
            ris_aware = False
            distance = None

            # Parse arguments
            idx = 1
            while idx < len(parts):
                if parts[idx] == '--ris-aware':
                    ris_aware = True
                    # Check if next arg is distance (number)
                    if idx + 1 < len(parts) and parts[idx + 1].replace('.', '', 1).isdigit():
                        distance = float(parts[idx + 1])
                        idx += 2
                    else:
                        idx += 1
                else:
                    if not name:
                        name = parts[idx]
                    idx += 1

            if not name:
                name = self.topology_helper.generate_auto_name(typ)

            z = 0.0

            if typ == 'ap':
                x, y = self.topology_helper.generate_position(typ)
                self.net.add_ap(name, x, y, z)
                print(f"✓ Added AP {name} at ({x:.2f}, {y:.2f})")
            elif typ == 'ris':
                x, y = self.topology_helper.generate_position(typ)
                N = 16
                bits = 1
                self.net.add_ris(name, x, y, z, N, bits)
                print(f"✓ Added RIS {name} at ({x:.2f}, {y:.2f}) (N={N}, bits={bits})")
            elif typ == 'ue':
                # Check if RIS exists in network
                ris_list = [n for n in self.net.nodes.values() if type(n).__name__ == 'RIS']
                has_ris = len(ris_list) > 0

                # If RIS exists, default to RIS-aware placement (unless explicitly set to False)
                # User can override with explicit flag
                use_ris_aware = ris_aware or (has_ris and not ris_aware)

                if use_ris_aware and has_ris:
                    x, y = self._add_ue_within_ris_fov(name, distance)
                else:
                    x, y = self.topology_helper.generate_position(typ)

                self.net.add_ue(name, x, y, z)
                if use_ris_aware and has_ris:
                    print(f"✓ Added UE {name} at ({x:.2f}, {y:.2f}) (RIS-aware placement)")
                else:
                    print(f"✓ Added UE {name} at ({x:.2f}, {y:.2f})")
            else:
                print('usage: add <ap|ris|ue> [name] [--ris-aware [distance]]')
                return

            self._save_network()
        except Exception as e:
            print('error:', e)

    def _calculate_angle_from_ris(self, ris_pos, target_pos):
        """Calculate angle from RIS to target in world coordinates (degrees)"""
        dx = target_pos[0] - ris_pos[0]
        dy = target_pos[1] - ris_pos[1]
        angle_rad = np.arctan2(dy, dx)
        angle_deg = np.degrees(angle_rad)

        # Normalize to [-180, 180]
        if angle_deg < -180:
            angle_deg += 360
        elif angle_deg > 180:
            angle_deg -= 360

        return angle_deg

    def _is_within_ris_fov(self, angle_deg, ris_normal, ris_max_angle):
        """Check if angle is within RIS FOV"""
        min_angle = ris_normal - ris_max_angle
        max_angle = ris_normal + ris_max_angle
        return (angle_deg >= min_angle) and (angle_deg <= max_angle)

    def _add_ue_within_ris_fov(self, ue_name, distance=None):
        """Position UE within RIS deflection FOV, respecting AP position.

        The UE must be positioned such that:
        1. Both AP and UE are within RIS hardware FOV (±max_angle_deg from RIS normal)
        2. The angular separation between AP and UE (as seen from RIS) respects the
           deflection constraint: |AP_angle - UE_angle| <= 2 * max_angle_deg
        3. This ensures the AP->RIS->UE deflection stays within hardware capability

        Args:
            ue_name: Name of UE being added
            distance: Distance from RIS (optional, auto-calculated if None)

        Returns:
            (x, y) position within RIS reachable angles
        """
        import numpy as np

        # Check if RIS exists
        ris_list = [n for n in self.net.nodes.values() if type(n).__name__ == 'RIS']
        if not ris_list:
            print("  Warning: No RIS in network, using random position")
            return self.topology_helper.generate_position('ue')

        ris = ris_list[0]  # Use first RIS
        ris_max_angle = getattr(ris, 'max_angle_deg', 60.0)
        ris_normal = getattr(ris, 'normal_angle_deg', 0.0)

        # Auto-calculate distance if not provided
        if distance is None:
            distance = np.random.uniform(5.0, 15.0)

        # Check AP position if it exists
        ap_list = [n for n in self.net.nodes.values() if type(n).__name__ == 'AccessPoint']
        ap_angle = None
        ap_within_fov = False
        ap_reachable = True
        if ap_list:
            ap = ap_list[0]  # Use first AP
            ap_angle = self._calculate_angle_from_ris(ris.pos, ap.pos)
            ap_within_fov = self._is_within_ris_fov(ap_angle, ris_normal, ris_max_angle)

            # Check if AP is reachable by RIS at all (within deflection capability)
            ris_fov_min = ris_normal - ris_max_angle
            ris_fov_max = ris_normal + ris_max_angle

            # Check distance to closest RIS FOV boundary
            dist_to_min = abs(ap_angle - ris_fov_min)
            dist_to_max = abs(ap_angle - ris_fov_max)
            # Normalize to [0, 180]
            while dist_to_min > 180:
                dist_to_min = 360 - dist_to_min
            while dist_to_max > 180:
                dist_to_max = 360 - dist_to_max
            min_dist_to_fov = min(dist_to_min, dist_to_max)

            if min_dist_to_fov > ris_max_angle:
                ap_reachable = False
                print(f"  ✗ CRITICAL: AP at angle {ap_angle:.2f}° is {min_dist_to_fov:.1f}° away from nearest RIS FOV point")
                print(f"  RIS can only deflect ±{ris_max_angle}°. AP is unreachable by this RIS!")
                print(f"  UE placement will be unconstrained. Connection will likely fail.")
            elif not ap_within_fov:
                print(f"  Warning: AP at angle {ap_angle:.2f}° is outside RIS FOV")
                print(f"  RIS FOV: [{ris_normal - ris_max_angle:.2f}°, {ris_normal + ris_max_angle:.2f}°]")

        # Determine valid angular range for UE placement
        # UE angle must satisfy:
        # 1. Be within RIS FOV: |UE_angle - RIS_normal| <= max_angle_deg
        # 2. If AP exists, deflection constraint: |AP_angle - UE_angle| <= 2 * max_angle_deg

        min_angle = ris_normal - ris_max_angle
        max_angle = ris_normal + ris_max_angle

        # Apply deflection constraint if AP exists
        if ap_angle is not None:
            # Deflection constraint: |UE_angle - AP_angle| <= max_angle_deg
            # The RIS can only deflect the beam by at most ±max_angle_deg
            # This ensures the RIS can physically reach both AP and UE

            # Valid UE angles are those where |UE_angle - AP_angle| <= max_angle_deg
            min_ue_from_ap = ap_angle - ris_max_angle
            max_ue_from_ap = ap_angle + ris_max_angle

            # Intersect with RIS FOV range
            ris_fov_min = ris_normal - ris_max_angle
            ris_fov_max = ris_normal + ris_max_angle

            intersect_min = max(ris_fov_min, min_ue_from_ap)
            intersect_max = min(ris_fov_max, max_ue_from_ap)

            if intersect_min <= intersect_max:
                # Valid intersection exists
                min_angle = intersect_min
                max_angle = intersect_max
                if not ap_within_fov:
                    print(f"  Warning: AP is outside RIS FOV but within deflection range")
            else:
                # No valid intersection - AP and UE cannot be simultaneously served
                if ap_within_fov:
                    print(f"  Warning: AP deflection constraint too strict, using RIS FOV only")
                    min_angle = ris_fov_min
                    max_angle = ris_fov_max
                else:
                    # AP is too far outside RIS FOV - try to place UE closer to AP
                    # Find the part of RIS FOV that's closest to AP
                    ap_to_fov_min = abs(ap_angle - ris_fov_min)
                    ap_to_fov_max = abs(ap_angle - ris_fov_max)

                    # Normalize angle differences to [0, 180]
                    while ap_to_fov_min > 180:
                        ap_to_fov_min = 360 - ap_to_fov_min
                    while ap_to_fov_max > 180:
                        ap_to_fov_max = 360 - ap_to_fov_max

                    if ap_to_fov_min <= ap_to_fov_max:
                        # FOV min is closer to AP
                        min_angle = max(ris_fov_min, ap_angle - ris_max_angle)
                        max_angle = ris_fov_max
                    else:
                        # FOV max is closer to AP
                        min_angle = ris_fov_min
                        max_angle = min(ris_fov_max, ap_angle + ris_max_angle)

                    print(f"  Warning: AP too far from RIS FOV, placing UE in closest reachable range")
                    if min_angle > max_angle:
                        # Even closer approach failed, use full FOV
                        min_angle = ris_fov_min
                        max_angle = ris_fov_max

        # Sample random angle within constrained range
        random_angle_deg = np.random.uniform(min_angle, max_angle)
        random_angle_rad = np.radians(random_angle_deg)

        # Calculate position relative to RIS
        x = ris.pos[0] + distance * np.cos(random_angle_rad)
        y = ris.pos[1] + distance * np.sin(random_angle_rad)

        # Debug output
        print(f"  RIS normal: {ris_normal:.2f}°, valid FOV: [{ris_normal - ris_max_angle:.2f}°, {ris_normal + ris_max_angle:.2f}°]")
        if ap_angle is not None:
            deflection = abs(random_angle_deg - ap_angle)
            # Normalize deflection to [0, 180]
            while deflection > 180:
                deflection = 360 - deflection
            print(f"  AP angle: {ap_angle:.2f}° {'✓' if ap_within_fov else '✗ outside FOV'}, deflection: {deflection:.2f}°")
        print(f"  UE angle: {random_angle_deg:.2f}°, distance: {distance:.2f}m")

        return x, y

    def _handle_add_random(self, arg):
        """Internal handler for 'add random' subcommand.

        Parameters:
          num_ap: Number of Access Points to add (default: 1)
          num_ris: Number of RIS nodes to add (default: 1)
          num_ue: Number of User Equipment to add (default: 1)
          --distance min-max: Distance range for UE from RIS (e.g., 5-15, default: 5-7)
          --no-ue: Skip adding User Equipment (useful for OpenCV vision-based detection)

        Examples:
          add random                           -> Adds 1 AP, 1 RIS, 1 UE
          add random 2 1 5                     -> Adds 2 APs, 1 RIS, 5 UEs
          add random 1 2 4 --distance 8-12     -> Custom distance range
          add random 1 1 --no-ue               -> Adds 1 AP, 1 RIS, no UE
        """
        try:
            parts = shlex.split(arg) if arg else []

            # Parse arguments with defaults
            num_ap = 1
            num_ris = 1
            num_ue = 1
            distance_range = (5.0, 7.0)
            skip_ue = False

            # Parse positional arguments
            idx = 0
            if idx < len(parts) and not parts[idx].startswith('--'):
                num_ap = int(parts[idx])
                idx += 1
            if idx < len(parts) and not parts[idx].startswith('--'):
                num_ris = int(parts[idx])
                idx += 1
            if idx < len(parts) and not parts[idx].startswith('--'):
                num_ue = int(parts[idx])
                idx += 1

            # Parse optional flags
            while idx < len(parts):
                if parts[idx] == '--distance' and idx + 1 < len(parts):
                    distance_str = parts[idx + 1]
                    try:
                        min_dist, max_dist = map(float, distance_str.split('-'))
                        distance_range = (min_dist, max_dist)
                        idx += 2
                    except (ValueError, IndexError):
                        print(f"Invalid distance format: {distance_str}. Expected: min-max (e.g., 5-15)")
                        return
                elif parts[idx] == '--no-ue':
                    skip_ue = True
                    num_ue = 0
                    idx += 1
                else:
                    idx += 1

            # Validate arguments
            if num_ap < 0 or num_ris < 0 or num_ue < 0:
                print("Error: Node counts must be non-negative")
                return

            if distance_range[0] < 0 or distance_range[1] < 0 or distance_range[0] > distance_range[1]:
                print("Error: Distance range must be positive and min <= max")
                return

            print("\n" + "=" * 70)
            print("ADDING RANDOM NODES TO NETWORK")
            print("=" * 70)
            print(f"Target: {num_ap} AP(s), {num_ris} RIS(s), {num_ue} UE(s)")
            print(f"UE distance range: {distance_range[0]:.1f}m - {distance_range[1]:.1f}m")
            print("-" * 70)

            # Add RIS nodes first (AP and UE placement depend on RIS position)
            ris_positions = []
            for i in range(num_ris):
                x, y = self.topology_helper.generate_position('ris')
                name = self.topology_helper.generate_auto_name('ris')
                self.net.add_ris(name, x, y, 0.0, N=16, bits=1)
                ris_positions.append((name, x, y))
                print(f"✓ Added RIS {name} at ({x:.2f}, {y:.2f}) (N=16, bits=1)")

            # Add APs - position them relative to RIS if RIS exists
            if num_ris > 0 and num_ap > 0:
                ris_name, ris_x, ris_y = ris_positions[0]
                for i in range(num_ap):
                    # Place AP within reachable range of RIS (±60° FOV, distance 5-15m)
                    ris_max_angle = 60.0
                    ap_distance = np.random.uniform(5.0, 15.0)
                    ap_angle_deg = np.random.uniform(-ris_max_angle, ris_max_angle)
                    ap_angle_rad = np.radians(ap_angle_deg)
                    x = ris_x + ap_distance * np.cos(ap_angle_rad)
                    y = ris_y + ap_distance * np.sin(ap_angle_rad)
                    name = self.topology_helper.generate_auto_name('ap')
                    self.net.add_ap(name, x, y, 0.0)
                    print(f"✓ Added AP {name} at ({x:.2f}, {y:.2f}) (RIS-aware, angle: {ap_angle_deg:.2f}°)")
            else:
                # Fallback to random AP placement if no RIS
                for i in range(num_ap):
                    x, y = self.topology_helper.generate_position('ap')
                    name = self.topology_helper.generate_auto_name('ap')
                    self.net.add_ap(name, x, y, 0.0)
                    print(f"✓ Added AP {name} at ({x:.2f}, {y:.2f})")

            # Add UE nodes with RIS-aware positioning
            ris_list = [n for n in self.net.nodes.values() if type(n).__name__ == 'RIS']
            has_ris = len(ris_list) > 0

            for i in range(num_ue):
                name = self.topology_helper.generate_auto_name('ue')

                if has_ris:
                    # Use RIS-aware placement with custom distance range
                    distance = np.random.uniform(distance_range[0], distance_range[1])
                    x, y = self._add_ue_within_ris_fov(name, distance)
                    self.net.add_ue(name, x, y, 0.0)
                    print(f"✓ Added UE {name} at ({x:.2f}, {y:.2f}) (RIS-aware placement)")
                else:
                    # Use random positioning
                    x, y = self.topology_helper.generate_position('ue')
                    self.net.add_ue(name, x, y, 0.0)
                    print(f"✓ Added UE {name} at ({x:.2f}, {y:.2f})")

            print("-" * 70)
            print(f"✓ Successfully added {num_ap + num_ris + num_ue} nodes to network")
            print(f"  Total nodes in network: {len(self.net.nodes)}")
            print("=" * 70 + "\n")

            self._save_network()

        except ValueError as e:
            print(f"Error: Invalid argument - {e}")
        except Exception as e:
            print(f"Error: {e}")

    def do_list(self, arg):
        """list nodes - Show network topology"""
        self.topology_helper.print_topology()
        print()
        self.net.list_nodes()

    def do_status(self, arg):
        """status - Show network status and active links
        Displays all nodes and any active link connections with their metrics.
        """
        print("\n" + "="*70)
        print("NETWORK STATUS")
        print("="*70)

        # Show nodes
        if not self.net.nodes:
            print("\n✗ No nodes in network")
        else:
            print(f"\nNODES ({len(self.net.nodes)}):")
            print("-" * 70)
            for node_name, node in self.net.nodes.items():
                node_type = type(node).__name__
                pos_str = f"({node.pos[0]:.1f}, {node.pos[1]:.1f}, {node.pos[2]:.1f})"
                print(f"\n  {node_name:<20} : {node_type:<12} at {pos_str}")

                # Show node-specific details with aligned labels
                if hasattr(node, 'freq'):
                    freq_ghz = node.freq / 1e9 if node.freq else 0
                    print(f"      Frequency:                      {freq_ghz:.2f} GHz")

                if hasattr(node, 'bandwidth_MHz'):
                    bw = node.bandwidth_MHz if node.bandwidth_MHz else 0
                    print(f"      Bandwidth:                      {bw:.1f} MHz")

                if hasattr(node, 'power_dBm'):
                    print(f"      Power:                          {node.power_dBm:.1f} dBm")

                if hasattr(node, 'N'):  # RIS specific
                    print(f"      RIS Elements:                   {node.N}")
                    if hasattr(node, 'bits'):
                        print(f"      Phase Bits:                     {node.bits}")

                if hasattr(node, 'noise_figure_dB'):
                    print(f"      Noise Figure:                   {node.noise_figure_dB:.1f} dB")

                if hasattr(node, 'antenna_gain_dBi'):
                    print(f"      Antenna Gain:                   {node.antenna_gain_dBi:.1f} dBi")

            # Show distances between all node pairs
            node_names = list(self.net.nodes.keys())
            if len(node_names) > 1:
                print(f"\nDISTANCES:")
                print("-" * 70)
                import numpy as np
                # Calculate max node name length for alignment
                max_node_len = max(len(n) for n in node_names)
                for i, node1_name in enumerate(node_names):
                    for node2_name in node_names[i+1:]:
                        node1 = self.net.nodes[node1_name]
                        node2 = self.net.nodes[node2_name]
                        distance = float(np.linalg.norm(node1.pos - node2.pos))
                        pair_str = f"{node1_name:<{max_node_len}} ↔ {node2_name:<{max_node_len}}"
                        print(f"  {pair_str}: {distance:>8.2f} m")

        # Show active links with indices
        active_links = self.net.get_active_links()
        if not active_links:
            print("\n✗ No active links")
        else:
            print(f"\nACTIVE LINKS ({len(active_links)}):")
            print("-" * 70)
            for idx, (link_name, link_info) in enumerate(active_links.items(), 1):
                print(f"\n  [{idx}] {link_name}")
                origin = link_info.get('source', 'unknown')
                origin_label = origin.capitalize() if isinstance(origin, str) else str(origin)
                print(f"      Source:                         {origin_label}")
                print(f"      SNR:                            {link_info['snr_dB']:>8.2f} dB")
                print(f"      Power:                          {link_info['pwr_dBm']:>8.2f} dBm")
                print(f"      Gain:                           {link_info['gain_dBi']:>8.2f} dBi")
                # Display angles with new format (Steering Angle with azimuths if available)
                if link_info.get('deflection_angle_deg') is not None:
                    print(f"      Steering Angle (Deflection):    {link_info['deflection_angle_deg']:>8.2f}°")
                    if link_info.get('incident_azimuth_deg') is not None:
                        print(f"      Incident Azimuth (AP→RIS):     {link_info['incident_azimuth_deg']:>8.2f}°")
                    if link_info.get('reflected_azimuth_deg') is not None:
                        print(f"      Reflected Azimuth (RIS→UE):    {link_info['reflected_azimuth_deg']:>8.2f}°")
                elif 'beam_angle_local' in link_info:
                    # Use beam_angle_local as steering angle when metadata unavailable
                    print(f"      Steering Angle (Deflection):    {link_info['beam_angle_local']:>8.2f}°")
                # Show as absolute penalty value (positive dB loss)
                penalty = abs(link_info['quant_loss_dB'])
                print(f"      Quant Penalty:                  {penalty:>8.2f} dB")

        print("\n" + "="*70 + "\n")

    def do_env(self, arg):
        """env [size W H [CX CY]] [bounds set XMIN XMAX YMIN YMAX] - Show or resize the environment"""

        parts = shlex.split(arg)
        env = self.net.environment
        bounds = env.bounds
        if not parts:
            width = bounds['x_max'] - bounds['x_min']
            height = bounds['y_max'] - bounds['y_min']
            wall_count = len(env.walls)
            print("\nEnvironment:")
            print("  Bounds:")
            print(f"    x: {bounds['x_min']} → {bounds['x_max']} ({width} m)")
            print(f"    y: {bounds['y_min']} → {bounds['y_max']} ({height} m)")
            print(f"  Size: {width:.1f} m × {height:.1f} m  (area {width*height:.1f} m²)")
            print(f"  Walls configured: {wall_count}")
            return

        cmd = parts[0].lower()
        if cmd == 'size':
            if len(parts) < 3:
                print("Usage: env size <width> <height> [<center_x> <center_y>]")
                return
            try:
                width = float(parts[1])
                height = float(parts[2])
                if width <= 0 or height <= 0:
                    raise ValueError("width and height must be positive")
                center_x = float(parts[3]) if len(parts) > 3 else (bounds['x_min'] + bounds['x_max']) / 2.0
                center_y = float(parts[4]) if len(parts) > 4 else (bounds['y_min'] + bounds['y_max']) / 2.0
            except ValueError as exc:
                print(f"Error: {exc}")
                return

            half_width = width / 2.0
            half_height = height / 2.0
            new_bounds = {
                'x_min': center_x - half_width,
                'x_max': center_x + half_width,
                'y_min': center_y - half_height,
                'y_max': center_y + half_height
            }
            env.bounds = new_bounds
            print("✓ Environment resized")
            print(f"  Center: ({center_x:.1f}, {center_y:.1f}), Width: {width:.1f}, Height: {height:.1f}")
            print(f"  New bounds: x={new_bounds['x_min']:.1f} → {new_bounds['x_max']:.1f}, "
                  f"y={new_bounds['y_min']:.1f} → {new_bounds['y_max']:.1f}")
            self._save_network()
            return

        if cmd == 'bounds':
            if len(parts) == 1:
                print("Bounds:")
                print(f"  x: {bounds['x_min']} → {bounds['x_max']}")
                print(f"  y: {bounds['y_min']} → {bounds['y_max']}")
                return

            if parts[1].lower() != 'set' or len(parts) != 6:
                print("Usage: env bounds set <x_min> <x_max> <y_min> <y_max>")
                return

            try:
                x_min = float(parts[2])
                x_max = float(parts[3])
                y_min = float(parts[4])
                y_max = float(parts[5])
            except ValueError:
                print("Error: bounds must be numeric values")
                return

            if x_min >= x_max or y_min >= y_max:
                print("Error: min values must be less than max values")
                return

            env.bounds = {
                'x_min': x_min,
                'x_max': x_max,
                'y_min': y_min,
                'y_max': y_max
            }
            print("✓ Environment bounds updated")
            print(f"  x: {x_min} → {x_max}")
            print(f"  y: {y_min} → {y_max}")
            self._save_network()
            return

        print("Usage: env [size <width> <height> [<center_x> <center_y>]] | "
              "env bounds [set <x_min> <x_max> <y_min> <y_max>]")

    def do_ap(self, arg):
        """ap <name>|list [show]|ap <name> set key=value ... - Inspect or update AP settings"""
        parts = shlex.split(arg)
        if not parts:
            self._print_ap_list()
            return

        if parts[0].lower() == 'list':
            self._print_ap_list()
            return

        ap_name = parts[0]
        ap_node = self.net.get(ap_name)
        if ap_node is None or type(ap_node).__name__ != 'AccessPoint':
            print(f"Error: Access Point '{ap_name}' not found")
            return

        if len(parts) == 1 or (len(parts) > 1 and parts[1].lower() == 'show'):
            self._print_ap_details(ap_node)
            return

        if parts[1].lower() != 'set' or len(parts) < 3:
            print("Usage: ap <name> set key=value [key=value ...]")
            return

        key_map = {
            'power': ('power_dBm', float),
            'freq': ('freq', float),
            'frequency': ('freq', float),
            'bandwidth': ('bandwidth_MHz', float),
            'bw': ('bandwidth_MHz', float),
            'gain': ('antenna_gain_dBi', float),
            'antenna_gain': ('antenna_gain_dBi', float),
            'noise': ('noise_figure_dB', float),
            'noise_figure': ('noise_figure_dB', float),
            'target_snr': ('target_snr_dB', float),
            'power_max': ('power_dBm_max', float),
            'power_min': ('power_dBm_min', float),
            'pos': ('pos', self._parse_position_arg),
            'position': ('pos', self._parse_position_arg)
        }

        applied = []
        for token in parts[2:]:
            if '=' not in token:
                print(f"Skipping invalid token: {token}")
                continue
            key, value = token.split('=', 1)
            key = key.lower()
            if key not in key_map:
                print(f"Unknown parameter: {key}")
                continue
            attr, parser = key_map[key]
            try:
                parsed = parser(value) if callable(parser) else parser
            except ValueError as exc:
                print(f"Error parsing {key}: {exc}")
                continue
            if attr == 'pos':
                ap_node.pos = parsed
            else:
                setattr(ap_node, attr, parsed)
            applied.append((key, attr, parsed))

        if not applied:
            print("No valid parameters were updated")
            return

        for key, attr, parsed in applied:
            if attr == 'pos':
                pos = parsed
                print(f"  ✓ Position set to ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
            elif attr in ('freq',):
                print(f"  ✓ {key} set to {parsed} Hz")
            elif attr in ('bandwidth_MHz',):
                print(f"  ✓ {key} set to {parsed:.2f} MHz")
            else:
                suffix = ' dBm' if attr.startswith('power') or attr == 'noise_figure_dB' else ''
                print(f"  ✓ {key} set to {parsed}{suffix}")

        self._save_network()

    def do_ris(self, arg):
        """ris <name>|list [show]|ris <name> set key=value ... - Inspect or update RIS settings"""
        parts = shlex.split(arg)
        if not parts:
            self._print_ris_list()
            return

        if parts[0].lower() == 'list':
            self._print_ris_list()
            return

        ris_name = parts[0]
        ris_node = self.net.get(ris_name)
        if ris_node is None or type(ris_node).__name__ != 'RIS':
            print(f"Error: RIS '{ris_name}' not found")
            return

        if len(parts) == 1 or (len(parts) > 1 and parts[1].lower() == 'show'):
            self._print_ris_details(ris_node)
            return

        if parts[1].lower() != 'set' or len(parts) < 3:
            print("Usage: ris <name> set key=value [key=value ...]")
            return

        key_map = {
            'n': ('N', int),
            'size': ('N', int),
            'grid': ('N', int),
            'bits': ('bits', int),
            'max_angle': ('max_angle_deg', float),
            'fov': ('max_angle_deg', float),
            'normal': ('normal_angle_deg', float),
            'freq': ('freq', float),
            'active': ('active_mode', self._parse_bool),
            'active_mode': ('active_mode', self._parse_bool),
            'amp_gain': ('amplifier_gain', float),
            'efficiency': ('element_efficiency', float),
            'phase_error': ('phase_rms', float),
            'phase_rms': ('phase_rms', float),
            'amp_std': ('amp_std', float),
            'noise': ('noise_floor', float),
            'noise_floor': ('noise_floor', float),
            'coupling': ('coupling_enabled', self._parse_bool),
            'pos': ('pos', self._parse_position_arg),
            'position': ('pos', self._parse_position_arg)
        }

        applied = []
        geometry_touched = False
        for token in parts[2:]:
            if '=' not in token:
                print(f"Skipping invalid token: {token}")
                continue
            key, value = token.split('=', 1)
            key = key.lower()
            if key not in key_map:
                print(f"Unknown parameter: {key}")
                continue
            attr, parser = key_map[key]
            try:
                parsed = parser(value) if callable(parser) else parser
            except ValueError as exc:
                print(f"Error parsing {key}: {exc}")
                continue
            if attr == 'pos':
                ris_node.pos = parsed
                geometry_touched = True
            else:
                setattr(ris_node, attr, parsed)
                if attr == 'N':
                    geometry_touched = True
            applied.append((key, attr, parsed))

        if geometry_touched:
            ris_node.update_geometry()

        if not applied:
            print("No valid parameters were updated")
            return

        for key, attr, parsed in applied:
            if attr == 'pos':
                pos = parsed
                print(f"  ✓ Position set to ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
            elif attr in ('N', 'bits', 'max_angle_deg', 'normal_angle_deg'):
                print(f"  ✓ {key} set to {parsed}")
            elif attr in ('freq',):
                print(f"  ✓ {key} set to {parsed} Hz")
            else:
                print(f"  ✓ {key} set to {parsed}")

        self._save_network()

    def do_ue(self, arg):
        """ue <name>|list [show]|ue <name> set key=value ... - Inspect or update UE settings"""
        parts = shlex.split(arg)
        if not parts:
            self._print_ue_list()
            return

        if parts[0].lower() == 'list':
            self._print_ue_list()
            return

        ue_name = parts[0]
        ue_node = self.net.get(ue_name)
        if ue_node is None or type(ue_node).__name__ != 'UE':
            print(f"Error: UE '{ue_name}' not found")
            return

        if len(parts) == 1 or (len(parts) > 1 and parts[1].lower() == 'show'):
            self._print_ue_details(ue_node)
            return

        if parts[1].lower() != 'set' or len(parts) < 3:
            print("Usage: ue <name> set key=value [key=value ...]")
            return

        key_map = {
            'gain': ('antenna_gain_dBi', float),
            'antenna_gain': ('antenna_gain_dBi', float),
            'noise': ('noise_figure_dB', float),
            'noise_figure': ('noise_figure_dB', float),
            'max_angle': ('max_angle_deg', float),
            'fov': ('max_angle_deg', float),
            'normal': ('normal_angle_deg', float),
            'feedback': ('feedback_enabled', self._parse_bool),
            'pos': ('pos', self._parse_position_arg),
            'position': ('pos', self._parse_position_arg)
        }

        applied = []
        for token in parts[2:]:
            if '=' not in token:
                print(f"Skipping invalid token: {token}")
                continue
            key, value = token.split('=', 1)
            key = key.lower()
            if key not in key_map:
                print(f"Unknown parameter: {key}")
                continue
            attr, parser = key_map[key]
            try:
                parsed = parser(value) if callable(parser) else parser
            except ValueError as exc:
                print(f"Error parsing {key}: {exc}")
                continue
            if attr == 'pos':
                ue_node.pos = parsed
            else:
                setattr(ue_node, attr, parsed)
            applied.append((key, attr, parsed))

        if not applied:
            print("No valid parameters were updated")
            return

        for key, attr, parsed in applied:
            if attr == 'pos':
                pos = parsed
                print(f"  ✓ Position set to ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
            else:
                print(f"  ✓ {key} set to {parsed}")

        self._save_network()

    def _print_ap_list(self):
        nodes = [n for n in self.net.nodes.values() if type(n).__name__ == 'AccessPoint']
        if not nodes:
            print("No Access Points configured")
            return
        print("\nAccess Points:")
        for node in nodes:
            pos = node.pos
            print(f"  {node.name:<10} pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) "
                  f"power={node.power_dBm:.1f} dBm freq={node.freq/1e9:.2f} GHz")

    def _print_ris_list(self):
        nodes = [n for n in self.net.nodes.values() if type(n).__name__ == 'RIS']
        if not nodes:
            print("No RIS surfaces configured")
            return
        print("\nRIS Surfaces:")
        for node in nodes:
            pos = node.pos
            print(f"  {node.name:<10} pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) "
                  f"N={node.N} bits={node.bits} max_angle=±{node.max_angle_deg}°")

    def _print_ue_list(self):
        nodes = [n for n in self.net.nodes.values() if type(n).__name__ == 'UE']
        if not nodes:
            print("No UEs configured")
            return
        print("\nUser Equipment:")
        for node in nodes:
            pos = node.pos
            print(f"  {node.name:<10} pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f}) "
                  f"FOV=±{node.max_angle_deg}°")

    def _print_ap_details(self, node):
        pos = node.pos
        print(f"\n{node.name} (Access Point)")
        print(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
        print(f"  Power: {node.power_dBm:.1f} dBm")
        print(f"  Frequency: {node.freq/1e9:.3f} GHz")
        print(f"  Bandwidth: {node.bandwidth_MHz:.1f} MHz")
        print(f"  Antenna Gain: {node.antenna_gain_dBi:.1f} dBi")
        print(f"  Noise Figure: {node.noise_figure_dB:.1f} dB")
        print(f"  Target SNR: {node.target_snr_dB:.1f} dB")

    def _print_ris_details(self, node):
        pos = node.pos
        print(f"\n{node.name} (RIS)")
        print(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
        print(f"  Grid: {node.N} × {node.N} elements")
        print(f"  Bits: {node.bits}")
        print(f"  Frequency: {node.freq/1e9:.3f} GHz")
        print(f"  FOV: ±{node.max_angle_deg}° (normal={node.normal_angle_deg}°)")
        print(f"  Active mode: {'Yes' if node.active_mode else 'No'}")
        print(f"  Amplifier gain: {node.amplifier_gain:.2f}")
        print(f"  Phase RMS: {node.phase_rms:.2f}°")

    def _print_ue_details(self, node):
        pos = node.pos
        print(f"\n{node.name} (UE)")
        print(f"  Position: ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")
        print(f"  Antenna Gain: {node.antenna_gain_dBi:.1f} dBi")
        print(f"  Noise Figure: {node.noise_figure_dB:.1f} dB")
        print(f"  FOV: ±{node.max_angle_deg}° (normal={node.normal_angle_deg}°)")
        print(f"  Feedback: {'Enabled' if node.feedback_enabled else 'Disabled'}")

    def _parse_position_arg(self, value):
        parts = value.replace(',', ' ').split()
        if len(parts) not in (2, 3):
            raise ValueError("position must have 2 or 3 values")
        numbers = [float(p) for p in parts]
        if len(numbers) == 2:
            numbers.append(0.0)
        return np.array(numbers)

    def _parse_bool(self, value):
        norm = value.strip().lower()
        if norm in {'true', '1', 'yes', 'on', 'enabled'}:
            return True
        if norm in {'false', '0', 'no', 'off', 'disabled'}:
            return False
        raise ValueError("must be a boolean (true/false)")

    def do_links(self, arg):
        """links - Show active connection links.
        Use 'links plot <index|name> [--out output.png]' to generate the top-down geometry for one."""
        active_links = self.net.get_active_links()
        parts = shlex.split(arg) if arg else []

        if parts and parts[0].lower() == 'plot':
            self._handle_links_plot(parts[1:], active_links)
            return

        print("\n" + "="*70)
        print("ACTIVE LINKS")
        print("="*70)

        ordered_links = self._ordered_active_link_items(active_links)

        if not active_links:
            print("\nNo active links")
        else:
            print(f"\nACTIVE LINKS ({len(active_links)}):")
            print("-" * 70)
            for idx, (link_name, link_info) in enumerate(ordered_links, 1):
                print(f"\n  [{idx}] {link_name}")
                origin = link_info.get('source', 'unknown')
                origin_label = origin.capitalize() if isinstance(origin, str) else str(origin)
                print(f"      Source:                         {origin_label}")
                print(f"      SNR:                            {link_info['snr_dB']:>8.2f} dB")
                print(f"      Power:                          {link_info['pwr_dBm']:>8.2f} dBm")
                print(f"      Gain:                           {link_info['gain_dBi']:>8.2f} dBi")
                # Display angles with new format (Steering Angle with azimuths if available)
                if link_info.get('deflection_angle_deg') is not None:
                    print(f"      Steering Angle (Deflection):    {link_info['deflection_angle_deg']:>8.2f}°")
                    if link_info.get('incident_azimuth_deg') is not None:
                        print(f"      Incident Azimuth (AP→RIS):     {link_info['incident_azimuth_deg']:>8.2f}°")
                    if link_info.get('reflected_azimuth_deg') is not None:
                        print(f"      Reflected Azimuth (RIS→UE):    {link_info['reflected_azimuth_deg']:>8.2f}°")
                elif 'beam_angle_local' in link_info:
                    # Use beam_angle_local as steering angle when metadata unavailable
                    print(f"      Steering Angle (Deflection):    {link_info['beam_angle_local']:>8.2f}°")
                # Show as absolute penalty value (positive dB loss)
                penalty = abs(link_info['quant_loss_dB'])
                print(f"      Quant Penalty:                  {penalty:>8.2f} dB")

        print("\n" + "="*70 + "\n")

    def _handle_links_plot(self, args, active_links):
        """Handle 'links plot' requests and forward to the geometry renderer."""
        if not active_links:
            print("✗ No active links to plot")
            return

        target = None
        output_path = None
        i = 0
        while i < len(args):
            token = args[i]
            if token == '--out' and i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
                continue
            if target is None:
                target = token
                i += 1
                continue
            print(f"Unexpected extra argument: {token}")
            return

        if not target:
            print("Usage: links plot <index|name> [--out output.png]")
            return

        items = self._ordered_active_link_items(active_links)
        link_index = None
        link_name = None
        link_info = None

        if target.isdigit():
            idx = int(target)
            if idx < 1 or idx > len(items):
                print(f"✗ Invalid link index. Available links: [1] to [{len(items)}]")
                return
            link_index = idx
            link_name, link_info = items[idx - 1]
        else:
            matches = [idx for idx, (name, _) in enumerate(items) if name.lower() == target.lower()]
            if not matches:
                print(f"✗ No link named '{target}' found")
                return
            if len(matches) > 1:
                print(f"✗ Link name '{target}' is ambiguous (multiple matches). Use the numeric index.")
                return
            link_index = matches[0] + 1
            link_name, link_info = items[matches[0]]

        self._plot_active_link_geometry(link_index, link_name, link_info, output_path=output_path)

    def _ordered_active_link_items(self, active_links):
        """Return active link tuples in a deterministic order for indexing."""
        return sorted(active_links.items(), key=lambda item: item[0].casefold())

    def _plot_active_link_geometry(self, link_index, link_name, link_info, output_path=None):
        """Plot the top-down geometry for an active link and save to disk."""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            print("✗ matplotlib not installed. Install with: pip install matplotlib")
            return

        ap_node = self.net.get(link_info.get('ap'))
        ris_node = self.net.get(link_info.get('ris'))
        ue_node = self.net.get(link_info.get('ue'))

        if not (ap_node and ris_node and ue_node):
            print("✗ Unable to locate AP/RIS/UE nodes for this link")
            return

        ap_xy = np.array(ap_node.pos, dtype=float)[:2]
        ris_xy = np.array(ris_node.pos, dtype=float)[:2]
        ue_xy = np.array(ue_node.pos, dtype=float)[:2]

        theta_in_rad = math.atan2(ap_xy[1] - ris_xy[1], ap_xy[0] - ris_xy[0])
        theta_out_rad = math.atan2(ue_xy[1] - ris_xy[1], ue_xy[0] - ris_xy[0])
        angle_diff = theta_out_rad - theta_in_rad
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        theta_out_norm = theta_in_rad + angle_diff

        abs_diff_deg = math.degrees(abs(angle_diff))
        mid_ang = theta_in_rad + angle_diff / 2

        stored_deflection = link_info.get('deflection_angle_deg')
        if stored_deflection is None:
            stored_deflection = link_info.get('beam_angle_local')
        if stored_deflection is not None:
            try:
                stored_deflection = float(stored_deflection)
            except (TypeError, ValueError):
                stored_deflection = abs_diff_deg
        else:
            stored_deflection = abs_diff_deg
        deflection_display = abs(stored_deflection)

        arc_radius = max(1.0, min(3.0, np.linalg.norm(ap_xy - ris_xy) * 0.35))
        theta_vals = np.linspace(theta_in_rad, theta_out_norm, 200)
        arc_x = ris_xy[0] + arc_radius * np.cos(theta_vals)
        arc_y = ris_xy[1] + arc_radius * np.sin(theta_vals)

        ris_normal_deg = link_info.get(
            'ris_normal_angle',
            getattr(ris_node, 'normal_angle_deg', 0.0)
        )
        if ris_normal_deg is None:
            ris_normal_deg = 0.0
        ris_normal_rad = math.radians(ris_normal_deg)
        fov_half_deg = abs(getattr(ris_node, 'max_angle_deg', 60.0) or 60.0)
        fov_radius = max(4.0, np.linalg.norm(ue_xy - ris_xy))
        fov_angles = np.linspace(
            ris_normal_rad - math.radians(fov_half_deg),
            ris_normal_rad + math.radians(fov_half_deg),
            200
        )
        fov_x = [ris_xy[0]] + list(ris_xy[0] + fov_radius * np.cos(fov_angles)) + [ris_xy[0]]
        fov_y = [ris_xy[1]] + list(ris_xy[1] + fov_radius * np.sin(fov_angles)) + [ris_xy[1]]

        ap_ris_dist = np.linalg.norm(ap_xy - ris_xy)
        ris_ue_dist = np.linalg.norm(ue_xy - ris_xy)

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(*ap_xy, s=140, color='green', marker='s', label='AP (Source)', zorder=5)
        ax.scatter(*ris_xy, s=200, color='orange', marker='^', label='RIS', zorder=5)
        ax.scatter(*ue_xy, s=140, color='red', marker='o', label='UE (Target)', zorder=5)
        ax.plot([ris_xy[0], ap_xy[0]], [ris_xy[1], ap_xy[1]], 'g--', lw=2, label='AP→RIS ray', alpha=0.7)
        ax.plot([ris_xy[0], ue_xy[0]], [ris_xy[1], ue_xy[1]], 'r--', lw=2, label='RIS→UE ray', alpha=0.7)
        self._annotate_distance(ax, ap_xy, ris_xy, ap_ris_dist, color='green', offset=0.2)
        self._annotate_distance(ax, ris_xy, ue_xy, ris_ue_dist, color='red', offset=-0.2)
        ax.plot(arc_x, arc_y, color='purple', lw=2.5, label=f'Azimuth deflection: {deflection_display:.2f}°')
        ax.fill(fov_x, fov_y, color='gray', alpha=0.15, label=f'RIS FOV ±{fov_half_deg:.1f}°')
        for sign in (-1, 1):
            edge_ang = ris_normal_rad + sign * math.radians(fov_half_deg)
            ax.plot(
                [ris_xy[0], ris_xy[0] + fov_radius * math.cos(edge_ang)],
                [ris_xy[1], ris_xy[1] + fov_radius * math.sin(edge_ang)],
                color='gray',
                ls=':',
                lw=1.5,
                alpha=0.6
            )
        ax.text(
            ris_xy[0] + arc_radius * math.cos(mid_ang),
            ris_xy[1] + arc_radius * math.sin(mid_ang),
            f"{deflection_display:.2f}°",
            color='purple',
            fontsize=10,
            fontweight='bold'
        )

        def _fmt_number(value, precision=2):
            if value is None:
                return 'N/A'
            try:
                return f"{float(value):.{precision}f}"
            except (TypeError, ValueError):
                return str(value)

        beam_angle_abs = link_info.get('beam_angle_absolute')
        stats = [
            f"SNR: {_fmt_number(link_info.get('snr_dB'))} dB",
            f"Power: {_fmt_number(link_info.get('pwr_dBm'))} dBm",
            f"Deflection: {deflection_display:.2f}°",
            f"Beam angle: {_fmt_number(beam_angle_abs)}°"
        ]
        ax.text(
            0.02,
            0.98,
            "\n".join(stats),
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.3')
        )

        margin = 1.5
        xs = [ap_xy[0], ris_xy[0], ue_xy[0]]
        ys = [ap_xy[1], ris_xy[1], ue_xy[1]]
        ax.set_xlim(min(xs) - margin, max(xs) + margin)
        ax.set_ylim(min(ys) - margin, max(ys) + margin)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        ax.legend(loc='lower right', fontsize=10, framealpha=0.9, edgecolor='black')
        ax.set_title(f"Link Geometry: {link_name}", fontsize=12, pad=10)
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Y (m)')
        fig.tight_layout()

        slug = ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in link_name)
        if not slug:
            slug = f"link{link_index}"

        if output_path:
            plot_path = Path(output_path)
        else:
            plot_path = Path(f"link_{link_index}_{slug}_geometry.png")
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close(fig)

        print(f"✓ Geometry plot saved to {plot_path}")

    def _annotate_distance(self, ax, start, end, dist, color='black', offset=0.0):
        """Annotate the midpoint between start and end with the given distance."""
        start = np.array(start, dtype=float)
        end = np.array(end, dtype=float)
        midpoint = (start + end) / 2
        direction = end - start
        perp = np.array([-direction[1], direction[0]])
        norm = np.linalg.norm(perp)
        if norm > 0:
            perp /= norm
        text_pos = midpoint + perp * offset
        ax.text(
            text_pos[0],
            text_pos[1],
            f"{dist:.2f} m",
            fontsize=9,
            color=color,
            ha='center',
            va='center',
            bbox=dict(facecolor='white', alpha=0.8, edgecolor=color, boxstyle='round,pad=0.2')
        )

    def do_clear(self, arg):
        """clear [net|links] - Clear network or links

        Usage:
            clear           - Clear entire network (nodes + links) [DEFAULT]
            clear net       - Clear entire network (nodes + links)
            clear links     - Clear active links only (keep nodes)
        """
        parts = arg.split() if arg else []

        # Default behavior: clear net (entire network)
        if not parts or parts[0].lower() == 'net':
            if not self.net.nodes:
                print("Network is already empty")
                return
            self.net.nodes.clear()
            self.net.clear_links()
            if hasattr(self.net, 'last_connect_result'):
                self.net.last_connect_result = None
            if hasattr(self.net, 'last_sweep_result'):
                self.net.last_sweep_result = None
            self._save_network()
            print(f"✓ Cleared entire network (nodes + links)")

        elif parts[0].lower() == 'links':
            if not self.net.get_active_links():
                print("No active links to clear")
                return
            num_links = len(self.net.get_active_links())
            self.net.active_links.clear()
            if hasattr(self.net, 'last_connect_result'):
                self.net.last_connect_result = None
            if hasattr(self.net, 'last_sweep_result'):
                self.net.last_sweep_result = None
            self._save_network()
            print(f"✓ Cleared {num_links} active link(s) (nodes kept)")
        else:
            print(f"Error: Unknown clear option '{parts[0]}'. Use 'clear net' or 'clear links'")

    # =====================================================================
    # Connection & Control Commands
    # =====================================================================

    def do_connect(self, arg):
        """connect [ap] [ris] [ue] [beam_angle_deg] [--modulation mod] [--no-waveform] [--no-feedback] [--sweep fov step] [--algo algorithm] [--ml-predictor predictor] [--use-mock true|false] [--mock-trajectory type]
        Unified connect command: single-angle measurement OR multi-angle beam optimization via --sweep flag.

        SINGLE-ANGLE MODE (default, traditional behavior):
            connect ap1 ris1 ue1                           # Auto-compute specular angle, single measurement
            connect ap1 ris1 ue1 30                        # Beam at 30°, real signal
            connect ap1 ris1 ue1 30 --modulation 16QAM     # Beam at 30°, 16QAM modulation
            connect ap1 ris1 ue1 30 --no-waveform          # Beam at 30°, physics-only
            connect ap1 ris1 ue1 30 --no-feedback          # No closed-loop adaptation

        MULTI-ANGLE SWEEP MODE (explicit --sweep flag):
            connect ap1 ris1 ue1 --sweep 60 10             # Sweep ±60° at 10° steps (linear algo)
            connect ap1 ris1 ue1 --sweep 60 10 --algo center-out   # Two-phase coarse-fine sweep
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor xgb  # ML-guided sweep
            connect ap1 ris1 ue1 --sweep 90 5 --modulation 16QAM  # Sweep with signal-level sim

        OPENCV VISION SWEEP (synthetic camera for testing):
            connect ap1 ris1 ue1 --sweep 60 10 --algo opencv --use-mock true  # Mock camera with circular motion
            connect ap1 ris1 ue1 --sweep 60 10 --algo opencv --use-mock true --mock-trajectory linear  # Linear motion
            connect ap1 ris1 ue1 --sweep 60 10 --algo opencv  # Real camera (requires --use-mock false or omit flag)

        AVAILABLE SWEEP ALGORITHMS (use with --sweep):
            linear (aliases: brute-force)
                Exhaustive search: tests all beam angles across FOV at specified resolution.
            coarse-fine (aliases: two-phase, center-out, adaptive)
                Two-phase sweep: coarse center-out search, then fine refinement. ~30% more efficient.
            directional-exhaustive (aliases: directional, exhaustive)
                Exhaustive sweep of all codebook angles for all network links with directional SNR.
            ml (aliases: ml-guided)
                ML-guided beam sweep: validates top ML-predicted angles through measurement.
            opencv (aliases: vision, aruco)
                Vision-based beam sweep: uses ArUco marker detection to track UE position from camera.

        ML PREDICTORS (use with --ml-predictor when algo is ml or ml-guided):
            rf          Random Forest (recommended, best balance of speed/accuracy)
            xgb         XGBoost (high accuracy, slower)
            svr         Support Vector Regression (very high accuracy)
            dt          Decision Tree (interpretable, moderate accuracy)
            knn         K-Nearest Neighbors (local pattern recognition)
            lr          Linear Regression (fast, simple baseline)

        MOCK CAMERA OPTIONS (use with --algo opencv):
            --use-mock true|false       Enable/disable mock camera (default: false)
            --mock-trajectory type      Trajectory type: circular, linear, random, static (default: circular)
            --r-cw path/to/matrix.npy   Camera-to-world rotation matrix (.npy file, optional)
            --t-cw path/to/vector.npy   Camera-to-world translation vector (.npy file, optional)
                                        Note: Defaults to identity transform for mock camera

        Examples:
            connect                                        # Auto-detect nodes, single angle (specular)
            connect ap1                                    # Auto-detect RIS/UE, single angle
            connect ap1 ris1 ue1                           # Auto-compute angle, single measurement
            connect ap1 ris1 ue1 30                        # Single angle at 30°
            connect ap1 ris1 ue1 --sweep 60 10             # Multi-angle sweep ±60° at 10° (linear)
            connect ap1 ris1 ue1 --sweep 60 10 --algo center-out  # Coarse-fine sweep
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor xgb  # ML-guided with XGBoost
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor knn  # ML-guided with KNN
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml  # ML-guided sweep with default predictor
            connect ap1 ris1 ue1 --sweep 60 10 --algo opencv --use-mock true  # OpenCV with mock camera
            connect ap1 ris1 ue1 --sweep 60 10 --algo opencv --use-mock true --mock-trajectory linear  # Linear motion

        Tip: Use TAB completion with --algo and --ml-predictor flags to see available options.
        Default: 100% real signal-level simulation (generates actual waveforms, measures SNR and SER)
        """
        # Parse arguments using connection handler
        ap, ris, ue, remaining_parts, error_msg = self.connection_handler.parse_connect_arguments(arg)
        if error_msg:
            print(error_msg)
            return

        # Parse flags using connection handler
        flags_result = self.connection_handler.parse_flags(remaining_parts)
        if flags_result['error_msg']:
            print(flags_result['error_msg'])
            return

        enable_feedback = flags_result['enable_feedback']
        use_waveform = flags_result['use_waveform']
        modulation = flags_result['modulation']
        fov = flags_result['fov']
        step = flags_result['step']
        algo_name = flags_result['algo_name']
        ml_predictor = flags_result['ml_predictor']
        angle = flags_result['angle']
        seed = flags_result['seed']
        metric = flags_result.get('metric', 'snr')
        enable_codebook_validation = flags_result['enable_codebook_validation']
        codebook_increment = flags_result['codebook_increment']
        codebook_neighbors = flags_result['codebook_neighbors']
        include_predicted_angle = flags_result['include_predicted_angle']
        codebook_start = flags_result['codebook_start']
        codebook_end = flags_result['codebook_end']
        codebook_step = flags_result['codebook_step']
        use_mock = flags_result.get('use_mock', False)
        mock_trajectory = flags_result.get('mock_trajectory', 'circular')
        r_cw = flags_result.get('r_cw', None)
        t_cw = flags_result.get('t_cw', None)

        # Determine mode: single-angle vs sweep
        if fov is not None:
            # Multi-angle sweep mode
            return self._do_connect_sweep(ap, ris, ue, fov, step, algo_name, ml_predictor,
                                         enable_feedback, use_waveform, modulation, seed,
                                         metric, enable_codebook_validation, codebook_increment,
                                         codebook_neighbors, include_predicted_angle,
                                         codebook_start, codebook_end, codebook_step, use_mock, mock_trajectory,
                                         r_cw, t_cw)
        else:
            # Single-angle connect mode
            return self._do_single_connect(ap, ris, ue, angle, enable_feedback, use_waveform,
                                          modulation, seed)

    def _do_single_connect(self, ap, ris, ue, angle, enable_feedback, use_waveform, modulation, seed):
        """Execute single-angle connect measurement"""
        res = self.connection_handler.execute_single_connect(ap, ris, ue, angle, enable_feedback, use_waveform, modulation, seed)
        if res is None:
            return

        # Print detailed results using connection handler
        self.connection_handler.print_connect_results(res, ap, ris, ue, enable_feedback, use_waveform, modulation, angle, seed)

        # Create and save connection record
        connection_record = self.connection_handler.create_connection_record(ap, ris, ue, res, angle, seed, enable_feedback, use_waveform, modulation)
        self.net.last_connect_result = sanitize_for_json(connection_record)

    def _do_connect_sweep(self, ap, ris, ue, fov, step, algo_name, ml_predictor, enable_feedback, use_waveform, modulation, seed, metric='snr', enable_codebook_validation=False, codebook_increment=5.0, codebook_neighbors=1, include_predicted_angle=True, codebook_start=10.0, codebook_end=60.0, codebook_step=10.0, use_mock=False, mock_trajectory='circular', r_cw=None, t_cw=None):
        """Execute multi-angle sweep within unified connect command"""
        # Execute sweep using connection handler
        out = self.connection_handler.execute_sweep(ap, ris, ue, fov, step, algo_name, ml_predictor, enable_feedback, use_waveform, modulation, seed, metric=metric, enable_codebook_validation=enable_codebook_validation, codebook_increment=codebook_increment, codebook_neighbors=codebook_neighbors, include_predicted_angle=include_predicted_angle, codebook_start=codebook_start, codebook_end=codebook_end, codebook_step=codebook_step, use_mock=use_mock, mock_trajectory=mock_trajectory, r_cw=r_cw, t_cw=t_cw)
        if out is None:
            return

        try:
            # Print sweep results using connection handler
            best_angles_info = self.connection_handler.print_sweep_results(out, fov, step, ap, ris, ue, algo_name, metric=metric)

            # Create sweep record and update network using connection handler
            self.connection_handler.create_sweep_record_and_link(ap, ris, ue, out, best_angles_info, fov, step, algo_name, use_waveform, modulation)

        except ValueError as e:
            # Clean error output for FOV violations
            print(f"\n✗ {e}\n")
        except Exception as e:
            print(f"\nError during sweep: {e}\n")

    def do_sweep(self, arg):
        """sweep ap ris ue [fov step] [--algo algorithm] [--ml-predictor type] [--modulation mod] [--no-waveform]
        DEPRECATED: Use 'connect --sweep' instead. This command now delegates to the unified connect.

        Examples:
            sweep AP1 R1 UE1 60 10                              # Equivalent to: connect AP1 R1 UE1 --sweep 60 10
            sweep AP1 R1 UE1 60 10 --algo center-out             # Equivalent to: connect AP1 R1 UE1 --sweep 60 10 --algo center-out
            sweep AP1 R1 UE1 60 10 --modulation 16QAM            # Equivalent to: connect AP1 R1 UE1 --sweep 60 10 --modulation 16QAM

        For new code, use 'connect --sweep' directly:
            connect AP1 R1 UE1 --sweep 60 10
            connect AP1 R1 UE1 --sweep 60 10 --algo center-out
            connect AP1 R1 UE1 --sweep 60 10 --algo ml --ml-predictor xgb
        """
        # Parse basic arguments
        parts = shlex.split(arg) if arg else []
        if len(parts) < 3:
            print('usage: sweep ap ris ue [fov step] [--algo algorithm] [--ml-predictor type]')
            print('(Use "connect --sweep" for new code)')
            return

        ap, ris, ue = parts[0], parts[1], parts[2]
        fov = float(parts[3]) if len(parts) > 3 else 60.0
        step = float(parts[4]) if len(parts) > 4 else 10.0

        # Reconstruct as connect --sweep command
        connect_arg = f"{ap} {ris} {ue} --sweep {fov} {step}"

        # Pass remaining flags
        for flag in ['--algo', '--ml-predictor', '--modulation', '--no-waveform', '--no-feedback']:
            if flag in parts:
                idx = parts.index(flag)
                if idx + 1 < len(parts):
                    connect_arg += f" {flag} {parts[idx + 1]}"
                else:
                    connect_arg += f" {flag}"

        # Delegate to unified connect command
        print("(delegating to: connect " + connect_arg + ")\n")
        self.do_connect(connect_arg)


    def do_stream(self, arg):
        """stream [ap] [ris] [ue] --file path [--modulation MOD] [--chunks N] [--num-symbols N]
        Smart stream (like smart connect). If AP/RIS/UE are omitted, auto-detect when unambiguous.
        Streams a binary/video file through the AP→RIS→UE link using the waveform workflow (Example 15).
        Options:
          --file PATH         Payload file (default streaming/video.mp4)
          --modulation MOD    QPSK | 16QAM | 64QAM (default 16QAM)
          --chunks N          Chunks to stream (default 6)
          --num-symbols N     Symbols per chunk (default 2000)
          --symbol-rate Hz    Symbol rate (default 2e6)
          --sample-rate Hz    Sample rate (default 20e6)
          --sweep-fov deg     Beam sweep FOV (default 80)
          --sweep-step deg    Beam sweep step (default 5)
          --ml-top-k N        ML sweep suggestions (default 2)
          --quality-metrics   Show per-chunk quality metrics (SNR, SER, BER)
          --beam-adaptive     Enable adaptive beam steering during streaming
        """
        parts = shlex.split(arg) if arg else []
        node_tokens = []
        file_path_arg = None
        idx = 0
        while idx < len(parts) and not parts[idx].startswith('--'):
            # Stop if we encounter a file path (contains / or \)
            if '/' in parts[idx] or '\\' in parts[idx]:
                file_path_arg = parts[idx]
                idx += 1
                break
            node_tokens.append(parts[idx])
            idx += 1
        opts = parts[idx:]

        # Gather nodes
        aps = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'AccessPoint']
        riss = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'RIS']
        ues = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'UE']

        ap = node_tokens[0] if len(node_tokens) > 0 else None
        ris = node_tokens[1] if len(node_tokens) > 1 else None
        ue = node_tokens[2] if len(node_tokens) > 2 else None

        def _resolve(name, candidates):
            if not name:
                return None
            if name in candidates:
                return name
            lower = name.lower()
            for cand in candidates:
                if cand.lower() == lower:
                    return cand
            return name  # leave as-is; validation later

        ap = _resolve(ap, aps)
        ris = _resolve(ris, riss)
        ue = _resolve(ue, ues)

        # Auto-fill missing nodes (smart detection)
        if ap is None:
            if len(aps) == 1:
                ap = aps[0]
            elif len(aps) == 0:
                print("Error: No Access Points available in network")
                return
            else:
                print("Error: Ambiguous AP selection. Specify one of:", ", ".join(aps))
                return

        if ris is None:
            if len(riss) == 1:
                ris = riss[0]
            elif len(riss) == 0:
                print("Error: No RIS nodes available in network")
                return
            else:
                print(f"Error: Ambiguous RIS selection for AP '{ap}'. Options:", ", ".join(riss))
                return

        if ue is None:
            if len(ues) == 1:
                ue = ues[0]
            elif len(ues) == 0:
                print("Error: No UE nodes available in network")
                return
            else:
                print(f"Error: Ambiguous UE selection for {ap}→{ris}. Options:", ", ".join(ues))
                return

        video_path = None
        modulation = "16QAM"
        chunk_limit = 6
        num_symbols = 2000000  # 2M symbols × 6 chunks = ~6s total (more realistic for video)
        symbol_rate = 2e6
        sample_rate = 20e6
        quality_metrics = False
        beam_adaptive = False

        opt_iter = iter(opts)
        for token in opt_iter:
            try:
                if token == "--file":
                    video_path = Path(next(opt_iter))
                elif token == "--modulation":
                    modulation = next(opt_iter)
                elif token == "--chunks":
                    chunk_limit = int(float(next(opt_iter)))
                elif token == "--num-symbols":
                    num_symbols = int(float(next(opt_iter)))
                elif token == "--symbol-rate":
                    symbol_rate = float(next(opt_iter))
                elif token == "--sample-rate":
                    sample_rate = float(next(opt_iter))
                elif token == "--quality-metrics":
                    quality_metrics = True
                elif token == "--beam-adaptive":
                    beam_adaptive = True
                else:
                    print(f"Unknown option: {token}")
                    return
            except StopIteration:
                print(f"Missing value after {token}")
                return
            except ValueError:
                print(f"Invalid value for {token}")
                return

        if not self.net.get(ap):
            print(f"Unknown AP '{ap}'")
            return
        if not self.net.get(ris):
            print(f"Unknown RIS '{ris}'")
            return
        if not self.net.get(ue):
            print(f"Unknown UE '{ue}'")
            return

        # Use file_path_arg if no --file option was provided
        if video_path is None and file_path_arg is not None:
            video_path = Path(file_path_arg)

        if video_path is None:
            print("Error: --file PATH is required for streaming")
            return

        video_path = video_path.expanduser()
        if not video_path.is_absolute():
            video_path = Path(os.getcwd()) / video_path

        config = VideoStreamConfig(
            video_path=video_path,
            modulation=modulation,
            num_symbols=num_symbols,
            symbol_rate=symbol_rate,
            sample_rate=sample_rate,
            chunk_limit=chunk_limit,
            quality_metrics=quality_metrics,
            beam_adaptive=beam_adaptive,
        )

        try:
            run_video_stream_workflow(self.net, ap, ris, ue, config)
        except FileNotFoundError as e:
            print(f"error: {e}")
        except Exception as e:
            print(f"Streaming failed: {e}")

    def do_signal(self, arg):
        """signal [<ap> <ris> <ue>] [--beam ANGLE] [--bandwidth MHz] [--breakdown] [--sweep-beam FOV STEP]
        Measure AP→RIS→UE transmit and receive power to expose apparent loss.

        Usage:
          signal                                                       - measure all active links (default)
          signal <ap> <ris> <ue>                                     - measure specific link
          signal <ap> <ris> <ue> [--beam ANGLE] [--bandwidth MHz]   - with specific parameters
          signal <ap> <ris> <ue> --breakdown                         - show AP→RIS and RIS→UE loss separately
          signal <ap> <ris> <ue> --sweep-beam 60 10                 - sweep beam angles ±60° at 10° steps

        Options:
          --beam ANGLE           Fixed beam angle in degrees
          --bandwidth MHz        Signal bandwidth (default: 100 MHz)
          --breakdown            Show per-hop loss breakdown (AP→RIS, RIS→UE)
          --sweep-beam FOV STEP  Sweep beam angles within ±FOV at STEP intervals"""
        parts = shlex.split(arg) if arg else []

        # Default to active links mode (--active behavior) if no node arguments provided
        # Only use specific link mode if first 3 arguments are valid node names
        use_active_links = True
        if len(parts) >= 1 and parts[0] not in ('--bandwidth', '-w', '--beam', '-b'):
            # Check if first arg could be a node name (not an option)
            if not parts[0].startswith('-'):
                # Could be a node name; check if we have 3 node names before options
                node_count = 0
                for p in parts:
                    if p.startswith('-'):
                        break
                    node_count += 1
                if node_count >= 3:
                    use_active_links = False

        if use_active_links:
            # Mode: run signal on all active links
            parts = [p for p in parts if p not in ('--active', '-a')]

            # Parse optional parameters
            opt_iter = iter(parts)
            bandwidth_MHz = None
            breakdown = False
            sweep_beam_fov = None
            sweep_beam_step = None
            for token in opt_iter:
                try:
                    if token in ('--bandwidth', '-w'):
                        bandwidth_MHz = float(next(opt_iter))
                    elif token == '--breakdown':
                        breakdown = True
                    elif token == '--sweep-beam':
                        sweep_beam_fov = float(next(opt_iter))
                        sweep_beam_step = float(next(opt_iter))
                    else:
                        print(f"Unknown option: {token}")
                        return
                except StopIteration:
                    print(f"Missing value after {token}")
                    return
                except ValueError:
                    print(f"Invalid numeric value for {token}")
                    return

            active_links = self.net.get_active_links()
            if not active_links:
                print("No active links. Use 'connect' command to create active links first.")
                return

            print(f"Measuring signal on {len(active_links)} active link(s):\n")
            for link_idx, (link_key, link_data) in enumerate(active_links.items(), 1):
                ap_name = link_data['ap']
                ris_name = link_data['ris']
                ue_name = link_data['ue']

                ap_node = self.net.get(ap_name)
                ue_node = self.net.get(ue_name)

                if not ap_node or not ue_node:
                    print(f"[{link_idx}] Link '{link_key}' - Error: node not found")
                    continue

                # Use the beam angle from the active link
                beam_angle = link_data.get('beam_angle_absolute')

                try:
                    result = self.net.connect(
                        ap_name, ris_name, ue_name,
                        beam_angle_deg=beam_angle,
                        bandwidth_MHz=bandwidth_MHz,
                        compute_phases=False,
                        use_isolated_copy=True,
                        store_in_active_links=False
                    )
                except Exception as exc:
                    print(f"[{link_idx}] Link '{link_key}' - Measurement failed: {exc}")
                    continue

                tx_power = float(ap_node.power_dBm)
                rx_power = float(result.get('rssi_dBm', result.get('pwr_dBm', 'nan')))
                loss_dB = tx_power - rx_power

                print(f"[{link_idx}] {link_key}")
                print(f"    AP {ap_name}: Tx power = {tx_power:.2f} dBm")
                print(f"    UE {ue_name}: Rx power = {rx_power:.2f} dBm")
                print(f"    Apparent loss (Tx - Rx) = {loss_dB:.2f} dB")

                # Add measurement assumptions for SNR/gain traceability
                bw_mhz = bandwidth_MHz if bandwidth_MHz else 100.0
                ue_nf = ue_node.noise_figure_dB if hasattr(ue_node, 'noise_figure_dB') else 6.0

                # Calculate theoretical noise floor from stated assumptions
                noise_floor_dbm = -174 + 10 * np.log10(bw_mhz * 1e6) + ue_nf
                theoretical_snr = rx_power - noise_floor_dbm

                print(f"    Assumptions: B = {bw_mhz:.1f} MHz, NF = {ue_nf:.1f} dB (noise floor ≈ {noise_floor_dbm:.2f} dBm)")

                if 'snr_dB' in result:
                    snr_measured = result['snr_dB']
                    # Check if fading reduced SNR significantly
                    if abs(snr_measured - theoretical_snr) > 0.5:
                        print(f"    SNR (theoretical) = {theoretical_snr:.2f} dB")
                        print(f"    SNR (measured with fading) = {snr_measured:.2f} dB")
                    else:
                        print(f"    SNR estimate = {snr_measured:.2f} dB")
                if 'gain_dBi' in result:
                    print(f"    RIS gain = {result['gain_dBi']:.2f} dBi (aperture-based; > measured realized gain ~22.6 dBi)")

                # Per-hop loss breakdown if requested
                if breakdown:
                    print(f"    [PER-HOP BREAKDOWN]")
                    ap_ris_loss = result.get('total_loss_dB', 0)  # Includes path loss AP→RIS
                    ris_ue_loss = 0  # Will be calculated

                    # Get RIS node for detailed path loss
                    ris_node = self.net.get(ris_name)
                    if ris_node and hasattr(ris_node, 'pos'):
                        dist_ap_ris = float(np.linalg.norm(ap_node.pos - ris_node.pos))
                        dist_ris_ue = float(np.linalg.norm(ris_node.pos - ue_node.pos))
                        freq = ap_node.freq if hasattr(ap_node, 'freq') and ap_node.freq else 5.8e9

                        # Path loss formula: PL = 20*log10(4*pi*d*f/c)
                        c = 3e8
                        pl_ap_ris = 20 * np.log10(4 * np.pi * dist_ap_ris * freq / c)
                        pl_ris_ue = 20 * np.log10(4 * np.pi * dist_ris_ue * freq / c)

                        print(f"      AP→RIS distance: {dist_ap_ris:.2f} m, path loss: {pl_ap_ris:.2f} dB")
                        print(f"      RIS→UE distance: {dist_ris_ue:.2f} m, path loss: {pl_ris_ue:.2f} dB")
                        print(f"      Total path loss: {pl_ap_ris + pl_ris_ue:.2f} dB")

                        # Show quantization loss if available
                        if 'quant_loss_dB' in result:
                            quant_loss = abs(result['quant_loss_dB'])
                            print(f"      Phase quantization loss: {quant_loss:.2f} dB")

                # Beam sweep if requested
                if sweep_beam_fov is not None and sweep_beam_step is not None:
                    print(f"    [BEAM SWEEP: ±{sweep_beam_fov:.1f}° at {sweep_beam_step:.1f}° steps]")
                    sweep_results = []

                    # Generate beam angles to sweep
                    angles = np.arange(-sweep_beam_fov, sweep_beam_fov + sweep_beam_step, sweep_beam_step)

                    for angle in angles:
                        try:
                            sweep_result = self.net.connect(
                                ap_name, ris_name, ue_name,
                                beam_angle_deg=angle,
                                bandwidth_MHz=bandwidth_MHz,
                                compute_phases=False,
                                use_isolated_copy=True,
                                store_in_active_links=False
                            )
                            snr = sweep_result.get('snr_dB', 0)
                            sweep_results.append({'angle': angle, 'snr': snr})
                        except Exception as e:
                            sweep_results.append({'angle': angle, 'snr': None})

                    # Find peak SNR
                    valid_results = [r for r in sweep_results if r['snr'] is not None]
                    if valid_results:
                        peak = max(valid_results, key=lambda x: x['snr'])
                        print(f"      Peak SNR: {peak['snr']:.2f} dB at {peak['angle']:.1f}°")
                        print(f"      Sweep results:")
                        for r in sweep_results:
                            if r['snr'] is not None:
                                marker = " ← PEAK" if r == peak else ""
                                print(f"        {r['angle']:7.1f}°: {r['snr']:7.2f} dB{marker}")
                            else:
                                print(f"        {r['angle']:7.1f}°: FAILED")

                print()
        else:
            # Mode: measure specific link
            if len(parts) < 3:
                print("usage: signal <ap> <ris> <ue> [--beam ANGLE] [--bandwidth MHz]")
                return

            ap_name, ris_name, ue_name = parts[:3]
            opts = parts[3:]

            def _ignore_case_lookup(name):
                node = self.net.get(name)
                if node:
                    return name
                lower = name.lower()
                for candidate in self.net.nodes:
                    if candidate.lower() == lower:
                        return candidate
                return name

            ap_name = _ignore_case_lookup(ap_name)
            ris_name = _ignore_case_lookup(ris_name)
            ue_name = _ignore_case_lookup(ue_name)

            opt_iter = iter(opts)
            beam_angle = None
            bandwidth_MHz = None
            breakdown = False
            sweep_beam_fov = None
            sweep_beam_step = None
            for token in opt_iter:
                try:
                    if token in ('--beam', '--beam-angle', '-b'):
                        beam_angle = float(next(opt_iter))
                    elif token in ('--bandwidth', '-w'):
                        bandwidth_MHz = float(next(opt_iter))
                    elif token == '--breakdown':
                        breakdown = True
                    elif token == '--sweep-beam':
                        sweep_beam_fov = float(next(opt_iter))
                        sweep_beam_step = float(next(opt_iter))
                    else:
                        print(f"Unknown option: {token}")
                        return
                except StopIteration:
                    print(f"Missing value after {token}")
                    return
                except ValueError:
                    print(f"Invalid numeric value for {token}")
                    return

            ap_node = self.net.get(ap_name)
            ris_node = self.net.get(ris_name)
            ue_node = self.net.get(ue_name)

            if not ap_node or type(ap_node).__name__ != 'AccessPoint':
                print(f"Unknown Access Point '{ap_name}'")
                return
            if not ris_node or type(ris_node).__name__ != 'RIS':
                print(f"Unknown RIS node '{ris_name}'")
                return
            if not ue_node or type(ue_node).__name__ != 'UE':
                print(f"Unknown UE '{ue_name}'")
                return

            try:
                result = self.net.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=beam_angle,
                    bandwidth_MHz=bandwidth_MHz,
                    compute_phases=False,
                    use_isolated_copy=True,
                    store_in_active_links=False
                )
            except Exception as exc:
                print(f"Signal measurement failed: {exc}")
                return

            tx_power = float(ap_node.power_dBm)
            rx_power = float(result.get('rssi_dBm', result.get('pwr_dBm', 'nan')))
            loss_dB = tx_power - rx_power

            print("Signal measurement:")
            print(f"  AP {ap_name}: Tx power = {tx_power:.2f} dBm")
            print(f"  UE {ue_name}: Rx power = {rx_power:.2f} dBm")
            print(f"  Apparent loss (Tx - Rx) = {loss_dB:.2f} dB")
            if 'snr_dB' in result:
                print(f"  SNR estimate = {result['snr_dB']:.2f} dB")
            if 'gain_dBi' in result:
                print(f"  RIS gain = {result['gain_dBi']:.2f} dBi")

            # Per-hop loss breakdown if requested
            if breakdown:
                print(f"  [PER-HOP BREAKDOWN]")
                ris_node = self.net.get(ris_name)
                if ris_node and hasattr(ris_node, 'pos'):
                    dist_ap_ris = float(np.linalg.norm(ap_node.pos - ris_node.pos))
                    dist_ris_ue = float(np.linalg.norm(ris_node.pos - ue_node.pos))
                    freq = ap_node.freq if hasattr(ap_node, 'freq') and ap_node.freq else 5.8e9

                    # Path loss formula: PL = 20*log10(4*pi*d*f/c)
                    c = 3e8
                    pl_ap_ris = 20 * np.log10(4 * np.pi * dist_ap_ris * freq / c)
                    pl_ris_ue = 20 * np.log10(4 * np.pi * dist_ris_ue * freq / c)

                    print(f"    AP→RIS distance: {dist_ap_ris:.2f} m, path loss: {pl_ap_ris:.2f} dB")
                    print(f"    RIS→UE distance: {dist_ris_ue:.2f} m, path loss: {pl_ris_ue:.2f} dB")
                    print(f"    Total path loss: {pl_ap_ris + pl_ris_ue:.2f} dB")

                    if 'quant_loss_dB' in result:
                        quant_loss = abs(result['quant_loss_dB'])
                        print(f"    Phase quantization loss: {quant_loss:.2f} dB")

            # Beam sweep if requested
            if sweep_beam_fov is not None and sweep_beam_step is not None:
                print(f"  [BEAM SWEEP: ±{sweep_beam_fov:.1f}° at {sweep_beam_step:.1f}° steps]")
                sweep_results = []

                # Generate beam angles to sweep
                angles = np.arange(-sweep_beam_fov, sweep_beam_fov + sweep_beam_step, sweep_beam_step)

                for angle in angles:
                    try:
                        sweep_result = self.net.connect(
                            ap_name, ris_name, ue_name,
                            beam_angle_deg=angle,
                            bandwidth_MHz=bandwidth_MHz,
                            compute_phases=False,
                            use_isolated_copy=True,
                            store_in_active_links=False
                        )
                        snr = sweep_result.get('snr_dB', 0)
                        sweep_results.append({'angle': angle, 'snr': snr})
                    except Exception as e:
                        sweep_results.append({'angle': angle, 'snr': None})

                # Find peak SNR
                valid_results = [r for r in sweep_results if r['snr'] is not None]
                if valid_results:
                    peak = max(valid_results, key=lambda x: x['snr'])
                    print(f"    Peak SNR: {peak['snr']:.2f} dB at {peak['angle']:.1f}°")
                    print(f"    Sweep results:")
                    for r in sweep_results:
                        if r['snr'] is not None:
                            marker = " ← PEAK" if r == peak else ""
                            print(f"      {r['angle']:7.1f}°: {r['snr']:7.2f} dB{marker}")
                        else:
                            print(f"      {r['angle']:7.1f}°: FAILED")
    # =====================================================================
    # Network I/O Commands
    # =====================================================================

    def do_save(self, arg):
        """save [filename] - Save network state to disk
        Examples:
          save              - Save to default .risnet_network.json
          save my_topo.json - Save to my_topo.json
        """
        try:
            if arg.strip():
                self._save_network_to_file(arg.strip())
                print(f"✓ Network saved to {arg.strip()}")
            else:
                self._save_network()
                print("✓ Network saved to .risnet_network.json")
        except Exception as e:
            print(f"Error saving network: {e}")

    def do_load(self, arg):
        """load [filepath] - Load network state from disk
        Examples:
          load                    - Load from default .risnet_network.json
          load examples/my_topo.json
        """
        try:
            if arg.strip():
                self._load_network_from_file(arg.strip())
                print(f"✓ Network loaded from {arg.strip()}")
            else:
                self._load_network()
                print("✓ Network loaded from .risnet_network.json")
        except Exception as e:
            print(f"Error loading network: {e}")

    def do_plot(self, arg):
        """plot [state_file] [--type sweep|connect] [--out output.png]
        Plot the most recent saved sweep/connect results. Provide a file to auto-load before plotting."""
        parts = shlex.split(arg) if arg else []
        result_type = 'sweep'
        output_path = None
        state_file = None

        i = 0
        while i < len(parts):
            token = parts[i]
            if token == '--type' and i + 1 < len(parts):
                result_type = parts[i + 1].lower()
                i += 2
                continue
            if token == '--out' and i + 1 < len(parts):
                output_path = parts[i + 1]
                i += 2
                continue
            if token.startswith('--'):
                print(f"Unknown option: {token}")
                return
            if state_file is None:
                state_file = token
            else:
                print(f"Unexpected extra argument: {token}")
                return
            i += 1

        if result_type not in ('sweep', 'connect'):
            print("Error: --type must be 'sweep' or 'connect'")
            return

        if state_file:
            if not os.path.exists(state_file):
                print(f"Error: File '{state_file}' not found")
                return
            try:
                self._load_network_from_file(state_file)
                print(f"✓ Network + results loaded from {state_file}")
            except Exception as exc:
                print(f"Error loading '{state_file}': {exc}")
                return

        stored = None
        if result_type == 'sweep':
            stored = getattr(self.net, 'last_sweep_result', None)
        else:
            stored = getattr(self.net, 'last_connect_result', None)

        if not stored:
            print(f"✗ No stored {result_type} results found. Run and save a {result_type} first.")
            return

        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            print("✗ matplotlib not installed. Install with: pip install matplotlib")
            return

        def _slug(text):
            if not text:
                return 'net'
            return ''.join(ch if ch.isalnum() or ch in ('-', '_') else '_' for ch in str(text))

        def _to_float_list(values):
            processed = []
            for val in values or []:
                if val is None:
                    processed.append(np.nan)
                    continue
                try:
                    processed.append(float(val))
                except (TypeError, ValueError):
                    processed.append(np.nan)
            return processed

        def _fmt_meta(value, precision=2):
            if value is None or value == '-':
                return '-'
            try:
                num = float(value)
                if np.isnan(num):
                    return '-'
                return f"{num:.{precision}f}"
            except (TypeError, ValueError):
                return str(value)

        def _derive_sweep_summary(payload):
            summary = {}
            local_coarse = _to_float_list(payload.get('local_coarse'))
            snr_coarse = _to_float_list(payload.get('snr_coarse'))
            local_fine = _to_float_list(payload.get('local_fine'))
            snr_fine = _to_float_list(payload.get('snr_fine'))
            specular_angle = payload.get('specular_angle')
            if specular_angle is None:
                specular_angle = payload.get('base_angle')

            def _best_pair(angles, snrs):
                if not angles or not snrs:
                    return None, None
                arr_angles = np.array(angles, dtype=float)
                arr_snrs = np.array(snrs, dtype=float)
                if arr_snrs.size == 0 or not np.isfinite(arr_snrs).any():
                    return None, None
                best_idx = int(np.nanargmax(arr_snrs))
                return arr_angles[best_idx], arr_snrs[best_idx]

            best_local = None
            best_snr = None
            if local_fine and snr_fine:
                best_local, best_snr = _best_pair(local_fine, snr_fine)
            if best_local is None and local_coarse and snr_coarse:
                best_local, best_snr = _best_pair(local_coarse, snr_coarse)

            if best_local is not None and specular_angle is not None:
                best_abs = float(specular_angle) + best_local
            elif best_local is not None:
                best_abs = best_local
            else:
                best_abs = None

            summary['best_local_deg'] = best_local
            summary['best_abs_deg'] = best_abs
            summary['specular_deg'] = specular_angle
            summary['expected_snr_dB'] = best_snr
            return summary

        def _derive_connect_summary(metrics):
            if not metrics:
                return {}
            return {
                'beam_angle_deg': metrics.get('beam_angle'),
                'snr_dB': metrics.get('snr_dB'),
                'pwr_dBm': metrics.get('pwr_dBm'),
                'gain_dBi': metrics.get('gain_dBi')
            }

        ap_label = stored.get('ap', 'AP')
        ris_label = stored.get('ris', 'RIS')
        ue_label = stored.get('ue', 'UE')

        default_filename = f"{_slug(ap_label)}_{_slug(ris_label)}_{_slug(ue_label)}_{result_type}_plot.png"
        output_path = output_path or default_filename

        metadata_lines = [
            f"Link: {ap_label}→{ris_label}→{ue_label}",
            f"Captured: {stored.get('captured_at', 'unknown')}"
        ]

        if result_type == 'sweep':
            params = stored.get('parameters') or {}
            summary = stored.get('summary') or {}
            if not summary:
                summary = _derive_sweep_summary(stored.get('outputs') or {})
            algo_label = stored.get('algorithm_alias') or stored.get('algorithm')
            metadata_lines.append(f"Algorithm: {algo_label or 'unknown'}")
            metadata_lines.append(
                f"FOV: {_fmt_meta(params.get('fov'))}°  "
                f"Step: {_fmt_meta(params.get('step'))}°"
            )
            if summary:
                metadata_lines.append(
                    f"Best Local: {_fmt_meta(summary.get('best_local_deg'))}°  "
                    f"Abs: {_fmt_meta(summary.get('best_abs_deg'))}°"
                )
                metadata_lines.append(
                    f"Specular: {_fmt_meta(summary.get('specular_deg'))}°  "
                    f"Expected SNR: {_fmt_meta(summary.get('expected_snr_dB'))} dB"
                )

            payload = stored.get('outputs') or {}
            local_coarse = _to_float_list(payload.get('local_coarse'))
            snr_coarse = _to_float_list(payload.get('snr_coarse'))
            pwr_coarse = _to_float_list(payload.get('pwr_coarse'))
            local_fine = _to_float_list(payload.get('local_fine'))
            snr_fine = _to_float_list(payload.get('snr_fine'))

            if not local_coarse or not snr_coarse:
                print("✗ Stored sweep does not contain coarse data to plot.")
                return

            has_fine = bool(local_fine and snr_fine)
            cols = 2 if has_fine else 1
            fig, axes = plt.subplots(1, cols, figsize=(12, 4.5 if has_fine else 4.0))
            if not isinstance(axes, (list, tuple, np.ndarray)):
                axes = [axes]

            coarse_ax = axes[0]
            coarse_ax.plot(local_coarse, snr_coarse, marker='o', color='tab:blue', label='SNR (dB)')
            coarse_ax.set_title('Coarse Phase')
            coarse_ax.set_xlabel('Local Angle (deg)')
            coarse_ax.set_ylabel('SNR (dB)')
            coarse_ax.grid(alpha=0.3)

            coarse_snr_arr = np.array(snr_coarse, dtype=float)
            coarse_angle_arr = np.array(local_coarse, dtype=float)
            if coarse_snr_arr.size and np.isfinite(coarse_snr_arr).any():
                best_idx = int(np.nanargmax(coarse_snr_arr))
                coarse_ax.scatter(
                    [coarse_angle_arr[best_idx]],
                    [coarse_snr_arr[best_idx]],
                    color='tab:green',
                    label='Best SNR',
                    zorder=5
                )

            pwr_arr = np.array(pwr_coarse, dtype=float) if pwr_coarse else np.array([])
            if pwr_arr.size and np.isfinite(pwr_arr).any():
                pwr_ax = coarse_ax.twinx()
                pwr_ax.plot(local_coarse, pwr_coarse, color='tab:orange', linestyle='--', marker='s', label='Power (dBm)')
                pwr_ax.set_ylabel('Power (dBm)', color='tab:orange')
                for tick in pwr_ax.get_yticklabels():
                    tick.set_color('tab:orange')
                lines_1, labels_1 = coarse_ax.get_legend_handles_labels()
                lines_2, labels_2 = pwr_ax.get_legend_handles_labels()
                coarse_ax.legend(lines_1 + lines_2, labels_1 + labels_2, loc='best')
            else:
                coarse_ax.legend(loc='best')

            if has_fine:
                fine_ax = axes[1]
                fine_ax.plot(local_fine, snr_fine, marker='o', color='tab:red', label='SNR (dB)')
                fine_ax.set_title('Fine Phase')
                fine_ax.set_xlabel('Local Angle (deg)')
                fine_ax.set_ylabel('SNR (dB)')
                fine_ax.grid(alpha=0.3)

                fine_snr_arr = np.array(snr_fine, dtype=float)
                fine_angle_arr = np.array(local_fine, dtype=float)
                if fine_snr_arr.size and np.isfinite(fine_snr_arr).any():
                    fine_idx = int(np.nanargmax(fine_snr_arr))
                    fine_ax.scatter(
                        [fine_angle_arr[fine_idx]],
                        [fine_snr_arr[fine_idx]],
                        color='tab:green',
                        label='Best SNR',
                        zorder=5
                    )
                    fine_ax.legend(loc='best')

            fig.suptitle(f"Sweep Results: {ap_label}→{ris_label}→{ue_label}")
        else:
            params = stored.get('parameters') or {}
            summary = stored.get('summary') or {}
            if not summary:
                summary = _derive_connect_summary(stored.get('metrics'))
            metadata_lines.append(f"Waveform: {'Yes' if params.get('use_waveform') else 'No'}"
                                  f"  Modulation: {params.get('modulation') or 'N/A'}")
            if summary:
                metadata_lines.append(
                    f"Beam Angle: {_fmt_meta(summary.get('beam_angle_deg'))}°  "
                    f"SNR: {_fmt_meta(summary.get('snr_dB'))} dB"
                )
                metadata_lines.append(
                    f"PWR: {_fmt_meta(summary.get('pwr_dBm'))} dBm  "
                    f"Gain: {_fmt_meta(summary.get('gain_dBi'))} dBi"
                )

            metrics = stored.get('metrics') or {}
            numeric_pairs = [
                ("SNR (dB)", 'snr_dB'),
                ("RSSI (dBm)", 'rssi_dBm'),
                ("Power (dBm)", 'pwr_dBm'),
                ("Gain (dBi)", 'gain_dBi')
            ]
            labels = []
            values = []
            for label, key in numeric_pairs:
                if key not in metrics or metrics[key] is None:
                    continue
                try:
                    values.append(float(metrics[key]))
                    labels.append(label)
                except (TypeError, ValueError):
                    continue

            if not labels:
                print("✗ No numeric connect metrics are available to plot.")
                return

            fig, ax = plt.subplots(figsize=(6, 4))
            bars = ax.barh(labels, values, color='tab:blue', alpha=0.85)
            ax.axvline(0, color='black', linewidth=0.5)
            ax.set_xlabel('Value')
            ax.set_title(f"Connect Metrics: {ap_label}→{ris_label}→{ue_label}")
            for bar, val in zip(bars, values):
                width = bar.get_width()
                offset = 0.4 if width >= 0 else -0.4
                ha = 'left' if width >= 0 else 'right'
                ax.text(
                    width + offset,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val:.2f}",
                    va='center',
                    ha=ha
                )

        fig.tight_layout()
        if metadata_lines:
            meta_text = "\n".join(str(line) for line in metadata_lines)
            # Ensure padding for metadata block
            fig.subplots_adjust(bottom=max(0.2, fig.subplotpars.bottom))
            fig.text(
                0.02,
                0.02,
                meta_text,
                fontsize=8,
                family='monospace',
                ha='left',
                va='bottom',
                color='#333333'
            )
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"✓ Plot saved to {output_path}")

    # =====================================================================
    # Node Shells
    # =====================================================================

    def default(self, line):
        """Handle node commands (e.g., R1, AP1, UE1, etc.)"""
        parts = shlex.split(line)
        if not parts:
            return

        node_name = parts[0]
        node = self.net.get(node_name)
        if node is None:
            print(f"Unknown command: {line}")
            return

        node_type = type(node).__name__

        if len(parts) == 1:
            # Just node name - enter interactive shell
            if node_type == 'RIS':
                shell = RISNodeShell(node, self.net)  # Pass network for active_links access
                # Pass last connect result if available
                if hasattr(self.net, 'last_connect_result') and self.net.last_connect_result:
                    shell.last_connect_result = self.net.last_connect_result
                shell.cmdloop()
            elif node_type == 'AccessPoint':
                shell = APNodeShell(node)
                shell.cmdloop()
            elif node_type == 'UE':
                shell = UENodeShell(node)
                shell.cmdloop()
        else:
            # Node name + command
            cmd_name = parts[1]
            cmd_args = parts[2:]
            if node_type == 'RIS':
                shell = RISNodeShell(node, self.net)  # Pass network for active_links access
                # Pass last connect result if available
                if hasattr(self.net, 'last_connect_result') and self.net.last_connect_result:
                    shell.last_connect_result = self.net.last_connect_result
                shell.onecmd(' '.join(parts[1:]))
            elif node_type == 'AccessPoint':
                shell = APNodeShell(node)
                shell.onecmd(' '.join(parts[1:]))
            elif node_type == 'UE':
                shell = UENodeShell(node)
                shell.onecmd(' '.join(parts[1:]))

    # =====================================================================
    # Test & Debug Commands
    # =====================================================================

    def do_testall(self, arg):
        """testall - Run comprehensive test suite"""
        print("\n" + "="*70)
        print("RISNet v2.0 - Comprehensive Test Suite")
        print("="*70)

        suite_results = run_testall(self.net)
        print(suite_results.format_text())

    def do_quit(self, arg):
        """quit - Exit the CLI"""
        if self.net.nodes:
            print("Clearing topology and active links...")
            self.net.clear_links()
            self.net.nodes.clear()
            if hasattr(self.net, 'last_connect_result'):
                self.net.last_connect_result = None
            if hasattr(self.net, 'last_sweep_result'):
                self.net.last_sweep_result = None
            # Do NOT save network on exit - ensures clean state on restart
            # Only save results would be blank anyway after clearing
            print("✓ Topology and links cleared (not saved)")
        print('Exiting RISNet CLI')
        return True

    def do_exit(self, arg):
        """exit - Exit the CLI (alias for quit)"""
        return self.do_quit(arg)

    # =====================================================================
    # Network I/O Helpers
    # =====================================================================

    def _save_network(self):
        """Save to default location"""
        self._save_network_to_file('.risnet_network.json')

    def _save_network_to_file(self, filepath):
        """Save network to JSON file"""
        self.network_io.save(self.net, filepath)

    def _load_network(self):
        """Load from default location"""
        self._load_network_from_file('.risnet_network.json')

    def _load_network_from_file(self, filepath):
        """Load network from JSON file"""
        self.network_io.load(self.net, filepath)
