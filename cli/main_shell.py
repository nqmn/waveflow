"""
Main RISNetCLI shell
Extracted from monolithic main.py for better modularity
"""

import cmd
import shlex
import pprint
import numpy as np
from core import RIS, AccessPoint, UE
from controller.beamsweeping import SweepAlgorithmLoader, MLPredictorLoader
from cli import run_testall
from cli.ris_shell import RISNodeShell
from cli.ap_shell import APNodeShell
from cli.ue_shell import UENodeShell
from cli.helpers import TopologyHelper, NetworkIO


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
        """add <ap|ris|ue> [name]
        Auto-generates random positions and parameters.
        Examples:
          add ap          -> Creates AP1
          add ap MyAP     -> Creates MyAP
          add ris         -> Creates R1
          add ue          -> Creates UE1
        """
        try:
            parts = shlex.split(arg)
            if len(parts) < 1:
                print("usage: add <ap|ris|ue> [name]")
                return

            typ = parts[0].lower()
            name = parts[1] if len(parts) > 1 else None

            if not name:
                name = self.topology_helper.generate_auto_name(typ)

            x, y = self.topology_helper.generate_position(typ)
            z = 0.0

            if typ == 'ap':
                self.net.add_ap(name, x, y, z)
                print(f"✓ Added AP {name} at ({x:.2f}, {y:.2f})")
            elif typ == 'ris':
                N = 16
                bits = 1
                self.net.add_ris(name, x, y, z, N, bits)
                print(f"✓ Added RIS {name} at ({x:.2f}, {y:.2f}) (N={N}, bits={bits})")
            elif typ == 'ue':
                self.net.add_ue(name, x, y, z)
                print(f"✓ Added UE {name} at ({x:.2f}, {y:.2f})")
            else:
                print('usage: add <ap|ris|ue> [name]')
                return

            self._save_network()
        except Exception as e:
            print('error:', e)

    def do_list(self, arg):
        """list nodes - Show network topology"""
        self.topology_helper.print_topology()
        print()
        self.net.list_nodes()

    def do_clear(self, arg):
        """clear - Remove all nodes from network"""
        if not self.net.nodes:
            print("Network is already empty")
            return
        self.net.nodes.clear()
        self._save_network()
        print(f"✓ All nodes cleared")

    # =====================================================================
    # Connection & Control Commands
    # =====================================================================

    def do_connect(self, arg):
        """connect ap ris ue [beam_angle_deg] [seed] [--no-feedback]
        Example: connect ap1 ris1 ue1 30
        """
        parts = shlex.split(arg)
        if len(parts) < 3:
            print('usage: connect ap ris ue [beam_angle] [seed] [--no-feedback]')
            return

        ap, ris, ue = parts[0], parts[1], parts[2]
        enable_feedback = True

        if '--no-feedback' in parts:
            enable_feedback = False
            parts.remove('--no-feedback')

        angle = float(parts[3]) if len(parts) > 3 else None
        seed = None
        if len(parts) > 4:
            try:
                seed = int(parts[4])
            except ValueError:
                print('Seed must be an integer')
                return

        res = self.net.connect(ap, ris, ue, beam_angle_deg=angle, seed=seed,
                              enable_feedback=enable_feedback, max_feedback_iterations=3)

        print(f"\nConnection Result (Feedback: {'Enabled' if enable_feedback else 'Disabled'}):")
        print("="*70)
        pprint.pprint(res)

    def do_sweep(self, arg):
        """sweep ap ris ue [fov step] [--algo algorithm]
        Sweep beam angles to find optimal direction.
        Examples:
            sweep AP1 R1 UE1
            sweep AP1 R1 UE1 60 10 --algo adaptive
        """
        parts = shlex.split(arg)
        if len(parts) < 3:
            print('usage: sweep ap ris ue [fov step] [--algo algorithm]')
            return

        ap, ris, ue = parts[0], parts[1], parts[2]

        # Parse flags
        algo_name = 'linear'
        enable_feedback = True
        ml_enabled = False

        if '--algo' in parts:
            idx = parts.index('--algo')
            if idx + 1 < len(parts):
                algo_name = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--no-feedback' in parts:
            enable_feedback = False
            parts.remove('--no-feedback')

        fov = float(parts[3]) if len(parts) > 3 else 60.0
        step = float(parts[4]) if len(parts) > 4 else 10.0

        try:
            algo = SweepAlgorithmLoader.get_algorithm(algo_name, self.net)
        except ValueError as e:
            print(f"Error: {e}")
            return

        if not self.net.get(ap) or not self.net.get(ris) or not self.net.get(ue):
            print(f"Error: Invalid node names")
            return

        print('\n' + '='*70)
        print('BEAM SWEEP')
        print('='*70)

        try:
            out = algo.sweep(ap, ris, ue, fov=fov, step=step,
                            enable_feedback=enable_feedback,
                            max_feedback_iterations=3)

            print(f'\n[RESULTS]')
            print('-'*70)
            local_coarse = out.get('local_coarse', [])
            snr_coarse = out.get('snr_coarse', [])
            pwr_coarse = out.get('pwr_coarse', [])

            if local_coarse and snr_coarse:
                print(f'Total angles tested: {len(local_coarse)}\n')
                header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"Power (dBm)":<15}'
                print(header)
                print('-'*70)

                best_idx = int(np.argmax(snr_coarse))
                for i, (angle, snr) in enumerate(zip(local_coarse, snr_coarse)):
                    pwr = pwr_coarse[i] if i < len(pwr_coarse) else 0.0
                    marker = " <-- BEST" if i == best_idx else ""
                    print(f'{angle:>11.1f}  {snr:>13.2f}  {pwr:>13.2f}{marker}')

            print('='*70 + '\n')

        except ValueError as e:
            print(f"Sweep failed: {e}")

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
                shell = RISNodeShell(node)
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
                shell = RISNodeShell(node)
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
