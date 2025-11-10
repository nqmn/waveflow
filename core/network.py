"""
RIS Network manager with controller integration
"""
import numpy as np
from typing import Dict, List, Optional
from .nodes import AccessPoint, RIS, UE
from .physics import Physics
from .environment import Environment


class RISNetwork:
    """RIS Network manager with advanced pathfinding support"""

    def __init__(self):
        self.nodes = {}
        self.environment = Environment()
        self._controller = None
        self.impairments = {}
        self.active_links = {}  # Track active link connections

    def set_controller(self, controller):
        """Set network controller"""
        self._controller = controller

    # Node management
    def set_impairments(self, data: Dict):
        """Store global impairment settings (e.g., extra losses)"""
        self.impairments = data or {}

    def add_ap(self, name, x, y, z=0.0, power_dBm=20.0, freq=5.8e9,
               bandwidth_MHz=20.0, antenna_gain_dBi=3.0,
               noise_figure_dB=6.0):
        """Add access point"""
        self.nodes[name] = AccessPoint(
            name, x, y, z, power_dBm, freq, bandwidth_MHz,
            antenna_gain_dBi=antenna_gain_dBi,
            noise_figure_dB=noise_figure_dB
        )

    def add_ris(self, name, x, y, z=0.0, N=32, bits=2, freq=10e9,
                max_angle_deg=60, active_mode=False, amplifier_gain=1.0,
                element_efficiency=0.95, phase_error_std_deg=8.0,
                amp_std=0.15, coupling_enabled=True, K_db=10,
                noise_floor=-90.0):
        """Add RIS node"""
        self.nodes[name] = RIS(
            name, x, y, z, N, bits, None, freq, max_angle_deg,
            active_mode=active_mode, amplifier_gain=amplifier_gain,
            element_efficiency=element_efficiency,
            phase_error_std_deg=phase_error_std_deg,
            amp_std=amp_std, coupling_enabled=coupling_enabled,
            K_db=K_db, noise_floor=noise_floor
        )

    def add_ue(self, name, x, y, z=0.0, antenna_gain_dBi=3.0,
               noise_figure_dB=6.0):
        """Add user equipment"""
        self.nodes[name] = UE(name, x, y, z,
                              antenna_gain_dBi=antenna_gain_dBi,
                              noise_figure_dB=noise_figure_dB)

    def get(self, name):
        """Get node by name (case-insensitive)"""
        # First try exact match
        if name in self.nodes:
            return self.nodes[name]

        # Then try case-insensitive match
        name_lower = name.lower()
        for node_name, node in self.nodes.items():
            if node_name.lower() == name_lower:
                return node

        return None

    def list_nodes(self):
        """Print all nodes"""
        for k, v in self.nodes.items():
            print(f"{k:10s} {v}")

    def get_nodes_dict(self):
        """Get all nodes as dict for API"""
        return {name: node.to_dict() for name, node in self.nodes.items()}

    def update_node_position(self, name: str, x: float, y: float, z: float = 0.0):
        """Update node position

        Args:
            name: Node name
            x, y, z: New coordinates
        """
        node = self.get(name)
        if node:
            node.pos = np.array([float(x), float(y), float(z)])
            # Update RIS geometry if applicable
            if hasattr(node, 'update_geometry'):
                node.update_geometry()

    def remove_node(self, name: str):
        """Remove node from network"""
        if name in self.nodes:
            del self.nodes[name]
            # Remove associated links
            self.active_links = {
                link: info for link, info in self.active_links.items()
                if name not in [info['ap'], info['ris'], info['ue']]
            }

    def get_active_links(self):
        """Get all active links with their current status

        Returns:
            Dictionary of active links with metrics
        """
        return self.active_links

    def clear_links(self):
        """Clear all active link information"""
        self.active_links = {}

    # Basic connectivity (legacy method, kept for compatibility)
    def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None, compute_phases=True,
                bandwidth_MHz=None, seed=None, enable_feedback=False, max_feedback_iterations=10):
        """Compute cascaded AP->RIS->UE link with optional automatic CSI feedback and adaptation

        Args:
            ap_name: AP node name
            ris_name: RIS node name
            ue_name: UE node name
            beam_angle_deg: Beam steering angle (None for auto)
            compute_phases: Whether to compute and quantize RIS phases
            bandwidth_MHz: Signal bandwidth in MHz for noise floor calculation
            seed: Random seed for reproducibility (None = use random fading each call)
            enable_feedback: If True, UE sends CSI feedback to AP for closed-loop adaptation
            max_feedback_iterations: Maximum iterations for feedback loop (default 10)

        Returns:
            Dict with snr_dB, pwr_dBm, gain_dBi, quant_loss_dB, and feedback_info if enabled
        """
        # Set seed for reproducibility if provided
        if seed is not None:
            np.random.seed(seed)

        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)

        if ap is None or ris is None or ue is None:
            missing = []
            if ap is None:
                missing.append(f"AP '{ap_name}'")
            if ris is None:
                missing.append(f"RIS '{ris_name}'")
            if ue is None:
                missing.append(f"UE '{ue_name}'")
            available = ", ".join(self.nodes.keys()) if self.nodes else "none"
            raise ValueError(f"Invalid node name(s): {', '.join(missing)}. Available nodes: {available}")

        # Auto-compute beam angle if not provided
        if beam_angle_deg is None:
            vec_tgt = ue.pos - ris.pos
            beam_angle_deg = np.degrees(np.arctan2(vec_tgt[1], vec_tgt[0]))

        # Compute RIS phase configuration
        if compute_phases:
            ris.compute_phases(ap.pos, ue.pos)
            ris.quantize_phases()

        # Calculate link SNR using physics models
        if bandwidth_MHz is None:
            bandwidth_MHz = getattr(ap, 'bandwidth_MHz', 100.0)

        # Align RIS frequency with AP if not manually overridden
        if hasattr(ris, 'freq'):
            ris.freq = ap.freq

        # AP -> RIS
        d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
        pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)

        # RIS -> UE (with beam steering)
        d_ris_ue = np.linalg.norm(ue.pos - ris.pos)
        pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)

        # RIS gain (total elements = N × N)
        N_total = ris.N * ris.N
        target_angle = np.degrees(np.arctan2(ue.pos[1] - ris.pos[1], ue.pos[0] - ris.pos[0]))

        # Enforce max_angle_deg constraint - clamp target angle to within RIS capability
        max_angle = getattr(ris, 'max_angle_deg', 60.0)
        if abs(target_angle) > max_angle:
            # Clamp to the nearest valid angle within [-max_angle, +max_angle]
            if target_angle > max_angle:
                target_angle = max_angle
            elif target_angle < -max_angle:
                target_angle = -max_angle

        angle_loss = Physics.angle_loss_dB(beam_angle_deg, target_angle)
        gain_dBi = Physics.array_gain_dBi(N_total, ris.amplifier_gain, angle_loss_dB=angle_loss)

        # Quantization loss (negative dB = loss)
        quant_loss_dB = Physics.quantization_loss_dB(
            ris.bits,
            element_efficiency=getattr(ris, 'element_efficiency', 0.95)
        )

        # AP and UE antenna gains (default 3 dBi each for omnidirectional)
        ap_antenna_gain_dBi = getattr(ap, 'antenna_gain_dBi', 3.0)
        ue_antenna_gain_dBi = getattr(ue, 'antenna_gain_dBi', 3.0)
        noise_figure_dB = getattr(ue, 'noise_figure_dB', 6.0)

        # Received power calculation (coherent link)
        # Pr = Pt + G_AP + G_UE + G_RIS - PL_AP_RIS - PL_RIS_UE - |quant_loss|
        # NOTE: quant_loss_dB is NEGATIVE (e.g., -1.67 dB), so we subtract it (subtract negative = add less)
        extra_loss = float(self.impairments.get('extra_path_loss_dB', 0.0))
        pwr_dBm = (ap.power_dBm + ap_antenna_gain_dBi + ue_antenna_gain_dBi + gain_dBi -
                   pl_ap_ris - pl_ris_ue - extra_loss + quant_loss_dB)

        # SNR calculation using physics module (100 MHz default, 6 dB NF)
        # This properly accounts for noise floor = -174 + 10*log10(BW) + NF
        total_loss_dB = pl_ap_ris + pl_ris_ue + extra_loss
        total_gain_dBi = (gain_dBi + quant_loss_dB +
                          ap_antenna_gain_dBi + ue_antenna_gain_dBi)

        snr_dB = Physics.compute_snr_dB(
            tx_power_dBm=ap.power_dBm,
            total_loss_dB=total_loss_dB,
            gain_dBi=total_gain_dBi,
            bandwidth_MHz=bandwidth_MHz,
            noise_figure_dB=noise_figure_dB
        )

        # Apply fading only if not in deterministic mode (seed not set)
        # Fading reduces SNR when coefficient < 1.0
        if seed is None:
            fading_coeff = Physics.rician_fading(ris.K_db)
            if fading_coeff < 1.0:
                snr_dB += 20 * np.log10(fading_coeff)  # Reduces SNR (negative dB)

        gain_linear = 10 ** (gain_dBi / 10)

        result = {
            "snr_dB": float(snr_dB),
            "pwr_dBm": float(pwr_dBm),
            "rssi_dBm": float(pwr_dBm),
            "gain_linear": float(gain_linear),
            "gain_dBi": float(gain_dBi),
            "quant_loss_dB": float(quant_loss_dB),
            "beam_angle": float(beam_angle_deg),
            "evm_percent": float(Physics.snr_to_evm(snr_dB))
        }

        # Automatic CSI feedback and closed-loop adaptation
        if enable_feedback:
            result["feedback_info"] = self._run_adaptive_feedback_loop(
                ap_name, ris_name, ue_name, snr_dB, max_feedback_iterations,
                bandwidth_MHz, seed
            )

        # Track active link
        link_key = f"{ap_name}→{ris_name}→{ue_name}"
        self.active_links[link_key] = {
            'ap': ap_name,
            'ris': ris_name,
            'ue': ue_name,
            'snr_dB': result['snr_dB'],
            'pwr_dBm': result['pwr_dBm'],
            'beam_angle': beam_angle_deg,
            'gain_dBi': result.get('gain_dBi', 0.0),
            'quant_loss_dB': result.get('quant_loss_dB', 0.0)
        }

        return result

    def _run_adaptive_feedback_loop(self, ap_name, ris_name, ue_name, initial_snr_dB,
                                    max_iterations, bandwidth_MHz, seed):
        """Run closed-loop feedback between UE and AP for adaptation

        Mimics real hardware: UE measures SNR and sends feedback to AP,
        AP adapts power/modulation, then transmits again.
        """
        ap = self.get(ap_name)
        ue = self.get(ue_name)

        if not ap or not ue:
            return {"error": "Invalid AP or UE"}

        # Enable adaptive features (respect explicit user overrides)
        was_power_enabled = ap.power_control_enabled
        was_rate_enabled = ap.rate_adaptation_enabled
        power_override = getattr(ap, 'power_control_override_active', lambda: True)()
        rate_override = getattr(ap, 'rate_adaptation_override_active', lambda: True)()

        auto_enabled_power = False
        auto_enabled_rate = False

        if not was_power_enabled and not power_override:
            ap.set_power_control_enabled(True, user_override=None)
            auto_enabled_power = True

        if not was_rate_enabled and not rate_override:
            ap.set_rate_adaptation_enabled(True, user_override=None)
            auto_enabled_rate = True

        feedback_iterations = []

        for iteration in range(max_iterations):
            # Iteration 0 uses initial SNR from first transmission
            if iteration == 0:
                snr_measured = initial_snr_dB
            else:
                # Re-compute link with adapted power
                link_result = self.connect(
                    ap_name, ris_name, ue_name,
                    compute_phases=True,
                    bandwidth_MHz=bandwidth_MHz,
                    seed=seed,
                    enable_feedback=False
                )
                snr_measured = link_result["snr_dB"]

            # UE measures SNR and generates feedback
            ue.estimate_snr_from_waveform(
                rx_signal=np.random.randn(1000) + 1j * np.random.randn(1000),
                noise_power=0.01
            )
            ue.snr_measurement_dB = snr_measured

            csi_feedback = ue.generate_csi_feedback(snr_dB=snr_measured)

            # AP receives feedback and adapts
            control_action = ap.process_csi_feedback(csi_feedback)

            snr_error = abs(ap.target_snr_dB - snr_measured)
            converged = snr_error < 1.0

            iteration_info = {
                "iteration": iteration,
                "measured_snr_dB": snr_measured,
                "ap_power_dBm": ap.power_dBm,
                "ap_mcs": ap.get_current_mcs()["name"],
                "snr_error_dB": snr_error,
                "converged": converged,
                "control_action": control_action
            }

            feedback_iterations.append(iteration_info)

            if converged:
                break

        # Restore original settings only if we auto-enabled them
        if auto_enabled_power:
            ap.set_power_control_enabled(was_power_enabled, user_override=None)

        if auto_enabled_rate:
            ap.set_rate_adaptation_enabled(was_rate_enabled, user_override=None)

        # Determine convergence: SNR error < 1 dB threshold (power/rate are adapted)
        final_iteration = feedback_iterations[-1] if feedback_iterations else None

        return {
            "iterations": feedback_iterations,
            "final_iteration": final_iteration,
            "converged": final_iteration["converged"] if final_iteration else False,
            "convergence_definition": "SNR error < 1.0 dB from target (power and rate adapted)",
            "num_iterations": len(feedback_iterations),
            "final_power_dBm": ap.power_dBm,
            "final_mcs": ap.get_current_mcs()["name"],
            "final_snr_dB": final_iteration["measured_snr_dB"] if final_iteration else None
        }

    def direct_link(self, ap_name: str, ue_name: str,
                    bandwidth_MHz: Optional[float] = None,
                    apply_extra_loss: bool = True,
                    apply_blockage: bool = True) -> Dict:
        """Compute direct AP→UE link budget without RIS assistance.

        Args:
            ap_name: Access point name
            ue_name: UE name
            bandwidth_MHz: Optional bandwidth override
            apply_extra_loss: Apply global extra_path_loss_dB impairment
            apply_blockage: Apply direct_blockage_dB impairment

        Returns:
            Dict with distance, losses, SNR, and RSSI.
        """
        ap = self.get(ap_name)
        ue = self.get(ue_name)

        if ap is None or ue is None:
            raise ValueError("Invalid node name in direct_link")

        distance = float(np.linalg.norm(ue.pos - ap.pos))
        path_loss_dB = float(Physics.path_loss_dB(distance, ap.freq))

        extra_loss = float(self.impairments.get('extra_path_loss_dB', 0.0)) if apply_extra_loss else 0.0
        blockage_loss = 0.0
        if apply_blockage:
            blockage_loss = float(self.impairments.get('direct_blockage_dB', extra_loss))

        total_loss_dB = path_loss_dB + extra_loss + blockage_loss

        ap_gain = float(getattr(ap, 'antenna_gain_dBi', 3.0))
        ue_gain = float(getattr(ue, 'antenna_gain_dBi', 3.0))
        total_gain_dBi = ap_gain + ue_gain

        if bandwidth_MHz is None:
            bandwidth_MHz = float(getattr(ap, 'bandwidth_MHz', 20.0))

        noise_figure_dB = float(getattr(ue, 'noise_figure_dB', 6.0))

        rx_power_dBm = ap.power_dBm + total_gain_dBi - total_loss_dB
        snr_dB = Physics.compute_snr_dB(
            tx_power_dBm=ap.power_dBm,
            total_loss_dB=total_loss_dB,
            gain_dBi=total_gain_dBi,
            bandwidth_MHz=bandwidth_MHz,
            noise_figure_dB=noise_figure_dB
        )

        return {
            "distance_m": distance,
            "path_loss_dB": path_loss_dB,
            "extra_loss_dB": extra_loss if apply_extra_loss else 0.0,
            "blockage_loss_dB": blockage_loss if apply_blockage else 0.0,
            "total_loss_dB": total_loss_dB,
            "rx_power_dBm": float(rx_power_dBm),
            "rssi_dBm": float(rx_power_dBm),
            "snr_dB": float(snr_dB),
            "gain_dBi": total_gain_dBi
        }

    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, fine_span=5, fine_res=1, seed=0):
        """Coarse and fine beam sweep with deterministic SNR measurement

        Args:
            ap_name: AP name
            ris_name: RIS name
            ue_name: UE name
            fov: Field of view (degrees)
            step: Coarse step size (degrees)
            fine_span: Fine search span (degrees)
            fine_res: Fine resolution (degrees)
            seed: Random seed for reproducible fading (0 = reproducible, None = random)

        Returns:
            Dict with sweep results
        """
        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        vec = ue.pos - ris.pos
        base_dir = np.degrees(np.arctan2(vec[1], vec[0]))

        # Coarse sweep
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = base_dir + local_coarse

        snr_coarse = []
        pwr_coarse = []

        # Use deterministic seed for consistent SNR measurements across sweep
        for abs_a in abs_angles:
            res = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a, seed=seed)
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        # Find best coarse angle
        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # Fine sweep
        local_fine = np.arange(best_local - fine_span, best_local + fine_span + fine_res, fine_res)
        abs_angles_fine = base_dir + local_fine
        snr_fine = []

        for abs_a in abs_angles_fine:
            # Use same seed for consistent comparison
            r = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a, seed=seed)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        return {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': np.array(snr_coarse).tolist(),
            'pwr_coarse': np.array(pwr_coarse).tolist(),
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine))
        }

    # Advanced pathfinding (uses controller)
    def find_paths(self, ap_name: str, ue_name: str, algorithm: str = 'dijkstra') -> List[Dict]:
        """Find all paths using controller

        Args:
            ap_name: AP name
            ue_name: UE name
            algorithm: Pathfinding algorithm

        Returns:
            List of path dicts
        """
        if self._controller:
            return self._controller.find_all_paths(ap_name, ue_name, algorithm)
        return []

    # Environment management
    def add_wall(self, start, end, attenuation_dB=20.0, name=None):
        """Add wall to environment"""
        return self.environment.add_wall(start, end, attenuation_dB, name)

    def remove_wall(self, name):
        """Remove wall"""
        self.environment.remove_wall(name)

    def clear_walls(self):
        """Clear all walls"""
        self.environment.clear_walls()

    def get_environment_dict(self):
        """Get environment as dict"""
        return self.environment.to_dict()
