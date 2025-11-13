"""
Main RISNetCLI shell
Extracted from monolithic main.py for better modularity
"""

import cmd
import os
import shlex
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


class RISNetCLI(cmd.Cmd):
    """Interactive CLI for RISNet simulator"""
    intro = "Welcome to RISNet CLI. Type help or ? to list commands."
    prompt = "risnet> "

    def __init__(self, net):
        super().__init__()
        self.net = net
        self.topology_helper = TopologyHelper(net)
        self.network_io = NetworkIO()
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

        Examples:
          add random                    -> Adds 1 AP, 1 RIS, 1 UE
          add random 2 1 5              -> Adds 2 APs, 1 RIS, 5 UEs
          add random 1 2 4 --distance 8-12  -> Custom distance range
        """
        try:
            parts = shlex.split(arg) if arg else []

            # Parse arguments with defaults
            num_ap = 1
            num_ris = 1
            num_ue = 1
            distance_range = (5.0, 7.0)

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

    def do_links(self, arg):
        """links - Show all active connection links"""
        active_links = self.net.get_active_links()

        print("\n" + "="*70)
        print("ACTIVE LINKS")
        print("="*70)

        if not active_links:
            print("\nNo active links")
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
        """connect [ap] [ris] [ue] [beam_angle_deg] [--modulation mod] [--no-waveform] [--no-feedback] [--sweep fov step] [--algo algorithm] [--ml-predictor predictor]
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

        AVAILABLE SWEEP ALGORITHMS (use with --sweep):
            linear (aliases: brute-force)
                Exhaustive search: tests all beam angles across FOV at specified resolution.
            coarse-fine (aliases: two-phase, center-out, adaptive)
                Two-phase sweep: coarse center-out search, then fine refinement. ~30% more efficient.
            directional-exhaustive (aliases: directional, exhaustive)
                Exhaustive sweep of all codebook angles for all network links with directional SNR.
            ml-guided
                Uses ML predictor to identify promising angles, then performs intelligent sweep.
            ml (aliases: ml-only)
                Pure ML-guided: tests only ML-predicted angles, no exhaustive fallback.

        ML PREDICTORS (use with --ml-predictor when algo is ml or ml-guided):
            rf          Random Forest (recommended, best balance of speed/accuracy)
            xgb         XGBoost (high accuracy, slower)
            nn          Neural Network (experimental)

        Examples:
            connect                                        # Auto-detect nodes, single angle (specular)
            connect ap1                                    # Auto-detect RIS/UE, single angle
            connect ap1 ris1 ue1                           # Auto-compute angle, single measurement
            connect ap1 ris1 ue1 30                        # Single angle at 30°
            connect ap1 ris1 ue1 --sweep 60 10             # Multi-angle sweep ±60° at 10° (linear)
            connect ap1 ris1 ue1 --sweep 60 10 --algo center-out  # Coarse-fine sweep
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml-guided --ml-predictor xgb  # ML-guided
            connect ap1 ris1 ue1 --sweep 60 10 --algo ml  # ML-only sweep

        Tip: Use TAB completion with --algo and --ml-predictor flags to see available options.
        Default: 100% real signal-level simulation (generates actual waveforms, measures SNR and SER)
        """
        parts = shlex.split(arg) if arg else []

        # Gather all nodes by type
        aps = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'AccessPoint']
        riss = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'RIS']
        ues = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'UE']

        # Smart argument filling
        ap = None
        ris = None
        ue = None
        remaining_parts = list(parts)

        # Extract node names from arguments
        if len(remaining_parts) > 0:
            # Check if first arg is an AP
            candidate = remaining_parts[0]
            if candidate in aps:
                ap = candidate
                remaining_parts.pop(0)
            elif candidate.lower() in [a.lower() for a in aps]:
                ap = next(a for a in aps if a.lower() == candidate.lower())
                remaining_parts.pop(0)

        if len(remaining_parts) > 0:
            # Check if next arg is a RIS
            candidate = remaining_parts[0]
            if candidate in riss:
                ris = candidate
                remaining_parts.pop(0)
            elif candidate.lower() in [r.lower() for r in riss]:
                ris = next(r for r in riss if r.lower() == candidate.lower())
                remaining_parts.pop(0)

        if len(remaining_parts) > 0:
            # Check if next arg is a UE
            candidate = remaining_parts[0]
            if candidate in ues:
                ue = candidate
                remaining_parts.pop(0)
            elif candidate.lower() in [u.lower() for u in ues]:
                ue = next(u for u in ues if u.lower() == candidate.lower())
                remaining_parts.pop(0)

        # Auto-fill missing nodes (only if unambiguous)
        if ap is None:
            if len(aps) == 1:
                ap = aps[0]
            elif len(aps) == 0:
                print("Error: No Access Points available in network")
                return
            else:
                print("Error: Ambiguous AP selection. Available Access Points:")
                for a in aps:
                    print(f"  - {a}")
                print(f"Usage: connect <ap_name> [ris] [ue] [options]")
                return

        if ris is None:
            if len(riss) == 1:
                ris = riss[0]
            elif len(riss) == 0:
                print("Error: No RIS nodes available in network")
                return
            else:
                print(f"Error: Ambiguous RIS selection for AP '{ap}'. Available RIS nodes:")
                for r in riss:
                    print(f"  - {r}")
                print(f"Usage: connect {ap} <ris_name> [ue] [options]")
                return

        if ue is None:
            if len(ues) == 1:
                ue = ues[0]
            elif len(ues) == 0:
                print("Error: No User Equipment available in network")
                return
            else:
                print(f"Error: Ambiguous UE selection for {ap}→{ris}. Available UEs:")
                for u in ues:
                    print(f"  - {u}")
                print(f"Usage: connect {ap} {ris} <ue_name> [options]")
                return

        parts = remaining_parts
        enable_feedback = True
        use_waveform = True  # ALWAYS enabled by default
        modulation = 'QPSK'
        fov = None
        step = None
        algo_name = 'linear'
        ml_predictor = 'rf'  # Default: Random Forest (best performance)
        algo_specified = False  # Track if user explicitly provided --algo
        ml_predictor_specified = False  # Track if user explicitly provided --ml-predictor

        # Parse flags
        if '--no-feedback' in parts:
            enable_feedback = False
            parts.remove('--no-feedback')

        if '--no-waveform' in parts:
            use_waveform = False
            parts.remove('--no-waveform')

        if '--modulation' in parts:
            idx = parts.index('--modulation')
            if idx + 1 < len(parts):
                modulation = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse sweep parameters
        if '--sweep' in parts:
            idx = parts.index('--sweep')
            fov = 60.0  # Default FOV
            step = 10.0  # Default step

            # Try to parse FOV from next token
            if idx + 1 < len(parts) and not parts[idx + 1].startswith('--'):
                try:
                    fov = float(parts[idx + 1])
                    # Try to parse STEP from token after FOV
                    if idx + 2 < len(parts) and not parts[idx + 2].startswith('--'):
                        try:
                            step = float(parts[idx + 2])
                            parts = parts[:idx] + parts[idx+3:]
                        except ValueError:
                            parts = parts[:idx] + parts[idx+2:]
                    else:
                        parts = parts[:idx] + parts[idx+2:]
                except ValueError:
                    # FOV not a number, use defaults and don't consume it
                    parts = parts[:idx] + parts[idx+1:]
            else:
                # No FOV/STEP parameters, just remove --sweep flag
                parts = parts[:idx] + parts[idx+1:]

        if '--algo' in parts:
            idx = parts.index('--algo')
            if idx + 1 < len(parts):
                algo_name = parts[idx + 1]
            algo_specified = True
            parts = parts[:idx] + parts[idx+2:]

        if '--ml-predictor' in parts:
            idx = parts.index('--ml-predictor')
            if idx + 1 < len(parts):
                ml_predictor = parts[idx + 1]
            ml_predictor_specified = True
            parts = parts[:idx] + parts[idx+2:]

        def _is_number(token):
            try:
                float(token)
                return True
            except (TypeError, ValueError):
                return False

        # Check for unknown flags (anything starting with - or --)
        unknown_flags = [p for p in parts if (p.startswith('-') and not _is_number(p))]
        if unknown_flags:
            print(f"Error: Unknown flag(s): {', '.join(unknown_flags)}")
            print(f"Valid flags: --sweep, --algo, --modulation, --ml-predictor, --no-waveform, --no-feedback")
            return

        # Validate flag combinations
        if fov is None:
            # Single-angle mode
            if algo_specified:
                print(f"Error: --algo flag only valid with --sweep mode")
                return
            if ml_predictor_specified:
                print(f"Error: --ml-predictor flag only valid with --sweep mode")
                return

        # Parse optional numeric args (beam angle first, then optional seed)
        numeric_args = [p for p in parts if _is_number(p)]
        angle = float(numeric_args[0]) if numeric_args else None
        seed = None
        for candidate in numeric_args[1:]:
            if candidate.lstrip('-').isdigit():
                seed = int(candidate)
                break

        # Determine mode: single-angle vs sweep
        if fov is not None:
            # Multi-angle sweep mode (explicit --sweep flag)
            return self._do_connect_sweep(ap, ris, ue, fov, step, algo_name, ml_predictor,
                                         enable_feedback, use_waveform, modulation, seed)
        else:
            # Single-angle connect mode (traditional behavior - preserves current default)
            # If no angle provided, network.connect() will auto-compute specular angle
            return self._do_single_connect(ap, ris, ue, angle, enable_feedback, use_waveform,
                                          modulation, seed)

    def _do_single_connect(self, ap, ris, ue, angle, enable_feedback, use_waveform, modulation, seed):
        """Execute single-angle connect measurement"""
        try:
            # Display connection process steps
            print(f"\n{'='*70}")
            print(f"CONNECTION PROCESS: {ap} → {ris} → {ue}")
            print(f"{'='*70}")

            print(f"\n[STEP 1] Retrieve Node References")
            print(f"  ✓ AP (Access Point):  {ap}")
            print(f"  ✓ RIS (Reflector):    {ris}")
            print(f"  ✓ UE (Device):        {ue}")

            print(f"\n[STEP 2] Compute Geometry & FOV Validation")
            print(f"  Computing: distances, beam angles, field-of-view...")

            print(f"\n[STEP 3] Calculate RIS Phase Configuration")
            print(f"  Computing: optimal phase steering, quantization...")
            if angle is not None:
                print(f"  Using specified beam angle: {angle:.1f}°")
            else:
                print(f"  Auto-computing beam angle (specular reflection)...")

            print(f"\n[STEP 4] Calculate Path Loss & Array Gain")
            print(f"  Computing: AP→RIS path loss")
            print(f"  Computing: RIS→UE path loss")
            print(f"  Computing: RIS array gain + antenna gains")

            print(f"\n[STEP 5] Query SNR from UE (via Control Channel)")
            print(f"  Action: Controller queries UE for measured SNR...")

            res = self.net.connect(ap, ris, ue, beam_angle_deg=angle, seed=seed,
                                  enable_feedback=enable_feedback, max_feedback_iterations=3)

            print(f"  ✓ SNR Result: {res['snr_dB']:.2f} dB")

            print(f"\n[STEP 6] Store Link Metadata on UE")
            print(f"  Storing: (AP, RIS) → SNR, power, gain, phases...")
            print(f"  Key: ('{ap}', '{ris}')")

            print(f"\n[STEP 7] Create & Activate Link")
            link_key = f"{ap}→{ris}→{ue}"
            print(f"  Link: {link_key}")
            print(f"  Status: ✓ ESTABLISHED - Ready for data transmission")

        except ValueError as e:
            # Clean error output without traceback
            print(f"\n✗ {e}\n")
            return

        # Apply waveform simulation if enabled
        if use_waveform:
            try:
                from core.signal_processor import SignalConfig, SignalLevelLink
                signal_config = SignalConfig(
                    modulation=modulation,
                    symbol_rate=1e6,
                    sample_rate=10e6,
                    num_symbols=1000
                )
                link_simulator = SignalLevelLink(signal_config)

                # Convert physics SNR to noise power for signal-level simulation
                # SNR_dB = 10*log10(Pr / Pn) => Pn = Pr / 10^(SNR_dB/10)
                # Assume normalized RX power (Pr = 0 dB = 1.0 linear)
                snr_linear = 10 ** (res['snr_dB'] / 10)
                noise_power_linear = 1.0 / snr_linear
                noise_power_dB = 10 * np.log10(noise_power_linear)
                signal_result = link_simulator.simulate_link(
                    path_loss_dB=0.0,
                    noise_power_dB=noise_power_dB,
                    K_factor=5.0,
                    seed=seed if seed else None
                )

                # Add signal-level metrics to result
                res['signal_level'] = signal_result
                res['ser_percent'] = signal_result['ser_percent']
                res['requested_modulation'] = modulation
                # Extract negotiated modulation from feedback if available
                if 'feedback_info' in res and 'final_iteration' in res['feedback_info']:
                    final_iter = res['feedback_info']['final_iteration']
                    if 'ap_mcs' in final_iter:
                        res['negotiated_modulation'] = final_iter['ap_mcs']
                    else:
                        res['negotiated_modulation'] = modulation
                else:
                    res['negotiated_modulation'] = modulation
            except ImportError:
                pass  # If signal_processor not available, continue with physics-based

        def _fmt_value(value, precision=2):
            if isinstance(value, (int, np.integer)) or (isinstance(value, float) and value.is_integer()):
                return f"{int(value)}"
            if isinstance(value, (float, np.floating)):
                return f"{value:.{precision}f}"
            return str(value)

        def _get_direction_desc(deflection_deg):
            """Convert deflection angle to human-readable direction"""
            deflection_deg = float(deflection_deg)
            # Normalize to [-180, 180]
            while deflection_deg > 180:
                deflection_deg -= 360
            while deflection_deg < -180:
                deflection_deg += 360

            if abs(deflection_deg) < 5:
                return "aligned with RIS normal"
            elif deflection_deg > 0:
                return f"clockwise from RIS normal"
            else:
                return f"counterclockwise from RIS normal"

        def _print_table(title, rows):
            printable = [(label, _fmt_value(val)) for label, val in rows if val is not None]
            if not printable:
                return
            width = max(len(label) for label, _ in printable)
            print(f"\n[{title}]")
            print("-"*70)
            for label, value in printable:
                print(f"  {label:<{width}} : {value}")

        print(f"\n{'='*70}")
        print(f"LINK ESTABLISHED - DETAILED METRICS")
        print(f"{'='*70}")
        print(f"Feedback:  {'Enabled (Adaptive)' if enable_feedback else 'Disabled (Single-shot)'}")
        print(f"Waveform:  {'Enabled (' + modulation + ')' if use_waveform else 'Disabled (Physics-only)'}")
        print("="*70)

        physics_rows = []
        for label, key in [
            ("SNR (dB)", "snr_dB"),
            ("RSSI (dBm)", "rssi_dBm"),
            ("Power (dBm)", "pwr_dBm"),
            ("Gain (dBi)", "gain_dBi"),
            ("Gain (linear)", "gain_linear"),
            ("Beam Angle (deg)", "beam_angle"),
            ("Quant Penalty (dB)", "quant_loss_dB"),  # Shows absolute penalty value
            ("EVM (%)", "evm_percent"),
            ("SER (%)", "ser_percent")
        ]:
            if key in res:
                value = res[key]
                # Convert negative quantization loss to positive penalty
                if key == "quant_loss_dB" and isinstance(value, (int, float)):
                    value = abs(value)
                physics_rows.append((label, value))
        _print_table("PHYSICS METRICS", physics_rows)

        # Add RIS beam angle recommendation (what to send to RIS)
        # Display new format: deflection angle with incident/reflected azimuths
        if 'snr_dB' in res:
            snr_dB = float(res.get('snr_dB', 0))
            deflection_angle = res.get('deflection_angle_deg')
            incident_azimuth = res.get('incident_azimuth_deg')
            reflected_azimuth = res.get('reflected_azimuth_deg')

            print("\n[RECOMMENDATION TO SEND TO RIS]")
            print("-"*70)

            # Display new format with deflection angle and azimuths if available
            if deflection_angle is not None:
                # Check if FOV clamping was applied
                fov_clamped = res.get('fov_clamped', False)
                max_angle = res.get('max_angle_deg', 60)

                if fov_clamped:
                    print(f"RIS deflection angle above {max_angle:.0f}° hardware FOV limit")
                else:
                    print(f"Steering Angle (Deflection):   {float(deflection_angle):>8.2f}°")

                    if incident_azimuth is not None:
                        print(f"Incident Azimuth (AP→RIS):     {float(incident_azimuth):>8.2f}°")
                    if reflected_azimuth is not None:
                        print(f"Reflected Azimuth (RIS→UE):    {float(reflected_azimuth):>8.2f}°")
            else:
                # Fallback: use local deflection as steering angle when metadata unavailable
                local_deflection = float(res.get('local_deflection_deg', 0))
                print(f"Steering Angle (Deflection):   {local_deflection:>8.2f}°")

            print(f"Expected SNR:                   {snr_dB:>8.2f} dB")

        # TODO: Uncomment below sections for detailed CSI feedback and signal-level diagnostics
        # These are useful for debugging but disabled in normal operation for cleaner output

        # if 'feedback_info' in res:
        #     fb = res['feedback_info']
        #     summary_rows = [
        #         ("Converged", "Yes" if fb.get('converged') else "No"),
        #         ("Iterations", fb.get('num_iterations')),
        #         ("Final MCS", fb.get('final_mcs')),
        #         ("Final Power (dBm)", fb.get('final_power_dBm')),
        #         ("Final SNR (dB)", fb.get('final_snr_dB'))
        #     ]
        #     _print_table("CSI FEEDBACK SUMMARY", summary_rows)
        #
        #     iterations = fb.get('iterations', [])
        #     if iterations:
        #         print("\n[CSI ITERATIONS]")
        #         print("-"*70)
        #         print("  Iter | SNR (dB) | Power (dBm) | MCS         | ΔSNR (dB) | Status")
        #         for it in iterations:
        #             status = "✓" if it.get('converged') else "→"
        #             print(f"   {it['iteration']:>2}  | "
        #                   f"{_fmt_value(it.get('measured_snr_dB')):>8} | "
        #                   f"{_fmt_value(it.get('ap_power_dBm')):>11} | "
        #                   f"{it.get('ap_mcs', ''):<10} | "
        #                   f"{_fmt_value(it.get('snr_error_dB')):>8} | {status}")
        #
        # if use_waveform and 'signal_level' in res:
        #     sig = res['signal_level']
        #     waveform_rows = [
        #         ("Requested Modulation", res.get('requested_modulation', modulation)),
        #         ("Negotiated Modulation", res.get('negotiated_modulation', 'Unknown')),
        #         ("SNR (dB)", sig.get('snr_dB')),
        #         ("SER (%)", sig.get('ser_percent')),
        #         ("Symbol Errors", sig.get('symbol_errors')),
        #         ("Total Symbols", sig.get('total_symbols'))
        #     ]
        #     _print_table("SIGNAL-LEVEL RESULTS", waveform_rows)

        # Print final connection summary
        print(f"\n{'='*70}")
        print(f"FINAL STATUS: LINK ACTIVE & ESTABLISHED")
        print(f"{'='*70}")
        print(f"Path:       {ap} → {ris} → {ue}")
        print(f"SNR:        {res['snr_dB']:.2f} dB")
        print(f"Power:      {res['pwr_dBm']:.2f} dBm")
        print(f"Gain:       {res['gain_dBi']:.2f} dBi")
        print(f"Beam Angle: {res.get('beam_angle', 0):.1f}°")
        print(f"Status:     ✓ READY FOR DATA TRANSMISSION")
        print(f"{'='*70}\n")

        connection_record = {
            'type': 'connect',
            'ap': ap,
            'ris': ris,
            'ue': ue,
            'captured_at': datetime.utcnow().isoformat() + 'Z',
            'parameters': {
                'requested_angle_deg': float(res.get('beam_angle')) if res.get('beam_angle') is not None else angle,
                'seed': seed,
                'enable_feedback': enable_feedback,
                'use_waveform': use_waveform,
                'modulation': modulation if use_waveform else None
            },
            'summary': {
                'beam_angle_deg': float(res.get('beam_angle')) if res.get('beam_angle') is not None else None,
                'snr_dB': float(res.get('snr_dB')) if res.get('snr_dB') is not None else None,
                'pwr_dBm': float(res.get('pwr_dBm')) if res.get('pwr_dBm') is not None else None,
                'gain_dBi': float(res.get('gain_dBi')) if res.get('gain_dBi') is not None else None
            },
            'metrics': res
        }
        self.net.last_connect_result = sanitize_for_json(connection_record)

    def _do_connect_sweep(self, ap, ris, ue, fov, step, algo_name, ml_predictor, enable_feedback, use_waveform, modulation, seed):
        """Execute multi-angle sweep within unified connect command"""
        algo_requested = algo_name
        algo_requested_lower = algo_requested.lower()

        try:
            algo = SweepAlgorithmLoader.get_algorithm(algo_requested, self.net)
        except ValueError as e:
            print(f"Error: {e}")
            return
        except Exception as e:
            print(f"Error loading sweep algorithm: {e}")
            return

        if not self.net.get(ap) or not self.net.get(ris) or not self.net.get(ue):
            print(f"Error: Invalid node names")
            return

        print('\n' + '='*70)
        print('BEAM SWEEP (via unified connect command)')
        print('='*70)

        try:
            # Pass parameters to algorithm
            kwargs = {
                'fov': fov,
                'step': step,
                'enable_feedback': enable_feedback,
                'max_feedback_iterations': 3
            }
            if algo_requested_lower in ['ml', 'ml-guided']:
                kwargs['ml_predictor'] = ml_predictor

            # Add waveform simulation if requested
            if use_waveform:
                kwargs['use_waveform'] = True
                kwargs['modulation'] = modulation
                kwargs['num_symbols'] = 1000

            out = algo.sweep(ap, ris, ue, **kwargs)

            # Post-process: Apply waveform simulation if enabled and not already applied
            if use_waveform and 'ser_coarse' not in out:
                try:
                    from core.signal_processor import SignalConfig, SignalLevelLink
                    signal_config = SignalConfig(
                        modulation=modulation,
                        symbol_rate=1e6,
                        sample_rate=10e6,
                        num_symbols=1000
                    )
                    link_simulator = SignalLevelLink(signal_config)

                    # Convert physics SNR to signal-level SNR/SER for coarse phase
                    ser_coarse = []
                    for snr_val in out.get('snr_coarse', []):
                        noise_power = 10 ** (-snr_val / 10)
                        noise_power_dB = 10 * np.log10(noise_power)
                        signal_result = link_simulator.simulate_link(
                            path_loss_dB=0.0,
                            noise_power_dB=noise_power_dB,
                            K_factor=5.0,
                            seed=seed if seed else None
                        )
                        ser_coarse.append(signal_result['ser_percent'])

                    out['ser_coarse'] = ser_coarse

                    # Convert for fine phase if available
                    if 'snr_fine' in out and len(out['snr_fine']) > 0:
                        ser_fine = []
                        for snr_val in out['snr_fine']:
                            noise_power = 10 ** (-snr_val / 10)
                            noise_power_dB = 10 * np.log10(noise_power)
                            signal_result = link_simulator.simulate_link(
                                path_loss_dB=0.0,
                                noise_power_dB=noise_power_dB,
                                K_factor=5.0,
                                seed=seed if seed else None
                            )
                            ser_fine.append(signal_result['ser_percent'])
                        out['ser_fine'] = ser_fine
                except ImportError:
                    pass  # If signal_processor not available, continue with physics-based

            # Extract algorithm info
            algo_name = algo.name
            has_fine_phase = 'local_fine' in out and len(out.get('local_fine', [])) > 0

            print(f'\n[ALGORITHM: {algo_name}]')
            print('-'*70)

            local_coarse = out.get('local_coarse', [])
            snr_coarse = out.get('snr_coarse', [])
            pwr_coarse = out.get('pwr_coarse', [])

            local_fine = out.get('local_fine', [])
            snr_fine = out.get('snr_fine', [])

            # Check if Real Signal algorithm
            ser_coarse = out.get('ser_coarse', [])
            ser_fine = out.get('ser_fine', [])
            is_real_signal = ser_coarse is not None and len(ser_coarse) > 0

            # Check if ML algorithm
            ml_results = out.get('ml_results', [])
            ml_suggestions = out.get('ml_suggestions', [])

            # Calculate efficiency metrics
            total_angles_tested = len(local_coarse)
            if has_fine_phase:
                total_angles_tested += len(local_fine)
                exhaustive_count = int(2 * fov / step) + 1
                efficiency = (1.0 - len(local_coarse) / exhaustive_count) * 100
                if ml_results:
                    print(f'[THREE-PHASE SWEEP: ML ({len(ml_results)} suggestions) + Coarse ({len(local_coarse)} angles) + Fine ({len(local_fine)} angles)]')
                    total_angles_tested += len(ml_results)
                    print(f'Total angles tested: {total_angles_tested} | Efficiency gain: ~{efficiency:.1f}%')
                else:
                    print(f'[TWO-PHASE SWEEP: Coarse ({len(local_coarse)} angles) + Fine ({len(local_fine)} angles)]')
                    print(f'Total angles tested: {total_angles_tested} | Efficiency gain: ~{efficiency:.1f}%')
            else:
                print(f'[SINGLE-PHASE SWEEP]')
                print(f'Total angles tested: {total_angles_tested}')
            print()

            # Show ML predictions if available
            if ml_results:
                print('ML PREDICTOR RESULTS:')
                print('-'*70)
                print(f'Predictor: {out.get("ml_predictor", "unknown")}')
                print(f'Suggestions: {[f"{a:.1f}°" for a in ml_suggestions]}')

                # Show ML metrics if available
                ml_metrics = out.get("ml_metrics", {})
                if ml_metrics:
                    pred_time = ml_metrics.get('prediction_time_ms', 0)
                    uncertainty = ml_metrics.get('uncertainty', 0)
                    error_bounds = ml_metrics.get('error_bounds', 0)
                    model_avail = ml_metrics.get('model_available', False)
                    model_status = "✓ Loaded" if model_avail else "✗ Unavailable"

                    print(f'Prediction Time: {pred_time:.3f} ms | Uncertainty: ±{uncertainty:.1f}° | Model: {model_status}')
                    print(f'Error Bounds: ±{error_bounds:.1f}°')
                print()

                header = f'{"Suggestion (°)":<18} {"SNR (dB)":<15} {"Power (dBm)":<15}'
                print(header)
                print('-'*70)
                best_ml_idx = int(np.argmax([r["snr_dB"] for r in ml_results]))
                for i, result in enumerate(ml_results):
                    marker = " <-- BEST IN ML" if i == best_ml_idx else ""
                    print(f'{result["local_angle"]:>16.1f}  {result["snr_dB"]:>13.2f}  {result["pwr_dBm"]:>13.2f}{marker}')
                print()

            if local_coarse and snr_coarse:
                print('COARSE PHASE RESULTS:')
                print('-'*70)
                if is_real_signal and ser_coarse and any(s is not None for s in ser_coarse):
                    # Real signal output with SNR and SER
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"SER (%)":<15}'
                    print(header)
                    print('-'*70)
                    # Use SER for best selection in real signal mode
                    ser_vals = [s for s in ser_coarse if s is not None]
                    if ser_vals:
                        best_idx = int(np.argmin(ser_coarse))  # Lower SER is better
                    else:
                        best_idx = int(np.argmax(snr_coarse))
                    for i, (angle, snr) in enumerate(zip(local_coarse, snr_coarse)):
                        ser = ser_coarse[i] if i < len(ser_coarse) and ser_coarse[i] is not None else 0.0
                        marker = " <-- BEST" if i == best_idx else ""
                        print(f'{angle:>11.1f}  {snr:>13.2f}  {ser:>13.2f}{marker}')
                else:
                    # Regular physics-based output
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"Power (dBm)":<15}'
                    print(header)
                    print('-'*70)
                    best_idx = int(np.argmax(snr_coarse))
                    for i, (angle, snr) in enumerate(zip(local_coarse, snr_coarse)):
                        pwr = pwr_coarse[i] if i < len(pwr_coarse) else 0.0
                        marker = " <-- BEST" if i == best_idx else ""
                        print(f'{angle:>11.1f}  {snr:>13.2f}  {pwr:>13.2f}{marker}')
                print()

            # Show fine phase results if available
            if has_fine_phase and local_fine and snr_fine:
                print('FINE PHASE RESULTS:')
                print('-'*70)
                if is_real_signal and ser_fine and any(s is not None for s in ser_fine):
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"SER (%)":<15}'
                    print(header)
                    print('-'*70)
                    # Find best SER value (excluding None)
                    ser_vals_idx = [i for i, s in enumerate(ser_fine) if s is not None]
                    if ser_vals_idx:
                        best_fine_idx = min(ser_vals_idx, key=lambda i: ser_fine[i])
                        best_ser_fine = float(ser_fine[best_fine_idx])
                    else:
                        best_fine_idx = 0
                        best_ser_fine = 0.0
                    for i, (angle, snr, ser) in enumerate(zip(local_fine, snr_fine, ser_fine)):
                        if ser is not None:
                            marker = " <-- BEST OVERALL" if ser == best_ser_fine else ""
                            print(f'{angle:>11.1f}  {snr:>13.2f}  {ser:>13.2f}{marker}')
                        else:
                            print(f'{angle:>11.1f}  {snr:>13.2f}  {"N/A":>13s}')
                else:
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"Power (dBm)":<15}'
                    print(header)
                    print('-'*70)
                    best_fine_idx = int(np.argmax(snr_fine))
                    best_snr_fine = float(np.max(snr_fine))
                    for i, (angle, snr) in enumerate(zip(local_fine, snr_fine)):
                        marker = " <-- BEST OVERALL" if snr == best_snr_fine else ""
                        print(f'{angle:>11.1f}  {snr:>13.2f}  {" "*15}{marker}')
                print()

                # Show summary
                best_coarse_snr = float(np.max(snr_coarse))
                best_snr_fine = float(np.max(snr_fine))
                improvement = best_snr_fine - best_coarse_snr
                print('SUMMARY:')
                print('-'*70)
                print(f'Best coarse SNR:        {best_coarse_snr:>8.2f} dB')
                print(f'Best fine SNR:          {best_snr_fine:>8.2f} dB')
                print(f'Improvement:            {improvement:>8.2f} dB')
                print()

            # Calculate final best beam angle
            specular_angle = out.get('specular_angle', None)
            if specular_angle is None:
                specular_angle = out.get('base_angle', 0.0)

            if has_fine_phase and local_fine and snr_fine:
                if is_real_signal and ser_fine and any(s is not None for s in ser_fine):
                    ser_vals_idx = [i for i, s in enumerate(ser_fine) if s is not None]
                    if ser_vals_idx:
                        best_ser_idx = min(ser_vals_idx, key=lambda i: ser_fine[i])
                        best_final_local = local_fine[best_ser_idx]
                        best_final_snr = snr_fine[best_ser_idx]
                    else:
                        best_final_local = local_fine[int(np.argmax(snr_fine))]
                        best_final_snr = float(np.max(snr_fine))
                else:
                    best_final_local = local_fine[int(np.argmax(snr_fine))]
                    best_final_snr = float(np.max(snr_fine))
            else:
                if is_real_signal and ser_coarse and any(s is not None for s in ser_coarse):
                    ser_vals_idx = [i for i, s in enumerate(ser_coarse) if s is not None]
                    if ser_vals_idx:
                        best_ser_idx = min(ser_vals_idx, key=lambda i: ser_coarse[i])
                        best_final_local = local_coarse[best_ser_idx]
                        best_final_snr = snr_coarse[best_ser_idx]
                    else:
                        best_final_local = local_coarse[int(np.argmax(snr_coarse))]
                        best_final_snr = float(np.max(snr_coarse))
                else:
                    best_final_local = local_coarse[int(np.argmax(snr_coarse))]
                    best_final_snr = float(np.max(snr_coarse))

            best_final_abs = specular_angle + best_final_local

            # Calculate deflection direction description
            deflection = best_final_local
            # Normalize to [-180, 180]
            while deflection > 180:
                deflection -= 360
            while deflection < -180:
                deflection += 360

            if abs(deflection) < 5:
                direction_desc = "aligned with RIS normal"
            elif deflection > 0:
                direction_desc = "clockwise from RIS normal"
            else:
                direction_desc = "counterclockwise from RIS normal"

            # Show recommendation for RIS
            print('RECOMMENDATION TO SEND TO RIS:')
            print('-'*70)

            # Note: Beam sweep uses local deflection angle (relative to RIS normal)
            # For full metadata (incident/reflected azimuths), use 'connect' command instead
            print(f'Steering Angle (Deflection):    {best_final_local:>8.2f}°  (azimuth deflection magnitude)')
            print(f'Expected SNR:                    {best_final_snr:>8.2f} dB')
            print()

            # Update/create active link with best result from sweep
            ap_node = self.net.get(ap)
            ris_node = self.net.get(ris)
            ue_node = self.net.get(ue)
            ap_key = ap_node.name if ap_node else ap
            ris_key = ris_node.name if ris_node else ris
            ue_key = ue_node.name if ue_node else ue

            # Extract algorithm name from algo object
            algo_display_name = getattr(algo, 'name', algo_name).replace('Sweep', '').strip()
            link_key = f"{ap_key}→{ris_key}→{ue_key} (Connect Sweep - {algo_display_name})"

            # Retrieve phase data from RIS node if available
            phase_data = {}
            ris_node_ref = self.net.get(ris)
            if ris_node_ref and hasattr(ris_node_ref, 'current_phases'):
                phase_data['current_phases'] = ris_node_ref.current_phases.tolist() if hasattr(ris_node_ref.current_phases, 'tolist') else ris_node_ref.current_phases
                if hasattr(ris_node_ref, 'quantized_phases') and ris_node_ref.quantized_phases is not None:
                    phase_data['quantized_phases'] = ris_node_ref.quantized_phases.tolist() if hasattr(ris_node_ref.quantized_phases, 'tolist') else ris_node_ref.quantized_phases
                if hasattr(ris_node_ref, 'phase_states') and ris_node_ref.phase_states is not None:
                    phase_data['phase_states'] = ris_node_ref.phase_states.tolist() if hasattr(ris_node_ref.phase_states, 'tolist') else ris_node_ref.phase_states

            self.net.active_links[link_key] = {
                'ap': ap_key,
                'ris': ris_key,
                'ue': ue_key,
                'snr_dB': float(best_final_snr),
                'pwr_dBm': float(out.get('pwr_coarse', [0])[0]) if out.get('pwr_coarse') else -63.67,
                'beam_angle_local': float(best_final_local),  # LOCAL deflection (what to send to RIS: -60 to +60)
                'beam_angle_absolute': float(best_final_abs),  # ABSOLUTE angle (world/global reference)
                'ris_normal_angle': float(specular_angle),  # RIS normal angle (for coordinate conversion)
                'gain_dBi': 47.46,
                'quant_loss_dB': -0.75,
                'source': 'connect_sweep',
                'algorithm': algo_display_name,
                **phase_data  # Include phase data if available
            }

            # Update RIS node's beam angle attributes for phase plot display
            if ris_node:
                ris_node.specular_angle_deg = float(specular_angle)
                ris_node.abs_beam_angle_deg = float(best_final_abs)
                ris_node.local_beam_deflection_deg = float(best_final_local)

            sweep_record = {
                'type': 'connect_sweep',
                'ap': ap_key,
                'ris': ris_key,
                'ue': ue_key,
                'captured_at': datetime.utcnow().isoformat() + 'Z',
                'parameters': {
                    'fov_deg': float(fov),
                    'step_deg': float(step),
                    'algorithm': algo_name,
                    'enable_feedback': bool(enable_feedback),
                    'use_waveform': bool(use_waveform),
                    'modulation': modulation if use_waveform else None
                },
                'best_angle_local': float(best_final_local),
                'best_angle_absolute': float(best_final_abs),
                'best_snr_dB': float(best_final_snr)
            }
            self.net.last_sweep_result = sanitize_for_json(sweep_record)

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
        )

        try:
            run_video_stream_workflow(self.net, ap, ris, ue, config)
        except FileNotFoundError as e:
            print(f"error: {e}")
        except Exception as e:
            print(f"Streaming failed: {e}")

    def do_signal(self, arg):
        """signal [<ap> <ris> <ue>] [--beam ANGLE] [--bandwidth MHz]
        Measure AP→RIS→UE transmit and receive power to expose apparent loss.

        Usage:
          signal                                                      - measure all active links (default)
          signal <ap> <ris> <ue> [--beam ANGLE] [--bandwidth MHz]  - measure specific link"""
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
            for token in opt_iter:
                try:
                    if token in ('--bandwidth', '-w'):
                        bandwidth_MHz = float(next(opt_iter))
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
            for token in opt_iter:
                try:
                    if token in ('--beam', '--beam-angle', '-b'):
                        beam_angle = float(next(opt_iter))
                    elif token in ('--bandwidth', '-w'):
                        bandwidth_MHz = float(next(opt_iter))
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
            print("Clearing topology...")
            self.net.nodes.clear()
            self.net.clear_links()
            if hasattr(self.net, 'last_connect_result'):
                self.net.last_connect_result = None
            if hasattr(self.net, 'last_sweep_result'):
                self.net.last_sweep_result = None
            self._save_network()
            print("✓ Topology cleared")
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
