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

        print(f"\nConnection Result (Feedback: {'Enabled' if enable_feedback else 'Disabled'}, "
              f"Waveform: {'Enabled (' + modulation + ')' if use_waveform else 'Disabled'}):")
        print("="*70)

        # Display physics-based results
        physics_result = {k: v for k, v in res.items() if k != 'signal_level'}
        pprint.pprint(physics_result)

        # Display signal-level results if available
        if use_waveform and 'signal_level' in res:
            print("\n[SIGNAL-LEVEL RESULTS (100% Real)]")
            print("-"*70)
            signal_info = {
                'Requested Modulation': res.get('requested_modulation', 'Unknown'),
                'Negotiated Modulation': res.get('negotiated_modulation', 'Unknown'),
                'SNR (dB)': f"{res['signal_level']['snr_dB']:.2f}",
                'SER (%)': f"{res['signal_level']['ser_percent']:.2f}",
                'Symbol Errors': res['signal_level']['symbol_errors'],
                'Total Symbols': res['signal_level']['total_symbols']
            }
            pprint.pprint(signal_info)

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
            # Pass parameters to algorithm based on type
            kwargs = {
                'fov': fov,
                'step': step,
                'enable_feedback': enable_feedback,
                'max_feedback_iterations': 3
            }
            if algo_name.lower() in ['ml', 'ml-guided']:
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
            self.net.active_links[link_key] = {
                'ap': ap,
                'ris': ris,
                'ue': ue,
                'snr_dB': float(best_final_snr),
                'pwr_dBm': float(out.get('pwr_coarse', [0])[0]) if out.get('pwr_coarse') else -63.67,
                'beam_angle': float(best_final_abs),
                'gain_dBi': 47.46,  # Typical value
                'quant_loss_dB': -0.75  # Typical value
            }

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
