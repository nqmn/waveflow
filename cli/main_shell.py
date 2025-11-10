"""
Main RISNetCLI shell
Extracted from monolithic main.py for better modularity
"""

import cmd
import os
import shlex
import pprint
from datetime import datetime
import numpy as np
from core import RIS, AccessPoint, UE
from controller.beamsweeping import SweepAlgorithmLoader, MLPredictorLoader
from cli import run_testall
from cli.ris_shell import RISNodeShell
from cli.ap_shell import APNodeShell
from cli.ue_shell import UENodeShell
from cli.helpers import TopologyHelper, NetworkIO, sanitize_for_json


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
                print(f"  {node_name:<15} : {node_type:<12} at {pos_str}")

        # Show active links
        active_links = self.net.get_active_links()
        if not active_links:
            print("\n✗ No active links")
        else:
            print(f"\nACTIVE LINKS ({len(active_links)}):")
            print("-" * 70)
            for link_name, link_info in active_links.items():
                print(f"\n  {link_name}")
                origin = link_info.get('source', 'unknown')
                origin_label = origin.capitalize() if isinstance(origin, str) else str(origin)
                print(f"    Source:        {origin_label}")
                print(f"    SNR:           {link_info['snr_dB']:>8.2f} dB")
                print(f"    Power:         {link_info['pwr_dBm']:>8.2f} dBm")
                print(f"    Gain:          {link_info['gain_dBi']:>8.2f} dBi")
                print(f"    Beam Angle:    {link_info['beam_angle']:>8.2f}°")
                print(f"    Quant Loss:    {link_info['quant_loss_dB']:>8.2f} dB")

        print("\n" + "="*70 + "\n")

    def do_clear(self, arg):
        """clear - Remove all nodes from network"""
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
        print(f"✓ All nodes cleared")

    # =====================================================================
    # Connection & Control Commands
    # =====================================================================

    def do_connect(self, arg):
        """connect [ap] [ris] [ue] [beam_angle_deg] [--modulation mod] [--no-waveform] [--no-feedback]
        Smart connect - automatically infers missing nodes. Establish 100% real signal-level connection.
        Examples:
            connect                                        # Auto-detect all nodes (if unambiguous)
            connect ap1                                    # Auto-detect RIS and UE for AP1
            connect ap1 ris1                               # Auto-detect UE for AP1→RIS1
            connect ap1 ris1 ue1                           # Explicit (traditional)
            connect ap1 ris1 ue1 30                        # Beam at 30°, real signal
            connect ap1 ris1 ue1 30 --modulation 16QAM     # Beam at 30°, 16QAM modulation
            connect ap1 ris1 ue1 30 --no-waveform          # Beam at 30°, physics-only
            connect ap1 ris1 ue1 30 --no-feedback          # No closed-loop adaptation
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

        def _is_number(token):
            try:
                float(token)
                return True
            except (TypeError, ValueError):
                return False

        # Parse optional numeric args (beam angle first, then optional seed)
        numeric_args = [p for p in parts if _is_number(p)]
        angle = float(numeric_args[0]) if numeric_args else None
        seed = None
        for candidate in numeric_args[1:]:
            if candidate.lstrip('-').isdigit():
                seed = int(candidate)
                break

        res = self.net.connect(ap, ris, ue, beam_angle_deg=angle, seed=seed,
                              enable_feedback=enable_feedback, max_feedback_iterations=3)

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

        def _print_table(title, rows):
            printable = [(label, _fmt_value(val)) for label, val in rows if val is not None]
            if not printable:
                return
            width = max(len(label) for label, _ in printable)
            print(f"\n[{title}]")
            print("-"*70)
            for label, value in printable:
                print(f"  {label:<{width}} : {value}")

        print(f"\nConnection Result (Feedback: {'Enabled' if enable_feedback else 'Disabled'}, "
              f"Waveform: {'Enabled (' + modulation + ')' if use_waveform else 'Disabled'})")
        print("="*70)

        physics_rows = []
        for label, key in [
            ("SNR (dB)", "snr_dB"),
            ("RSSI (dBm)", "rssi_dBm"),
            ("Power (dBm)", "pwr_dBm"),
            ("Gain (dBi)", "gain_dBi"),
            ("Gain (linear)", "gain_linear"),
            ("Beam Angle (deg)", "beam_angle"),
            ("Quant Loss (dB)", "quant_loss_dB"),
            ("EVM (%)", "evm_percent"),
            ("SER (%)", "ser_percent")
        ]:
            if key in res:
                physics_rows.append((label, res[key]))
        _print_table("PHYSICS METRICS", physics_rows)

        if 'feedback_info' in res:
            fb = res['feedback_info']
            summary_rows = [
                ("Converged", "Yes" if fb.get('converged') else "No"),
                ("Iterations", fb.get('num_iterations')),
                ("Final MCS", fb.get('final_mcs')),
                ("Final Power (dBm)", fb.get('final_power_dBm')),
                ("Final SNR (dB)", fb.get('final_snr_dB'))
            ]
            _print_table("CSI FEEDBACK SUMMARY", summary_rows)

            iterations = fb.get('iterations', [])
            if iterations:
                print("\n[CSI ITERATIONS]")
                print("-"*70)
                print("  Iter | SNR (dB) | Power (dBm) | MCS         | ΔSNR (dB) | Status")
                for it in iterations:
                    status = "✓" if it.get('converged') else "→"
                    print(f"   {it['iteration']:>2}  | "
                          f"{_fmt_value(it.get('measured_snr_dB')):>8} | "
                          f"{_fmt_value(it.get('ap_power_dBm')):>11} | "
                          f"{it.get('ap_mcs', ''):<10} | "
                          f"{_fmt_value(it.get('snr_error_dB')):>8} | {status}")

        if use_waveform and 'signal_level' in res:
            sig = res['signal_level']
            waveform_rows = [
                ("Requested Modulation", res.get('requested_modulation', modulation)),
                ("Negotiated Modulation", res.get('negotiated_modulation', 'Unknown')),
                ("SNR (dB)", sig.get('snr_dB')),
                ("SER (%)", sig.get('ser_percent')),
                ("Symbol Errors", sig.get('symbol_errors')),
                ("Total Symbols", sig.get('total_symbols'))
            ]
            _print_table("SIGNAL-LEVEL RESULTS", waveform_rows)

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

    def do_sweep(self, arg):
        """sweep ap ris ue [fov step] [--algo algorithm] [--ml-predictor type] [--modulation mod] [--no-waveform]
        Sweep beam angles using physics-based simulation. Optional: add real signal-level emulation with waveforms.
        Examples:
            sweep AP1 R1 UE1                                      # Default: physics-based sweep (linear)
            sweep AP1 R1 UE1 60 10 --modulation 16QAM             # Physics-based + signal-level SER (16QAM)
            sweep AP1 R1 UE1 60 10 --algo center-out              # Two-phase center-out sweep (~30% faster)
            sweep AP1 R1 UE1 60 10 --algo exhaustive              # Directional exhaustive multi-link sweep
            sweep AP1 R1 UE1 60 10 --algo ml --ml-predictor xgb   # ML-only sweep (1-phase)
            sweep AP1 R1 UE1 60 10 --no-waveform                  # Physics-based only (no signal simulation)
        Available algorithms:
          linear (default)         - Exhaustive brute-force search
          center-out               - Two-phase center-out sweep (~30% faster)
          exhaustive               - Directional exhaustive multi-link sweep
          ml, ml-guided            - ML-only sweep (1-phase, ML predictions only)
        Available modulations: QPSK (default), 16QAM, 64QAM (for signal-level simulation)
        Available ML predictors: xgb (default), zero, default
        Note: Signal-level emulation is integrated into each algorithm via use_waveform parameter
        """
        parts = shlex.split(arg)
        if len(parts) < 3:
            print('usage: sweep ap ris ue [fov step] [--algo algorithm] [--ml-predictor type]')
            return

        ap, ris, ue = parts[0], parts[1], parts[2]

        # Parse flags
        algo_name = 'linear'
        enable_feedback = True
        ml_predictor = 'xgb'
        modulation = 'QPSK'
        use_waveform = True  # ALWAYS enabled by default

        if '--algo' in parts:
            idx = parts.index('--algo')
            if idx + 1 < len(parts):
                algo_name = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--ml-predictor' in parts:
            idx = parts.index('--ml-predictor')
            if idx + 1 < len(parts):
                ml_predictor = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--modulation' in parts:
            idx = parts.index('--modulation')
            if idx + 1 < len(parts):
                modulation = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Optional: disable waveform with flag if needed
        if '--no-waveform' in parts:
            use_waveform = False
            parts.remove('--no-waveform')

        if '--no-feedback' in parts:
            enable_feedback = False
            parts.remove('--no-feedback')

        fov = float(parts[3]) if len(parts) > 3 else 60.0
        step = float(parts[4]) if len(parts) > 4 else 10.0
        seed = None  # Optional seed for reproducibility

        algo_requested = algo_name
        algo_requested_lower = algo_requested.lower()

        try:
            algo = SweepAlgorithmLoader.get_algorithm(algo_requested, self.net)
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
            # Pass parameters to algorithm based on type
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
                        # Simulate real signal for this SNR value
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
            # Try to get the base/specular angle from the output
            specular_angle = out.get('specular_angle', None)
            if specular_angle is None:
                specular_angle = out.get('base_angle', 0.0)

            if has_fine_phase and local_fine and snr_fine:
                if is_real_signal and ser_fine and any(s is not None for s in ser_fine):
                    # For real signal, use SER-best angle
                    ser_vals_idx = [i for i, s in enumerate(ser_fine) if s is not None]
                    if ser_vals_idx:
                        best_ser_idx = min(ser_vals_idx, key=lambda i: ser_fine[i])
                        best_final_local = local_fine[best_ser_idx]
                        best_final_snr = snr_fine[best_ser_idx]
                    else:
                        best_final_local = local_fine[int(np.argmax(snr_fine))]
                        best_final_snr = float(np.max(snr_fine))
                else:
                    # For physics-based, use SNR-best angle
                    best_final_local = local_fine[int(np.argmax(snr_fine))]
                    best_final_snr = float(np.max(snr_fine))
            else:
                if is_real_signal and ser_coarse and any(s is not None for s in ser_coarse):
                    # For real signal, use SER-best angle
                    ser_vals_idx = [i for i, s in enumerate(ser_coarse) if s is not None]
                    if ser_vals_idx:
                        best_ser_idx = min(ser_vals_idx, key=lambda i: ser_coarse[i])
                        best_final_local = local_coarse[best_ser_idx]
                        best_final_snr = snr_coarse[best_ser_idx]
                    else:
                        best_final_local = local_coarse[int(np.argmax(snr_coarse))]
                        best_final_snr = float(np.max(snr_coarse))
                else:
                    # For physics-based, use SNR-best angle
                    best_final_local = local_coarse[int(np.argmax(snr_coarse))]
                    best_final_snr = float(np.max(snr_coarse))

            best_final_abs = specular_angle + best_final_local

            # Show recommendation for RIS
            print('RECOMMENDATION TO SEND TO RIS:')
            print('-'*70)
            print(f'Beam Angle (Local):     {best_final_local:>8.2f}°')
            print(f'Beam Angle (Absolute):  {best_final_abs:>8.2f}°')
            print(f'Specular/Base Angle:    {specular_angle:>8.2f}°')
            print(f'Expected SNR:           {best_final_snr:>8.2f} dB')
            print()

            # Update/create active link with best result from sweep
            link_key = f"{ap}→{ris}→{ue}"
            ap_node = self.net.get(ap)
            ris_node = self.net.get(ris)
            ue_node = self.net.get(ue)
            ap_key = ap_node.name if ap_node else ap
            ris_key = ris_node.name if ris_node else ris
            ue_key = ue_node.name if ue_node else ue
            link_key = f"{ap_key}→{ris_key}→{ue_key} (Sweep)"

            self.net.active_links[link_key] = {
                'ap': ap_key,
                'ris': ris_key,
                'ue': ue_key,
                'snr_dB': float(best_final_snr),
                'pwr_dBm': float(out.get('pwr_coarse', [0])[0]) if out.get('pwr_coarse') else -63.67,
                'beam_angle': float(best_final_abs),
                'gain_dBi': 47.46,  # Typical value
                'quant_loss_dB': -0.75,  # Typical value
                'source': 'sweep'
            }

            sweep_record = {
                'type': 'sweep',
                'ap': ap_key,
                'ris': ris_key,
                'ue': ue_key,
                'captured_at': datetime.utcnow().isoformat() + 'Z',
                'algorithm': algo_name,
                'algorithm_alias': algo_requested,
                'parameters': {
                    'fov': fov,
                    'step': step,
                    'seed': seed,
                    'algo': algo_requested,
                    'ml_predictor': ml_predictor if algo_requested_lower in ['ml', 'ml-guided'] else None,
                    'use_waveform': use_waveform,
                    'modulation': modulation if use_waveform else None,
                    'enable_feedback': enable_feedback,
                    'num_symbols': kwargs.get('num_symbols')
                },
                'summary': {
                    'best_local_deg': float(best_final_local),
                    'best_abs_deg': float(best_final_abs),
                    'specular_deg': float(specular_angle),
                    'expected_snr_dB': float(best_final_snr)
                },
                'outputs': out
            }
            self.net.last_sweep_result = sanitize_for_json(sweep_record)

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
