"""
Connection and sweep operations handler
Extracted from main_shell.py for better modularity
"""

import shlex
import numpy as np
from datetime import datetime, timezone
from cli.helpers import sanitize_for_json


class ConnectionHandler:
    """Handles connection and beam sweep operations"""

    def __init__(self, net):
        self.net = net

    def parse_connect_arguments(self, arg):
        """Parse and validate connect command arguments

        Returns:
            tuple: (ap, ris, ue, remaining_parts, error_msg)
        """
        parts = shlex.split(arg) if arg else []

        # Gather all nodes by type
        aps = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'AccessPoint']
        riss = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'RIS']
        ues = [n for n, nd in self.net.nodes.items() if type(nd).__name__ == 'UE']

        ap = None
        ris = None
        ue = None
        remaining_parts = list(parts)

        # Extract node names from arguments
        if len(remaining_parts) > 0:
            candidate = remaining_parts[0]
            if candidate in aps:
                ap = candidate
                remaining_parts.pop(0)
            elif candidate.lower() in [a.lower() for a in aps]:
                ap = next(a for a in aps if a.lower() == candidate.lower())
                remaining_parts.pop(0)

        if len(remaining_parts) > 0:
            candidate = remaining_parts[0]
            if candidate in riss:
                ris = candidate
                remaining_parts.pop(0)
            elif candidate.lower() in [r.lower() for r in riss]:
                ris = next(r for r in riss if r.lower() == candidate.lower())
                remaining_parts.pop(0)

        if len(remaining_parts) > 0:
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
                return (None, None, None, None, "Error: No Access Points available in network")
            else:
                error_msg = "Error: Ambiguous AP selection. Available Access Points:\n"
                for a in aps:
                    error_msg += f"  - {a}\n"
                error_msg += f"Usage: connect <ap_name> [ris] [ue] [options]"
                return (None, None, None, None, error_msg)

        if ris is None:
            if len(riss) == 1:
                ris = riss[0]
            elif len(riss) == 0:
                return (None, None, None, None, "Error: No RIS nodes available in network")
            else:
                error_msg = f"Error: Ambiguous RIS selection for AP '{ap}'. Available RIS nodes:\n"
                for r in riss:
                    error_msg += f"  - {r}\n"
                error_msg += f"Usage: connect {ap} <ris_name> [ue] [options]"
                return (None, None, None, None, error_msg)

        if ue is None:
            if len(ues) == 1:
                ue = ues[0]
            elif len(ues) == 0:
                # Check if this is an OpenCV vision sweep (allows UE to be created from detection)
                # Look ahead in remaining_parts for --algo opencv or --sweep with opencv
                is_opencv_sweep = False
                for i, part in enumerate(remaining_parts):
                    if part == '--algo' and i + 1 < len(remaining_parts) and remaining_parts[i + 1] == 'opencv':
                        is_opencv_sweep = True
                        break
                    elif part == '--sweep' and '--algo' in remaining_parts:
                        algo_idx = remaining_parts.index('--algo')
                        if algo_idx + 1 < len(remaining_parts) and remaining_parts[algo_idx + 1] == 'opencv':
                            is_opencv_sweep = True
                            break

                if is_opencv_sweep:
                    # For OpenCV vision sweep, UE can be created from camera detection
                    # Try to extract UE name from remaining arguments
                    if len(remaining_parts) > 0 and not remaining_parts[0].startswith('--'):
                        ue = remaining_parts.pop(0)
                    else:
                        ue = 'ue1'  # Default UE name for OpenCV sweep
                else:
                    return (None, None, None, None, "Error: No User Equipment available in network")
            else:
                error_msg = f"Error: Ambiguous UE selection for {ap}→{ris}. Available UEs:\n"
                for u in ues:
                    error_msg += f"  - {u}\n"
                error_msg += f"Usage: connect {ap} {ris} <ue_name> [options]"
                return (None, None, None, None, error_msg)

        return (ap, ris, ue, remaining_parts, None)

    def parse_flags(self, parts):
        """Parse connection flags and parameters

        Returns:
            dict: Parsed flags with keys: enable_feedback, use_waveform, modulation,
                  fov, step, algo_name, ml_predictor, metric, angle, seed, error_msg,
                  enable_codebook_validation, codebook_increment, codebook_neighbors,
                  include_predicted_angle, r_cw, t_cw
        """
        result = {
            'enable_feedback': True,
            'use_waveform': True,
            'modulation': 'QPSK',
            'fov': None,
            'step': None,
            'algo_name': 'linear',
            'ml_predictor': 'gmf',
            'angle': None,
            'seed': None,
            'error_msg': None,
            'algo_specified': False,
            'ml_predictor_specified': False,
            'metric': 'snr',  # Default metric for beam selection
            'enable_codebook_validation': False,
            'codebook_increment': 5.0,
            'codebook_neighbors': 1,
            'include_predicted_angle': True,
            'codebook_start': 10.0,
            'codebook_end': 60.0,
            'codebook_step': 10.0,
            'use_mock': False,  # Use mock camera (default: false for real camera)
            'mock_trajectory': 'circular',  # Mock camera trajectory type
            'r_cw': 'rotation.npy',  # Camera-to-world rotation matrix (default path)
            't_cw': 'translation.npy',  # Camera-to-world translation vector (default path)
            'tapering': 'uniform',  # Tapering window (uniform, hamming, hann, blackman)
            'channel_model': None,
            'environment': 'indoor',
            'scenario': 1,
        }

        parts = list(parts)  # Make a copy

        # Parse simple flags
        if '--no-feedback' in parts:
            result['enable_feedback'] = False
            parts.remove('--no-feedback')

        if '--no-waveform' in parts:
            result['use_waveform'] = False
            parts.remove('--no-waveform')

        # Parse modulation
        if '--modulation' in parts:
            idx = parts.index('--modulation')
            if idx + 1 < len(parts):
                result['modulation'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse sweep parameters
        if '--sweep' in parts:
            idx = parts.index('--sweep')
            result['fov'] = 60.0  # Default FOV
            result['step'] = 10.0  # Default step

            if idx + 1 < len(parts) and not parts[idx + 1].startswith('--'):
                try:
                    result['fov'] = float(parts[idx + 1])
                    if idx + 2 < len(parts) and not parts[idx + 2].startswith('--'):
                        try:
                            result['step'] = float(parts[idx + 2])
                            parts = parts[:idx] + parts[idx+3:]
                        except ValueError:
                            parts = parts[:idx] + parts[idx+2:]
                    else:
                        parts = parts[:idx] + parts[idx+2:]
                except ValueError:
                    parts = parts[:idx] + parts[idx+1:]
            else:
                parts = parts[:idx] + parts[idx+1:]

        # Parse algorithm
        if '--algo' in parts:
            idx = parts.index('--algo')
            if idx + 1 < len(parts):
                result['algo_name'] = parts[idx + 1]
            result['algo_specified'] = True
            parts = parts[:idx] + parts[idx+2:]

        # Parse ML predictor
        if '--ml-predictor' in parts:
            idx = parts.index('--ml-predictor')
            if idx + 1 < len(parts):
                result['ml_predictor'] = parts[idx + 1]
            result['ml_predictor_specified'] = True
            parts = parts[:idx] + parts[idx+2:]

        # Parse codebook validation flag
        if '--enable-codebook-validation' in parts:
            result['enable_codebook_validation'] = True
            parts.remove('--enable-codebook-validation')

        # Parse codebook increment
        if '--codebook-increment' in parts:
            idx = parts.index('--codebook-increment')
            if idx + 1 < len(parts):
                try:
                    result['codebook_increment'] = float(parts[idx + 1])
                except ValueError:
                    pass
            parts = parts[:idx] + parts[idx+2:]

        # Parse codebook neighbors
        if '--codebook-neighbors' in parts:
            idx = parts.index('--codebook-neighbors')
            if idx + 1 < len(parts):
                try:
                    result['codebook_neighbors'] = int(parts[idx + 1])
                except ValueError:
                    pass
            parts = parts[:idx] + parts[idx+2:]

        # Parse include predicted angle flag
        if '--no-predicted-angle' in parts:
            result['include_predicted_angle'] = False
            parts.remove('--no-predicted-angle')

        # Parse codebook start
        if '--codebook-start' in parts:
            idx = parts.index('--codebook-start')
            if idx + 1 < len(parts):
                try:
                    result['codebook_start'] = float(parts[idx + 1])
                except ValueError:
                    pass
            parts = parts[:idx] + parts[idx+2:]

        # Parse codebook end
        if '--codebook-end' in parts:
            idx = parts.index('--codebook-end')
            if idx + 1 < len(parts):
                try:
                    result['codebook_end'] = float(parts[idx + 1])
                except ValueError:
                    pass
            parts = parts[:idx] + parts[idx+2:]

        # Parse codebook step
        if '--codebook-step' in parts:
            idx = parts.index('--codebook-step')
            if idx + 1 < len(parts):
                try:
                    result['codebook_step'] = float(parts[idx + 1])
                except ValueError:
                    pass
            parts = parts[:idx] + parts[idx+2:]

        # Parse metric for beam selection
        if '--metric' in parts:
            idx = parts.index('--metric')
            if idx + 1 < len(parts):
                result['metric'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse mock camera flag
        if '--use-mock' in parts:
            idx = parts.index('--use-mock')
            if idx + 1 < len(parts):
                use_mock_str = parts[idx + 1].lower()
                result['use_mock'] = use_mock_str in ['true', '1', 'yes', 'on']
                parts = parts[:idx] + parts[idx+2:]
            else:
                result['use_mock'] = True
                parts = parts[:idx] + parts[idx+1:]

        # Parse mock trajectory type
        if '--mock-trajectory' in parts:
            idx = parts.index('--mock-trajectory')
            if idx + 1 < len(parts):
                result['mock_trajectory'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse camera-to-world rotation matrix (as path to .npy file)
        if '--r-cw' in parts:
            idx = parts.index('--r-cw')
            if idx + 1 < len(parts):
                result['r_cw'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse camera-to-world translation vector (as path to .npy file)
        if '--t-cw' in parts:
            idx = parts.index('--t-cw')
            if idx + 1 < len(parts):
                result['t_cw'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        # Parse tapering window
        if '--tapering' in parts:
            idx = parts.index('--tapering')
            if idx + 1 < len(parts):
                result['tapering'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--channel-model' in parts:
            idx = parts.index('--channel-model')
            if idx + 1 < len(parts):
                result['channel_model'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--environment' in parts:
            idx = parts.index('--environment')
            if idx + 1 < len(parts):
                result['environment'] = parts[idx + 1]
            parts = parts[:idx] + parts[idx+2:]

        if '--scenario' in parts:
            idx = parts.index('--scenario')
            if idx + 1 < len(parts):
                try:
                    result['scenario'] = int(parts[idx + 1])
                except ValueError:
                    result['error_msg'] = "Error: --scenario must be an integer (1 or 2)"
                    return result
            parts = parts[:idx] + parts[idx+2:]

        # Helper to check if token is a number
        def _is_number(token):
            try:
                float(token)
                return True
            except (TypeError, ValueError):
                return False

        # Check for unknown flags
        unknown_flags = [p for p in parts if (p.startswith('-') and not _is_number(p))]
        if unknown_flags:
            result['error_msg'] = f"Error: Unknown flag(s): {', '.join(unknown_flags)}\nValid flags: --sweep, --algo, --metric, --modulation, --ml-predictor, --enable-codebook-validation, --codebook-increment, --codebook-neighbors, --codebook-start, --codebook-end, --codebook-step, --no-predicted-angle, --use-mock, --mock-trajectory, --r-cw, --t-cw, --tapering, --channel-model, --environment, --scenario, --no-waveform, --no-feedback"
            return result

        # Validate flag combinations
        if result['fov'] is None:
            if result['algo_specified']:
                result['error_msg'] = "Error: --algo flag only valid with --sweep mode"
                return result
            if result['ml_predictor_specified']:
                result['error_msg'] = "Error: --ml-predictor flag only valid with --sweep mode"
                return result

        # Parse optional numeric args (beam angle first, then optional seed)
        numeric_args = [p for p in parts if _is_number(p)]
        if numeric_args:
            result['angle'] = float(numeric_args[0])

        for candidate in numeric_args[1:]:
            if candidate.lstrip('-').isdigit():
                result['seed'] = int(candidate)
                break

        return result

    def execute_single_connect(self, ap, ris, ue, angle, enable_feedback, use_waveform, modulation, seed, tapering='uniform', metric='snr', channel_model=None, environment='indoor', scenario=1, print_func=print):
        """Execute single-angle connect measurement

        Args:
            ap: Access Point name
            ris: RIS name
            ue: UE name
            angle: Beam angle in degrees (None for auto-compute)
            enable_feedback: Enable CSI feedback
            use_waveform: Enable signal-level simulation
            modulation: Modulation type (QPSK, 16QAM, etc.)
            seed: Random seed for reproducibility
            tapering: Tapering window type (uniform, hamming, hann, blackman)
            metric: Beam selection metric (snr, rssi, csi) - for future RSSI/CSI support
            print_func: Function for output printing
        """
        try:
            print_func(f"\n{'='*70}")
            print_func(f"CONNECTION PROCESS: {ap} → {ris} → {ue}")
            print_func(f"{'='*70}")

            print_func(f"\n[STEP 1] Retrieve Node References")
            try:
                ap_node = self.net.nodes.get(ap)
                ris_node = self.net.nodes.get(ris)
                ue_node = self.net.nodes.get(ue)

                print_func(f"  ✓ AP (Access Point):  {ap}")
                if ap_node and hasattr(ap_node, 'pos'):
                    print_func(f"    Position: x={ap_node.pos[0]:.2f}, y={ap_node.pos[1]:.2f}, z={ap_node.pos[2]:.2f}")

                print_func(f"  ✓ RIS (Reflector):    {ris}")
                if ris_node and hasattr(ris_node, 'pos'):
                    print_func(f"    Position: x={ris_node.pos[0]:.2f}, y={ris_node.pos[1]:.2f}, z={ris_node.pos[2]:.2f}")
                    if hasattr(ris_node, 'normal_angle_deg'):
                        print_func(f"    Normal Angle: {ris_node.normal_angle_deg:.1f}°")

                print_func(f"  ✓ UE (Device):        {ue}")
                if ue_node and hasattr(ue_node, 'pos'):
                    print_func(f"    Position: x={ue_node.pos[0]:.2f}, y={ue_node.pos[1]:.2f}, z={ue_node.pos[2]:.2f}")
            except Exception as e:
                print_func(f"  (Position data unavailable: {e})")

            print_func(f"\n[STEP 2] Compute Geometry & FOV Validation")
            print_func(f"  Computing: distances, beam angles, field-of-view...")
            try:
                if ap_node and ris_node and ue_node:
                    d_ap_ris = np.linalg.norm(ris_node.pos - ap_node.pos)
                    d_ris_ue = np.linalg.norm(ue_node.pos - ris_node.pos)
                    print_func(f"    AP→RIS distance: {d_ap_ris:.2f} m")
                    print_func(f"    RIS→UE distance: {d_ris_ue:.2f} m")
            except Exception:
                pass

            print_func(f"\n[STEP 3] Calculate RIS Phase Configuration & Path Loss & Array Gain")

            res = self.net.connect(
                ap,
                ris,
                ue,
                beam_angle_deg=angle,
                seed=seed,
                enable_feedback=enable_feedback,
                max_feedback_iterations=3,
                tapering=tapering,
                channel_model=channel_model,
                environment=environment,
                scenario=scenario,
            )

            # Show phase configuration results
            print_func(f"  Phase Configuration:")
            if 'incident_azimuth_deg' in res:
                print_func(f"    Incident Angle (AP→RIS): {res['incident_azimuth_deg']:.1f}°")
            if 'reflected_azimuth_deg' in res:
                print_func(f"    Reflection Angle (RIS→UE): {res['reflected_azimuth_deg']:.1f}°")

            # Use deflection_angle_deg if available (actual RIS command), otherwise local_deflection_deg
            deflection = res.get('deflection_angle_deg')
            if deflection is None:
                deflection = res.get('local_deflection_deg')
            if deflection is not None:
                print_func(f"    Required RIS Deflection: {float(deflection):.1f}°")

            # Show path loss and gain
            print_func(f"  Path Loss & Array Gain:")
            try:
                if ap_node and ris_node and ue_node and hasattr(ap_node, 'freq'):
                    from core.physics import Physics
                    d_ap_ris = np.linalg.norm(ris_node.pos - ap_node.pos)
                    d_ris_ue = np.linalg.norm(ue_node.pos - ris_node.pos)
                    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap_node.freq)
                    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap_node.freq)
                    print_func(f"    AP→RIS path loss ({d_ap_ris:.2f} m): {pl_ap_ris:.2f} dB")
                    print_func(f"    RIS→UE path loss ({d_ris_ue:.2f} m): {pl_ris_ue:.2f} dB")
            except Exception:
                pass

            if 'gain_dBi' in res:
                print_func(f"    RIS array gain + antenna gains: {res['gain_dBi']:.2f} dBi")
            if 'quant_loss_dB' in res and res['quant_loss_dB'] != 0:
                print_func(f"    Quantization loss: {abs(float(res['quant_loss_dB'])):.3f} dB")
            if res.get('channel_model_requested') is not None:
                print_func(f"    Engine requested: {res['channel_model_requested']}")
            if res.get('channel_model_used') is not None:
                print_func(f"    Engine used: {res['channel_model_used']}")
            if res.get('channel_model_fallback_reason'):
                print_func(f"    Engine fallback: {res['channel_model_fallback_reason']}")

            print_func(f"\n[STEP 4] Query SNR from UE (via Control Channel)")
            print_func(f"  Action: Controller queries UE for measured SNR...")
            print_func(f"  ✓ SNR Result: {res['snr_dB']:.2f} dB")

            print_func(f"\n[STEP 5] Store Link Metadata on UE")
            print_func(f"  Storing: (AP, RIS) → SNR, power, gain, phases...")
            print_func(f"  Key: ('{ap}', '{ris}')")

            print_func(f"\n[STEP 6] Create & Activate Link")
            link_key = f"{ap}→{ris}→{ue}"
            print_func(f"  Link: {link_key}")
            print_func(f"  Status: ✓ ESTABLISHED - Ready for data transmission")

        except ValueError as e:
            print_func(f"\n✗ {e}\n")
            return None

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

                snr_linear = 10 ** (res['snr_dB'] / 10)
                noise_power_linear = 1.0 / snr_linear
                noise_power_dB = 10 * np.log10(noise_power_linear)
                signal_result = link_simulator.simulate_link(
                    path_loss_dB=0.0,
                    noise_power_dB=noise_power_dB,
                    K_factor=5.0,
                    seed=seed if seed else None
                )

                res['signal_level'] = signal_result
                res['ser_percent'] = signal_result['ser_percent']
                res['requested_modulation'] = modulation

                if 'feedback_info' in res and 'final_iteration' in res['feedback_info']:
                    final_iter = res['feedback_info']['final_iteration']
                    if 'ap_mcs' in final_iter:
                        res['negotiated_modulation'] = final_iter['ap_mcs']
                    else:
                        res['negotiated_modulation'] = modulation
                else:
                    res['negotiated_modulation'] = modulation
            except ImportError:
                pass

        return res

    def print_connect_results(self, res, ap, ris, ue, enable_feedback, use_waveform, modulation, angle, seed, print_func=print):
        """Print detailed connection results"""

        def _fmt_value(value, precision=2):
            if isinstance(value, (int, np.integer)) or (isinstance(value, float) and value.is_integer()):
                return f"{int(value)}"
            if isinstance(value, (float, np.floating)):
                return f"{value:.{precision}f}"
            return str(value)

        def _get_direction_desc(deflection_deg):
            deflection_deg = float(deflection_deg)
            while deflection_deg > 180:
                deflection_deg -= 360
            while deflection_deg < -180:
                deflection_deg += 360

            if abs(deflection_deg) < 5:
                return "aligned with RIS normal"
            elif deflection_deg > 0:
                return "clockwise from RIS normal"
            else:
                return "counterclockwise from RIS normal"

        def _print_table(title, rows):
            printable = [(label, _fmt_value(val)) for label, val in rows if val is not None]
            if not printable:
                return
            width = max(len(label) for label, _ in printable)
            print_func(f"\n[{title}]")
            print_func("-"*70)
            for label, value in printable:
                print_func(f"  {label:<{width}} : {value}")

        print_func(f"\n{'='*70}")
        print_func(f"LINK ESTABLISHED - DETAILED METRICS")
        print_func(f"{'='*70}")
        print_func(f"Feedback:  {'Enabled (Adaptive)' if enable_feedback else 'Disabled (Single-shot)'}")
        print_func(f"Waveform:  {'Enabled (' + modulation + ')' if use_waveform else 'Disabled (Physics-only)'}")
        print_func("="*70)

        physics_rows = []
        for label, key in [
            ("SNR (dB)", "snr_dB"),
            ("RSSI (dBm)", "rssi_dBm"),
            ("Power (dBm)", "pwr_dBm"),
            ("Gain (dBi)", "gain_dBi"),
            ("Gain (linear)", "gain_linear"),
            ("Beam Angle (deg)", "beam_angle"),
            ("Quant Penalty (dB)", "quant_loss_dB"),
            ("EVM (%)", "evm_percent"),
            ("SER (%)", "ser_percent")
        ]:
            if key in res:
                value = res[key]
                if key == "quant_loss_dB" and isinstance(value, (int, float)):
                    value = abs(value)
                physics_rows.append((label, value))
        _print_table("PHYSICS METRICS", physics_rows)

        if 'snr_dB' in res:
            snr_dB = float(res.get('snr_dB', 0))
            deflection_angle = res.get('deflection_angle_deg')
            incident_azimuth = res.get('incident_azimuth_deg')
            reflected_azimuth = res.get('reflected_azimuth_deg')

            print_func("\n[RECOMMENDATION TO SEND TO RIS]")
            print_func("-"*70)

            if deflection_angle is not None:
                fov_clamped = res.get('fov_clamped', False)
                max_angle = res.get('max_angle_deg', 60)

                if fov_clamped:
                    print_func(f"RIS deflection angle above {max_angle:.0f}° hardware FOV limit")
                else:
                    print_func(f"Steering Angle (Local Deflection): {float(deflection_angle):>8.2f}°")
            else:
                local_deflection = float(res.get('local_deflection_deg', 0))
                print_func(f"Steering Angle (Local Deflection): {local_deflection:>8.2f}°")

            print_func(f"Expected SNR:                   {snr_dB:>8.2f} dB")


    def create_connection_record(self, ap, ris, ue, res, angle, seed, enable_feedback, use_waveform, modulation):
        """Create a connection record for saving"""
        return {
            'type': 'connect',
            'ap': ap,
            'ris': ris,
            'ue': ue,
            'captured_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
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

    def execute_sweep(self, ap, ris, ue, fov, step, algo_name, ml_predictor, enable_feedback, use_waveform, modulation, seed, metric='snr', enable_codebook_validation=False, codebook_increment=5.0, codebook_neighbors=1, include_predicted_angle=True, codebook_start=10.0, codebook_end=60.0, codebook_step=10.0, use_mock=False, mock_trajectory='circular', r_cw=None, t_cw=None, tapering='uniform', print_func=print):
        """Execute multi-angle sweep"""
        try:
            from controller.beamsweeping import SweepAlgorithmLoader
            algo = SweepAlgorithmLoader.get_algorithm(algo_name, self.net)
        except ValueError as e:
            print_func(f"Error: {e}")
            return None
        except Exception as e:
            print_func(f"Error loading sweep algorithm: {e}")
            return None

        # For OpenCV vision sweep, UE may not exist yet (will be created from detection)
        # For other algorithms, all nodes must exist
        if algo_name.lower() == 'opencv':
            if not self.net.get(ap) or not self.net.get(ris):
                print_func(f"Error: Invalid node names - AP and RIS must exist")
                return None
        else:
            if not self.net.get(ap) or not self.net.get(ris) or not self.net.get(ue):
                print_func(f"Error: Invalid node names")
                return None

        print_func('\n' + '='*70)
        print_func('BEAM SWEEP (via unified connect command)')
        print_func('='*70)

        try:
            # Create standardized metric selector
            from utils import create_metric_selector
            metric_selector = create_metric_selector(metric)

            # CRITICAL FIX: Disable feedback during sweep
            # Feedback modifies UE state across measurements, causing incorrect results
            # Example: connect shows 44.92°, but sweep showed 20° because feedback was
            # interfering with independent angle measurements
            # Sweep needs clean physics-based measurements for each angle
            sweep_enable_feedback = False

            kwargs = {
                'fov': fov,
                'step': step,
                'enable_feedback': sweep_enable_feedback,  # Always False for sweep
                'max_feedback_iterations': 3,
                'metric': metric,  # Beam selection metric string (for reference)
                # NOTE: metric_selector NOT passed to algorithm
                # Post-processing (line 740+) handles metric-based selection after CSI/RSSI computed
                'tapering': tapering,
                'seed': seed  # Pass seed to algorithm for reproducibility
            }
            if algo_name.lower() in ['ml', 'ml-guided']:
                kwargs['ml_predictor'] = ml_predictor
                kwargs['enable_codebook_validation'] = enable_codebook_validation
                kwargs['codebook_increment'] = codebook_increment
                kwargs['codebook_neighbors'] = codebook_neighbors
                kwargs['include_predicted_angle'] = include_predicted_angle
                kwargs['codebook_start'] = codebook_start
                kwargs['codebook_end'] = codebook_end
                kwargs['codebook_step'] = codebook_step

            if use_waveform:
                kwargs['use_waveform'] = True
                kwargs['modulation'] = modulation
                kwargs['num_symbols'] = 1000

            # Add mock camera parameters for opencv algorithm
            if algo_name.lower() in ['opencv', 'vision', 'aruco']:
                kwargs['use_mock'] = use_mock
                # Use static trajectory by default for simple testing
                kwargs['mock_trajectory'] = 'static' if mock_trajectory == 'circular' else mock_trajectory
                # Enable viewer (works with X11/VcXsrv on Windows)
                kwargs['enable_viewer'] = True

                # Handle camera-to-world transformations
                if use_mock:
                    # Use identity transform for mock camera (no external calibration needed)
                    # Try to load from files if they exist, otherwise use defaults
                    try:
                        if r_cw and isinstance(r_cw, str):
                            import os
                            if os.path.exists(r_cw):
                                kwargs['r_cw'] = np.load(r_cw)
                            else:
                                kwargs['r_cw'] = np.eye(3, dtype=np.float64)
                        else:
                            kwargs['r_cw'] = np.eye(3, dtype=np.float64)
                    except Exception as e:
                        print_func(f"Warning: Could not load r_cw, using identity: {e}")
                        kwargs['r_cw'] = np.eye(3, dtype=np.float64)

                    try:
                        if t_cw and isinstance(t_cw, str):
                            import os
                            if os.path.exists(t_cw):
                                kwargs['t_cw'] = np.load(t_cw)
                            else:
                                kwargs['t_cw'] = np.zeros(3, dtype=np.float64)
                        else:
                            kwargs['t_cw'] = np.zeros(3, dtype=np.float64)
                    except Exception as e:
                        print_func(f"Warning: Could not load t_cw, using zeros: {e}")
                        kwargs['t_cw'] = np.zeros(3, dtype=np.float64)
                else:
                    # For real camera, try loading calibration; otherwise fall back to default
                    try:
                        import os
                        if r_cw and isinstance(r_cw, str) and os.path.exists(r_cw):
                            kwargs['r_cw'] = np.load(r_cw)
                        else:
                            print_func("[OPENCV] No r_cw provided - assuming camera axes aligned with RIS.")

                        if t_cw and isinstance(t_cw, str) and os.path.exists(t_cw):
                            kwargs['t_cw'] = np.load(t_cw)
                        else:
                            print_func("[OPENCV] No t_cw provided - assuming camera located at RIS position.")
                    except Exception as e:
                        print_func(f"Error loading camera transformations: {e}")
                        return None

            out = algo.sweep(ap, ris, ue, **kwargs)

            # Compute metric-specific values for display
            if metric.lower() == 'rssi' and 'snr_coarse' in out:
                # Compute RSSI from SNR and noise power
                from utils.rssi import rssi_from_snr
                noise_power = 10 ** (-10 / 10)  # Assume -10 dB noise power as reference
                out['rssi_coarse'] = [rssi_from_snr(snr_val, noise_power) for snr_val in out.get('snr_coarse', [])]
                if 'snr_fine' in out:
                    out['rssi_fine'] = [rssi_from_snr(snr_val, noise_power) for snr_val in out.get('snr_fine', [])]

            if metric.lower() in ['csi', 'csi_quality'] and 'snr_coarse' in out:
                # Compute CSI quality metrics
                from utils.csi import estimate_channel_capacity_bps_hz
                out['csi_quality_coarse'] = [estimate_channel_capacity_bps_hz(snr_val) for snr_val in out.get('snr_coarse', [])]
                if 'snr_fine' in out:
                    out['csi_quality_fine'] = [estimate_channel_capacity_bps_hz(snr_val) for snr_val in out.get('snr_fine', [])]

            # Post-process waveform simulation if needed
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
                    pass

            # Post-process: Apply metric-based beam selection if metric != 'snr'
            if metric.lower() != 'snr' and out is not None:
                from utils import create_metric_selector
                metric_selector = create_metric_selector(metric)

                # Determine which phase to use for final selection
                has_fine_phase = 'snr_fine' in out and len(out.get('snr_fine', [])) > 0

                if has_fine_phase:
                    # Fine phase exists - use it for final selection
                    if metric.lower() in ['rssi', 'power'] and 'rssi_fine' in out:
                        metric_values = out['rssi_fine']
                    elif metric.lower() in ['csi', 'csi_quality'] and 'csi_quality_fine' in out:
                        metric_values = out['csi_quality_fine']
                    else:
                        metric_values = out['snr_fine']
                    best_idx = metric_selector.find_best_index(metric_values)

                    if best_idx < len(out.get('local_fine', [])):
                        out['best_local_fine'] = float(out['local_fine'][best_idx])
                        out['best_snr_fine'] = float(out['snr_fine'][best_idx])
                        out['best_angle'] = float(out['local_fine'][best_idx])
                        out['best_snr'] = float(out['snr_fine'][best_idx])
                else:
                    # Only coarse phase - select based on metric
                    if metric.lower() in ['rssi', 'power'] and 'rssi_coarse' in out:
                        metric_values = out['rssi_coarse']
                    elif metric.lower() in ['rssi', 'power'] and 'pwr_coarse' in out:
                        metric_values = out['pwr_coarse']
                    elif metric.lower() in ['csi', 'csi_quality'] and 'csi_quality_coarse' in out:
                        metric_values = out['csi_quality_coarse']
                    else:
                        metric_values = out.get('snr_coarse', out.get('snr', []))

                    best_idx = metric_selector.find_best_index(metric_values)

                    # Update best beam info from coarse phase
                    if best_idx < len(out.get('local_coarse', [])):
                        out['best_angle'] = float(out['local_coarse'][best_idx])
                        if 'snr_coarse' in out:
                            out['best_snr'] = float(out['snr_coarse'][best_idx])
                        if 'pwr_coarse' in out:
                            out['best_power'] = float(out['pwr_coarse'][best_idx])

            return out

        except ValueError as e:
            print_func(f"\n✗ {e}\n")
            return None
        except Exception as e:
            print_func(f"\nError during sweep: {e}\n")
            return None

    def print_sweep_results(self, out, fov, step, ap, ris, ue, algo_name, metric='snr', print_func=print):
        """Print detailed sweep results and return best beam angle info"""
        def _normalize_sequence(values):
            if values is None:
                return []
            if isinstance(values, np.ndarray):
                return values.tolist()
            return values

        algo = out.get('algo_object') or {'name': algo_name}
        algo_display_name = getattr(algo, 'name', algo_name) if hasattr(algo, 'name') else algo_name

        algo_name_clean = algo_display_name.replace('Sweep', '').strip()
        suppress_ml_details = algo_name.lower() in ('ml', 'ml-guided', 'gmf') or algo_display_name.lower().startswith('ml')
        if out.get('suppress_tables'):
            suppress_ml_details = True

        has_fine_phase = 'local_fine' in out and len(_normalize_sequence(out.get('local_fine', []))) > 0

        if not suppress_ml_details:
            print_func(f'\n[ALGORITHM: {algo_display_name}]')
            print_func('-'*70)

        # Initialize metadata variables (used later at line 1084+)
        loc = out.get('location', {}) or {}
        meta = out.get('metadata', {}) or {}
        recommendation_status = meta.get('recommendation_status', 'ok')
        no_reliable_estimate = recommendation_status == 'no_reliable_estimate'

        # Show ANM-specific summary if present
        if 'mode' in out:
            print_func('ANM SUMMARY:')
            print_func('-'*70)
            print_func(f"Mode: {out.get('mode')}")
            mode_note = meta.get('mode_note')
            if mode_note:
                print_func(f"Note: {mode_note}")
            if loc:
                if loc.get('type') == 'direction-only':
                    az = loc.get('azimuth')
                    el = loc.get('elevation')
                    if az is not None and el is not None:
                        print_func(f"Direction: az={az:.2f}°, el={el:.2f}°")
                    elif az is not None:
                        print_func(f"Direction: az={az:.2f}°")
                else:
                    print_func(
                        "Position: x={:.2f} m, y={:.2f} m, z={:.2f} m".format(
                            loc.get('x', float('nan')),
                            loc.get('y', float('nan')),
                            loc.get('z', float('nan')),
                        )
                    )
            curvature = out.get('curvature')
            thresh = out.get('curvature_threshold')
            print_func(f"Curvature: {curvature:.4f} (threshold {thresh})")
            confidence = out.get('confidence')
            if confidence is not None:
                print_func(f"Confidence: {confidence:.3f}")
            solver_status = meta.get('solver_status')
            solver_time = meta.get('solver_time_sec')
            if solver_status or solver_time:
                status_str = solver_status or 'unknown'
                time_str = f"{solver_time:.3f}s" if solver_time is not None else "n/a"
                print_func(f"Solver: {status_str} in {time_str}")
            # Step-by-step trace
            print_func("Process:")
            ris_normal = meta.get('ris_normal_deg')
            ap_angle = meta.get('ap_angle_deg')
            ue_angle = meta.get('ue_angle_deg')
            if ris_normal is not None and ap_angle is not None and ue_angle is not None:
                print_func(f"  Step 1: Geometry — AP={ap_angle:.2f}°, UE={ue_angle:.2f}°, RIS normal={ris_normal:.2f}°")
            fov = meta.get('fov_deg')
            step = meta.get('step_deg')
            if fov is not None and step is not None:
                angle_count = meta.get('angles_tested_count', len(out.get('local_coarse', [])))
                print_func(f"  Step 2: Sweep — fov=±{fov:.1f}°, step={step:.1f}°, angles tested={angle_count}")
            prelim = meta.get('mode_decision')
            if prelim:
                nf_flag = "near-field" if prelim == "near-field" else "far-field"
                print_func(f"  Step 3: Curvature → mode decision: {nf_flag}")
            anm_az = meta.get('anm_estimated_az_deg')
            if anm_az is not None:
                print_func(f"  Step 4: ANM azimuth estimate: {anm_az:.2f}°")
            rec_loc = meta.get('recommended_local_angle')
            rec_loc_ris = meta.get('recommended_local_angle_ris')
            rec_abs = meta.get('recommended_abs_angle')
            src = meta.get('angle_recommendation_source', 'unknown')
            if no_reliable_estimate:
                loss_val = meta.get('hybrid_model_fit_loss')
                if loss_val is not None:
                    print_func(
                        "  Step 5: Steering recommendation skipped — "
                        f"no reliable estimate (model loss={loss_val:.4f} > threshold)."
                    )
                else:
                    print_func("  Step 5: Steering recommendation skipped — no reliable estimate.")
            elif rec_loc is not None and rec_abs is not None:
                if rec_loc_ris is not None:
                    print_func(
                        f"  Step 5: Steering recommendation ({src}): "
                        f"local(AP)={rec_loc:.2f}°, local(RIS)={rec_loc_ris:.2f}°, abs={rec_abs:.2f}°"
                    )
                else:
                    print_func(f"  Step 5: Steering recommendation ({src}): local={rec_loc:.2f}°, abs={rec_abs:.2f}°")

            # Show measurement table for PRIME/ANM algorithms
            measurements = out.get('measurements', {})
            if isinstance(measurements, dict) and measurements and algo_name.lower() in ('prime', 'anm', 'anm-localization') and not out.get('suppress_tables'):
                angles_tested = measurements.get('angles_tested', [])
                snr_values = measurements.get('snr_values', [])
                if angles_tested and snr_values and len(angles_tested) == len(snr_values):
                    try:
                        print_func("\nMEASURED SNR PATTERN:")
                        print_func('-'*70)
                        ris_normal_deg = meta.get('ris_normal_deg', 0)
                        ap_angle_deg = meta.get('ap_angle_deg', 0)

                        def _wrap_pm180(angle_val: float) -> float:
                            return ((angle_val + 180.0) % 360.0) - 180.0

                        angles_local_ris = [_wrap_pm180(a - ris_normal_deg) for a in angles_tested]
                        angles_local_ap = [_wrap_pm180(a - ap_angle_deg) for a in angles_tested]
                        peak_idx = int(np.nanargmax(snr_values))

                        print_func(f"{'Angle(local_AP)°':>18} {'Angle(local_RIS)°':>18} {'Angle(abs)°':>14} {'SNR(dB)':>10} {'Peak?':>8}")
                        print_func('-'*80)
                        for i, (a_loc_ap, a_loc_ris, a_abs, snr) in enumerate(zip(angles_local_ap, angles_local_ris, angles_tested, snr_values)):
                            marker = " <--" if i == peak_idx else ""
                            print_func(f"{a_loc_ap:18.1f} {a_loc_ris:18.1f} {a_abs:14.1f} {snr:10.2f}{marker}")

                        print_func(
                            f"\nPeak: {snr_values[peak_idx]:.2f} dB "
                            f"at {angles_local_ap[peak_idx]:.1f}° (local_AP) / "
                            f"{angles_local_ris[peak_idx]:.1f}° (local_RIS), "
                            f"{angles_tested[peak_idx]:.1f}° (abs)"
                        )
                    except Exception as e:
                        print_func(f"Error displaying measurement table: {e}")

            print_func()

        local_coarse = _normalize_sequence(out.get('local_coarse', []))
        snr_coarse = _normalize_sequence(out.get('snr_coarse', []))
        pwr_coarse = _normalize_sequence(out.get('pwr_coarse', []))

        local_fine = _normalize_sequence(out.get('local_fine', []))
        snr_fine = _normalize_sequence(out.get('snr_fine', []))

        ser_coarse = _normalize_sequence(out.get('ser_coarse', []))
        ser_fine = _normalize_sequence(out.get('ser_fine', []))
        is_real_signal = ser_coarse is not None and len(ser_coarse) > 0

        ml_results = _normalize_sequence(out.get('ml_results', []))
        ml_suggestions = _normalize_sequence(out.get('ml_suggestions', []))

        if not suppress_ml_details:
            # Calculate efficiency metrics
            total_angles_tested = len(local_coarse)
            if has_fine_phase:
                total_angles_tested += len(local_fine)
                exhaustive_count = int(2 * fov / step) + 1
                efficiency = (1.0 - len(local_coarse) / exhaustive_count) * 100
                if ml_results:
                    print_func(f'[THREE-PHASE SWEEP: ML ({len(ml_results)} suggestions) + Coarse ({len(local_coarse)} angles) + Fine ({len(local_fine)} angles)]')
                    total_angles_tested += len(ml_results)
                    print_func(f'Total angles tested: {total_angles_tested} | Efficiency gain: ~{efficiency:.1f}%')
                else:
                    print_func(f'[TWO-PHASE SWEEP: Coarse ({len(local_coarse)} angles) + Fine ({len(local_fine)} angles)]')
                    print_func(f'Total angles tested: {total_angles_tested} | Efficiency gain: ~{efficiency:.1f}%')
            else:
                print_func(f'[SINGLE-PHASE SWEEP]')
                print_func(f'Total angles tested: {total_angles_tested}')
            print_func()

            # Show ML predictions if available
            if ml_results:
                print_func('ML PREDICTOR RESULTS:')
                print_func('-'*70)
                print_func(f'Predictor: {out.get("ml_predictor", "unknown")}')
                print_func(f'Suggestions: {[f"{a:.1f}°" for a in ml_suggestions]}')

                ml_metrics = out.get("ml_metrics", {})
                if ml_metrics:
                    pred_time = ml_metrics.get('prediction_time_ms', 0)
                    uncertainty = ml_metrics.get('uncertainty', 0)
                    error_bounds = ml_metrics.get('error_bounds', 0)
                    model_avail = ml_metrics.get('model_available', False)
                    model_status = "✓ Loaded" if model_avail else "✗ Unavailable"

                    print_func(f'Prediction Time: {pred_time:.3f} ms | Uncertainty: ±{uncertainty:.1f}° | Model: {model_status}')
                    print_func(f'Error Bounds: ±{error_bounds:.1f}°')
                print_func()

                header = f'{"Suggestion (°)":<18} {"SNR (dB)":<15} {"Power (dBm)":<15}'
                print_func(header)
                print_func('-'*70)
                best_ml_idx = int(np.argmax([r["snr_dB"] for r in ml_results]))
                for i, result in enumerate(ml_results):
                    marker = " <-- BEST IN ML" if i == best_ml_idx else ""
                    print_func(f'{result["local_angle"]:>16.1f}  {result["snr_dB"]:>13.2f}  {result["pwr_dBm"]:>13.2f}{marker}')
                print_func()

            if local_coarse and snr_coarse:
                print_func('COARSE PHASE RESULTS:')
                print_func('-'*70)
                if is_real_signal and ser_coarse and any(s is not None for s in ser_coarse):
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"SER (%)":<15}'
                    print_func(header)
                    print_func('-'*70)
                    ser_vals = [s for s in ser_coarse if s is not None]
                    if ser_vals:
                        best_idx = int(np.argmin(ser_coarse))
                    else:
                        best_idx = int(np.argmax(snr_coarse))
                    for i, (angle, snr) in enumerate(zip(local_coarse, snr_coarse)):
                        ser = ser_coarse[i] if i < len(ser_coarse) and ser_coarse[i] is not None else 0.0
                        marker = " <-- BEST" if i == best_idx else ""
                        print_func(f'{angle:>11.1f}  {snr:>13.2f}  {ser:>13.2f}{marker}')
                else:
                    # Determine which metric column to display
                    if metric.lower() in ['rssi', 'power']:
                        # Display RSSI or Power values
                        if 'rssi_coarse' in out:
                            metric_values = out['rssi_coarse']
                            metric_label = 'RSSI (dBm)'
                        else:
                            metric_values = pwr_coarse
                            metric_label = 'Power (dBm)'
                    elif metric.lower() in ['csi', 'csi_quality']:
                        # Display CSI quality metrics
                        metric_values = out.get('csi_quality_coarse', snr_coarse)
                        metric_label = 'CSI Quality (bps/Hz)'
                    else:
                        # Default: Display SNR
                        metric_values = snr_coarse
                        metric_label = 'SNR (dB)'

                    header = f'{"Local (°)":<12} {metric_label:^25}'
                    print_func(header)
                    print_func('-'*70)

                    # Use metric-selected best angle from output dict (handles metric-based selection)
                    best_angle_selected = out.get('best_angle')
                    best_idx = None
                    if best_angle_selected is not None:
                        # Find index matching the selected best angle
                        for i, angle in enumerate(local_coarse):
                            if abs(float(angle) - float(best_angle_selected)) < 0.01:
                                best_idx = i
                                break
                    if best_idx is None:
                        # Fallback to metric value
                        best_idx = int(np.argmax(metric_values))

                    for i, (angle, metric_val) in enumerate(zip(local_coarse, metric_values)):
                        marker = " <-- BEST" if i == best_idx else ""
                        print_func(f'{angle:>11.1f}  {metric_val:>21.4f}{marker}')
                print_func()

            # Show fine phase results if available
            if has_fine_phase and local_fine and snr_fine:
                print_func('FINE PHASE RESULTS:')
                print_func('-'*70)
                if is_real_signal and ser_fine and any(s is not None for s in ser_fine):
                    header = f'{"Local (°)":<12} {"SNR (dB)":<15} {"SER (%)":<15}'
                    print_func(header)
                    print_func('-'*70)
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
                            print_func(f'{angle:>11.1f}  {snr:>13.2f}  {ser:>13.2f}{marker}')
                        else:
                            print_func(f'{angle:>11.1f}  {snr:>13.2f}  {"N/A":>13s}')
                else:
                    # Determine which metric column to display
                    if metric.lower() in ['rssi', 'power']:
                        if 'rssi_fine' in out:
                            metric_values = out['rssi_fine']
                            metric_label = 'RSSI (dBm)'
                        else:
                            metric_values = snr_fine
                            metric_label = 'SNR (dB)'
                    elif metric.lower() in ['csi', 'csi_quality']:
                        metric_values = out.get('csi_quality_fine', snr_fine)
                        metric_label = 'CSI Quality (bps/Hz)'
                    else:
                        metric_values = snr_fine
                        metric_label = 'SNR (dB)'

                    header = f'{"Local (°)":<12} {metric_label:^25}'
                    print_func(header)
                    print_func('-'*70)
                    # Use metric-selected best angle from output dict (handles metric-based selection)
                    best_angle_selected = out.get('best_angle')
                    best_fine_idx = None
                    if best_angle_selected is not None:
                        # Find index in fine phase matching the selected best angle
                        for i, angle in enumerate(local_fine):
                            if abs(float(angle) - float(best_angle_selected)) < 0.01:
                                best_fine_idx = i
                                break
                    if best_fine_idx is None:
                        # Fallback to metric value
                        best_fine_idx = int(np.argmax(metric_values))

                    for i, (angle, metric_val) in enumerate(zip(local_fine, metric_values)):
                        marker = " <-- BEST OVERALL" if i == best_fine_idx else ""
                        print_func(f'{angle:>11.1f}  {metric_val:>21.4f}{marker}')
                print_func()

                best_coarse_snr = float(np.max(snr_coarse))
                best_snr_fine = float(np.max(snr_fine))
                improvement = best_snr_fine - best_coarse_snr
                print_func('SUMMARY:')
                print_func('-'*70)
                print_func(f'Best coarse SNR:        {best_coarse_snr:>8.2f} dB')
                print_func(f'Best fine SNR:          {best_snr_fine:>8.2f} dB')
                print_func(f'Improvement:            {improvement:>8.2f} dB')
                print_func()

        # Calculate final best beam angle
        specular_angle = out.get('specular_angle', None)
        if specular_angle is None:
            specular_angle = out.get('base_angle', 0.0)

        # If tables are suppressed (e.g., ANM), prefer recommended angles from metadata
        best_final_local = None
        best_final_local_ris = None
        best_final_snr = None
        meta_recommended_local = meta.get('recommended_local_angle')
        meta_recommended_local_ris = meta.get('recommended_local_angle_ris')
        meta_recommended_abs = meta.get('recommended_abs_angle')
        meta_meas_best_snr = None
        meas = out.get('measurements', {})
        if isinstance(meas, dict) and meas:
            meta_meas_best_snr = meas.get('best_snr_dB')
        best_final_abs = None

        if not no_reliable_estimate:
            use_metadata_angles = out.get('suppress_tables') and meta_recommended_local is not None
            if use_metadata_angles:
                best_final_local = float(meta_recommended_local)
                best_final_abs = float(meta_recommended_abs) if meta_recommended_abs is not None else float(specular_angle + best_final_local)
                best_final_snr = float(meta_meas_best_snr) if meta_meas_best_snr is not None else None
                if meta_recommended_local_ris is not None:
                    best_final_local_ris = float(meta_recommended_local_ris)
            else:
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

                if best_final_snr is None and meta_meas_best_snr is not None:
                    best_final_snr = float(meta_meas_best_snr)

        # Derive RIS-referenced local angle when available
        if best_final_local_ris is None and best_final_abs is not None:
            ris_normal_for_meta = meta.get('ris_normal_deg')
            if ris_normal_for_meta is not None and best_final_abs is not None:
                offset = best_final_abs - ris_normal_for_meta
                best_final_local_ris = ((offset + 180.0) % 360.0) - 180.0

        # Get the metric-specific expected value at best angle
        best_final_metric = None
        metric_display_label = 'Expected SNR'
        metric_display_unit = 'dB'

        if not no_reliable_estimate and best_final_local is not None:
            best_final_metric = best_final_snr
            best_angle_idx = None
            if has_fine_phase and local_fine:
                for i, angle in enumerate(local_fine):
                    if abs(float(angle) - float(best_final_local)) < 0.01:
                        best_angle_idx = i
                        break
                if best_angle_idx is not None:
                    if metric.lower() in ['rssi', 'power'] and 'rssi_fine' in out:
                        best_final_metric = out['rssi_fine'][best_angle_idx]
                        metric_display_label = 'Expected RSSI'
                        metric_display_unit = 'dBm'
                    elif metric.lower() in ['csi', 'csi_quality'] and 'csi_quality_fine' in out:
                        best_final_metric = out['csi_quality_fine'][best_angle_idx]
                        metric_display_label = 'Expected CSI Quality'
                        metric_display_unit = 'bps/Hz'
            elif local_coarse:
                for i, angle in enumerate(local_coarse):
                    if abs(float(angle) - float(best_final_local)) < 0.01:
                        best_angle_idx = i
                        break
                if best_angle_idx is not None:
                    if metric.lower() in ['rssi', 'power'] and 'rssi_coarse' in out:
                        best_final_metric = out['rssi_coarse'][best_angle_idx]
                        metric_display_label = 'Expected RSSI'
                        metric_display_unit = 'dBm'
                    elif metric.lower() in ['csi', 'csi_quality'] and 'csi_quality_coarse' in out:
                        best_final_metric = out['csi_quality_coarse'][best_angle_idx]
                        metric_display_label = 'Expected CSI Quality'
                        metric_display_unit = 'bps/Hz'

        # Compute actual deflection angle from geometry (AP→RIS vs RIS→UE)
        # This should match the deflection angle reported by connect command
        deflection_angle_deg = None
        incident_azimuth_deg = None
        reflected_azimuth_deg = None
        try:
            # Quick geometry calculation to get the actual deflection angle
            import math
            ap_node = self.net.get(ap)
            ris_node = self.net.get(ris)
            ue_node = self.net.get(ue)

            if ap_node and ris_node and ue_node:
                ap_vec = ap_node.pos - ris_node.pos
                ue_vec = ue_node.pos - ris_node.pos
                theta_in_rad = math.atan2(ap_vec[1], ap_vec[0])
                theta_out_rad = math.atan2(ue_vec[1], ue_vec[0])

                angle_diff = theta_out_rad - theta_in_rad
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi

                deflection_angle_deg = math.degrees(angle_diff)
                incident_azimuth_deg = math.degrees(theta_in_rad)
                reflected_azimuth_deg = math.degrees(theta_out_rad)

                # Normalize angles to [0, 360) for cleaner display
                if incident_azimuth_deg < 0:
                    incident_azimuth_deg += 360
                if reflected_azimuth_deg < 0:
                    reflected_azimuth_deg += 360
        except Exception:
            pass  # If computation fails, skip displaying deflection angle

        print_func('RECOMMENDATION TO SEND TO RIS:')
        print_func('-'*70)

        if no_reliable_estimate or best_final_local is None or best_final_abs is None:
            loss_val = meta.get('hybrid_model_fit_loss')
            loss_threshold = meta.get('loss_threshold')
            print_func('No reliable steering estimate available from PRIME model-fit.')
            if loss_val is not None and loss_threshold is not None:
                print_func(f'Model-fit loss {loss_val:.4f} exceeded threshold {loss_threshold:.4f}.')
            suggestion = meta.get('diagnostic_suggestions') or "Increase sweep resolution or enable near-field ANM/CSI."
            print_func(f'Suggestion: {suggestion}')
            print_func()
        else:
            if best_final_local_ris is not None:
                print_func(
                    f'Steering Angle (Local Deflection): '
                    f'{best_final_local:.2f}° (AP), {best_final_local_ris:.2f}° (RIS)'
                )
            else:
                print_func(f'Steering Angle (Local Deflection): {best_final_local:.2f}°')
            if best_final_metric is not None:
                print_func(f'{metric_display_label:<34} {best_final_metric:.2f} {metric_display_unit}')
            else:
                print_func(f'{metric_display_label:<34} n/a {metric_display_unit}')
            print_func()

        return {
            'best_final_local': best_final_local,
            'best_final_local_ris': best_final_local_ris,
            'best_final_snr': best_final_snr,
            'best_final_abs': best_final_abs,
            'specular_angle': specular_angle,
            'algo_name_clean': algo_name_clean,
            'deflection_angle_deg': deflection_angle_deg
        }

    def create_sweep_record_and_link(self, ap, ris, ue, out, best_angles_info, fov, step, algo_name, use_waveform, modulation):
        """Create sweep record and update network active links"""
        best_final_local = best_angles_info['best_final_local']
        best_final_snr = best_angles_info['best_final_snr']
        best_final_abs = best_angles_info['best_final_abs']
        specular_angle = best_angles_info['specular_angle']
        algo_name_clean = best_angles_info['algo_name_clean']

        if best_final_local is None or best_final_abs is None:
            return  # Nothing reliable to store

        # Update/create active link with best result from sweep
        ap_node = self.net.get(ap)
        ris_node = self.net.get(ris)
        ue_node = self.net.get(ue)
        ap_key = ap_node.name if ap_node else ap
        ris_key = ris_node.name if ris_node else ris
        ue_key = ue_node.name if ue_node else ue

        link_key = f"{ap_key}→{ris_key}→{ue_key} (Connect Sweep - {algo_name_clean})"

        # Get the actual deflection angle from the best sweep result by calling connect
        # This ensures we have the correct deflection_angle_deg from phase metadata
        deflection_angle_deg = None
        incident_azimuth_deg = None
        reflected_azimuth_deg = None
        final_gain_dBi = None
        final_quant_loss_dB = None
        final_pwr_dBm = None
        try:
            final_result = self.net.connect(ap, ris, ue, beam_angle_deg=best_final_abs,
                                           compute_phases=True, store_in_active_links=False)
            deflection_angle_deg = final_result.get('deflection_angle_deg')
            incident_azimuth_deg = final_result.get('incident_azimuth_deg')
            reflected_azimuth_deg = final_result.get('reflected_azimuth_deg')
            final_gain_dBi = final_result.get('gain_dBi')
            final_quant_loss_dB = final_result.get('quant_loss_dB')
            final_pwr_dBm = final_result.get('pwr_dBm')

            # Normalize angles to [0, 360) for cleaner display
            if incident_azimuth_deg is not None and incident_azimuth_deg < 0:
                incident_azimuth_deg += 360
            if reflected_azimuth_deg is not None and reflected_azimuth_deg < 0:
                reflected_azimuth_deg += 360
        except Exception as e:
            pass  # Fallback: use best_final_local if connect fails

        # Retrieve phase data from RIS node if available
        phase_data = {}
        ris_node_ref = self.net.get(ris)
        if ris_node_ref and hasattr(ris_node_ref, 'current_phases'):
            phase_data['current_phases'] = ris_node_ref.current_phases.tolist() if hasattr(ris_node_ref.current_phases, 'tolist') else ris_node_ref.current_phases
            if hasattr(ris_node_ref, 'quantized_phases') and ris_node_ref.quantized_phases is not None:
                phase_data['quantized_phases'] = ris_node_ref.quantized_phases.tolist() if hasattr(ris_node_ref.quantized_phases, 'tolist') else ris_node_ref.quantized_phases
            if hasattr(ris_node_ref, 'phase_states') and ris_node_ref.phase_states is not None:
                phase_data['phase_states'] = ris_node_ref.phase_states.tolist() if hasattr(ris_node_ref.phase_states, 'tolist') else ris_node_ref.phase_states

        link_data = {
            'ap': ap_key,
            'ris': ris_key,
            'ue': ue_key,
            'snr_dB': float(best_final_snr),
            'pwr_dBm': float(final_pwr_dBm) if final_pwr_dBm is not None else (float(out.get('pwr_coarse', [0])[0]) if out.get('pwr_coarse') else -63.67),
            'beam_angle_local': float(deflection_angle_deg if deflection_angle_deg is not None else best_final_local),
            'beam_angle_absolute': float(best_final_abs),
            'ris_normal_angle': float(specular_angle),
            'gain_dBi': float(final_gain_dBi) if final_gain_dBi is not None else 0.0,
            'quant_loss_dB': float(final_quant_loss_dB) if final_quant_loss_dB is not None else 0.0,
            'source': 'connect_sweep',
            'algorithm': algo_name_clean,
            **phase_data
        }

        # Add deflection angle metadata if available
        if deflection_angle_deg is not None:
            link_data['deflection_angle_deg'] = float(deflection_angle_deg)
        if incident_azimuth_deg is not None:
            link_data['incident_azimuth_deg'] = float(incident_azimuth_deg)
        if reflected_azimuth_deg is not None:
            link_data['reflected_azimuth_deg'] = float(reflected_azimuth_deg)

        self.net.active_links[link_key] = link_data

        # Update RIS node's beam angle attributes
        if ris_node:
            ris_node.specular_angle_deg = float(specular_angle)
            ris_node.abs_beam_angle_deg = float(best_final_abs)
            # Use the computed deflection angle if available, otherwise fallback to best_final_local
            if deflection_angle_deg is not None:
                ris_node.local_beam_deflection_deg = float(deflection_angle_deg)
            else:
                ris_node.local_beam_deflection_deg = float(best_final_local)

        sweep_record = {
            'type': 'connect_sweep',
            'ap': ap_key,
            'ris': ris_key,
            'ue': ue_key,
            'captured_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            'parameters': {
                'fov_deg': float(fov),
                'step_deg': float(step),
                'algorithm': algo_name,
                'enable_feedback': True,
                'use_waveform': bool(use_waveform),
                'modulation': modulation if use_waveform else None
            },
            'best_angle_local': float(best_final_local),
            'best_angle_absolute': float(best_final_abs),
            'best_snr_dB': float(best_final_snr)
        }
        self.net.last_sweep_result = sanitize_for_json(sweep_record)
        return sweep_record
