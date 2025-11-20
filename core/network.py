"""
RIS Network manager with controller integration
"""
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from .nodes import AccessPoint, RIS, UE
from .physics import Physics, C
from .environment import Environment
from .angle_utils import (
    normalize_angle_to_pm180,
    compute_offset_from_normal,
    is_within_fov,
    clamp_offset_to_fov,
    compute_absolute_angle_from_offset,
    compute_optimal_ris_normal
)
from .feedback_channel import FeedbackChannelManager, FeedbackChannel
from .snr_messaging import SNRMessagingSystem
from controller.ris_phase.phase_steering import PhaseSteeringEngine
from utils.rssi import compute_rssi_dBm


class RISNetwork:
    """RIS Network manager with advanced pathfinding support"""

    def __init__(self, enable_messaging=True, latency_ms=5.0, jitter_ms=1.0, use_get_snr=False):
        self.nodes = {}
        self.environment = Environment()
        self._controller = None
        self.impairments = {}
        self.active_links = {}  # Track active link connections
        self.last_connect_result = None
        self.last_sweep_result = None
        self.feedback_channels = FeedbackChannelManager()  # Option 3: Feedback channel system

        # Real-world messaging system (mimics control channel communication)
        if enable_messaging:
            self.snr_messaging = SNRMessagingSystem(self, latency_ms=latency_ms, jitter_ms=jitter_ms)
        else:
            self.snr_messaging = None

        # Global flag: when True, all operations use get_snr() instead of computing SNR
        # This is now the DEFAULT behavior - all commands query SNR from UE via messaging
        self.use_get_snr_global = use_get_snr

        # Angular tolerance (deg) to consider UE present in a beam and SNR floor when absent
        self.presence_detection_tolerance_deg = 5.0
        self.no_ue_snr_floor_dB = 0.0

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
                max_angle_deg=60, normal_angle_deg=0.0, active_mode=False, amplifier_gain=1.0,
                element_efficiency=0.95, phase_error_std_deg=8.0,
                amp_std=0.15, coupling_enabled=True, K_db=10,
                noise_floor=-90.0):
        """Add RIS node"""
        self.nodes[name] = RIS(
            name, x, y, z, N, bits, None, freq, max_angle_deg, normal_angle_deg,
            active_mode=active_mode, amplifier_gain=amplifier_gain,
            element_efficiency=element_efficiency,
            phase_error_std_deg=phase_error_std_deg,
            amp_std=amp_std, coupling_enabled=coupling_enabled,
            K_db=K_db, noise_floor=noise_floor
        )
        return self.nodes[name]

    def add_ue(self, name, x, y, z=0.0, antenna_gain_dBi=3.0,
               noise_figure_dB=6.0, max_angle_deg=180.0, normal_angle_deg=0.0):
        """Add user equipment

        Args:
            name: UE node name
            x, y, z: Position coordinates (z=0 for 2D)
            antenna_gain_dBi: Antenna gain in dBi (default 3.0)
            noise_figure_dB: Noise figure in dB (default 6.0)
            max_angle_deg: Antenna FOV in degrees (±angle from normal, default 180°)
            normal_angle_deg: Antenna boresight direction in degrees (default 0°)
        """
        self.nodes[name] = UE(name, x, y, z,
                              antenna_gain_dBi=antenna_gain_dBi,
                              noise_figure_dB=noise_figure_dB,
                              max_angle_deg=max_angle_deg,
                              normal_angle_deg=normal_angle_deg)

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

    # Feedback Channel Management (Option 3: UE → Controller SNR feedback)
    def create_feedback_channel(self, ue_name: str, ris_name: str,
                               history_size: int = 100) -> FeedbackChannel:
        """
        Create a feedback channel from UE to RIS controller.

        Args:
            ue_name: Source UE node name
            ris_name: Destination RIS node name
            history_size: Maximum CSI reports to store (default 100)

        Returns:
            FeedbackChannel instance
        """
        return self.feedback_channels.create_channel(ue_name, ris_name, history_size)

    def get_feedback_channel(self, ue_name: str, ris_name: str) -> Optional[FeedbackChannel]:
        """
        Get an existing feedback channel.

        Args:
            ue_name: Source UE name
            ris_name: Destination RIS name

        Returns:
            FeedbackChannel or None if not found
        """
        return self.feedback_channels.get_channel(ue_name, ris_name)

    def list_feedback_channels(self) -> Dict[str, Dict]:
        """
        Get all feedback channels with statistics.

        Returns:
            Dictionary of channel_key -> statistics
        """
        return self.feedback_channels.list_channels()

    def get_feedback_statistics(self) -> Dict:
        """
        Get network-wide feedback statistics.

        Returns:
            Dictionary with aggregated feedback stats
        """
        return self.feedback_channels.get_network_statistics()

    # Basic connectivity method
    def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None, compute_phases=True,
                bandwidth_MHz=None, seed=None, enable_feedback=False, max_feedback_iterations=10,
                use_isolated_copy=True, store_in_active_links=True, use_get_snr=True,
                tapering='uniform', fixed_ris_normal=None):
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
            use_isolated_copy: If True (default), use cloned nodes to prevent state pollution.
                              If False, modify original nodes (for persistent adaptation).
            store_in_active_links: If False, skip storing result in active_links (for intermediate sweep measurements).
                                  Default: True
            use_get_snr: If True (DEFAULT), retrieve SNR via messaging system instead of computing.
                        This queries UE for measured SNR through control channel (realistic behavior).
                        If False, compute SNR using physics models.
            tapering: Window function for side lobe suppression ('uniform', 'hamming', 'hann', 'blackman').
                     Default: 'uniform' (no tapering).
            fixed_ris_normal: If provided, use this RIS normal angle instead of auto-calculating.
                             For beam sweep testing to keep RIS normal consistent. Default: None

        Returns:
            Dict with snr_dB, pwr_dBm, gain_dBi, quant_loss_dB, and feedback_info if enabled
        """
        # Set seed for reproducibility if provided
        if seed is not None:
            np.random.seed(seed)

        ap_node = self.get(ap_name)
        ris_node = self.get(ris_name)
        ue_node = self.get(ue_name)

        if ap_node is None or ris_node is None or ue_node is None:
            missing = []
            if ap_node is None:
                missing.append(f"AP '{ap_name}'")
            if ris_node is None:
                missing.append(f"RIS '{ris_name}'")
            if ue_node is None:
                missing.append(f"UE '{ue_name}'")
            available = ", ".join(self.nodes.keys()) if self.nodes else "none"
            raise ValueError(f"Invalid node name(s): {', '.join(missing)}. Available nodes: {available}")

        # Use isolated clones by default to prevent cross-node state pollution
        if use_isolated_copy:
            ap = ap_node.clone()
            ris = ris_node.clone()
            ue = ue_node.clone()
        else:
            ap, ris, ue = ap_node, ris_node, ue_node

        # Apply tapering if requested (calculate weights)
        if tapering != 'uniform':
            # Calculate weights using PhaseSteeringEngine
            # Assuming square array for now (N x N)
            weights_2d = PhaseSteeringEngine.apply_tapering(ris.N, ris.N, window=tapering)
            ris.element_weights = weights_2d.flatten()
        else:
            # Reset to uniform if explicitly requested or default
            ris.element_weights = np.ones(ris.N * ris.N)

        # Auto-compute beam angle if not provided
        if beam_angle_deg is None:
            # Use the absolute angle from RIS to UE as the beam target direction
            # This will be converted to local deflection later via compute_offset_from_normal()
            vec_tgt = ue.pos - ris.pos
            beam_angle_deg = np.degrees(np.arctan2(vec_tgt[1], vec_tgt[0]))

        # Canonical node names for metadata/storage
        ap_key = ap.name if ap else ap_name
        ris_key = ris.name if ris else ris_name
        ue_key = ue.name if ue else ue_name

        # Compute RIS phase configuration
        phase_metadata = {}
        if compute_phases:
            # FIX FOR SNR DISCREPANCY: Use linear steering phases instead of path-optimized phases
            # The paper uses simple beam steering, not complex path-optimized phases.
            # Linear steering produces phases compatible with array factor calculation.
            from controller.ris_phase.phase_steering import PhaseSteeringEngine

            wavelength = C / ris.freq
            # Use linear steering phases for proper array gain at beam direction
            phases_linear = PhaseSteeringEngine.linear_steering_phases(
                beam_angle_deg=beam_angle_deg,
                ris_position=ris.pos,
                wavelength=wavelength,
                ris_array_size=ris.N,
                element_positions=getattr(ris, "element_positions", None),
            )
            ris.current_phases = phases_linear
            ris.quantize_phases()

            # Compute deflection angle for metadata (for consistency with formula doc)
            # Extract 2D projections for deflection calculation
            ap_2d = ap.pos[:2]
            ris_2d = ris.pos[:2]
            ue_2d = ue.pos[:2]

            # Calculate incident and reflected azimuth angles
            theta_in_rad = np.arctan2(ap_2d[1] - ris_2d[1], ap_2d[0] - ris_2d[0])
            theta_out_rad = np.arctan2(ue_2d[1] - ris_2d[1], ue_2d[0] - ris_2d[0])

            # Calculate angle difference and deflection
            angle_diff = theta_out_rad - theta_in_rad
            while angle_diff > np.pi:
                angle_diff -= 2 * np.pi
            while angle_diff < -np.pi:
                angle_diff += 2 * np.pi

            deflection_angle_deg = abs(np.degrees(angle_diff))
            deflection_angle_rad = abs(angle_diff)

            # Store metadata for result dictionary
            phase_metadata = {
                'deflection_angle_deg': deflection_angle_deg,
                'deflection_angle_clamped_deg': deflection_angle_deg,  # Not clamped in this path
                'fov_clamped': False,
                'incident_azimuth_deg': np.degrees(theta_in_rad),
                'reflected_azimuth_deg': np.degrees(theta_out_rad),
                'angle_diff_deg': np.degrees(angle_diff),
            }

            # Store phase metadata on RIS node so it can be picked up later
            ris.phase_metadata = phase_metadata

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

        # Determine RIS normal angle
        max_angle = getattr(ris, 'max_angle_deg', 60.0)
        if fixed_ris_normal is not None:
            # Use provided fixed RIS normal for consistent sweep measurements
            ris_normal = fixed_ris_normal
        else:
            ris_normal = getattr(ris, 'normal_angle_deg', 0.0)

        # Compute angles from RIS perspective for FOV checking
        ap_to_ris_vec = ap.pos - ris.pos  # Vector from RIS toward AP
        ap_angle = np.degrees(np.arctan2(ap_to_ris_vec[1], ap_to_ris_vec[0]))

        ue_to_ris_vec = ue.pos - ris.pos  # Vector from RIS toward UE
        ue_angle = np.degrees(np.arctan2(ue_to_ris_vec[1], ue_to_ris_vec[0]))

        # Check if RIS's current normal can serve both AP and UE
        ap_offset = compute_offset_from_normal(ap_angle, ris_normal)
        ue_offset = compute_offset_from_normal(target_angle, ris_normal)

        # If current RIS normal doesn't work for both AP and UE, calculate optimal bisector
        if not is_within_fov(ap_offset, max_angle) or not is_within_fov(ue_offset, max_angle):
            # RIS normal needs adjustment - calculate optimal bisector
            ris_normal = compute_optimal_ris_normal(ap_angle, ue_angle)

            # Recalculate offsets with new normal
            ap_offset = compute_offset_from_normal(ap_angle, ris_normal)
            ue_offset = compute_offset_from_normal(target_angle, ris_normal)

        # Final validation - AP must be in FOV
        if not is_within_fov(ap_offset, max_angle):
            raise ValueError(
                f"AP outside RIS FOV: AP is at {ap_angle:.2f}° (absolute), "
                f"{ap_offset:.2f}° relative to RIS normal of {ris_normal:.2f}°, "
                f"but RIS FOV is ±{max_angle}°. "
                f"RIS cannot serve AP from this direction."
            )

        # Final validation - UE must be in FOV
        if not is_within_fov(ue_offset, max_angle):
            raise ValueError(
                f"UE outside RIS FOV: UE is at {target_angle:.2f}° (absolute), "
                f"{ue_offset:.2f}° relative to RIS normal of {ris_normal:.2f}°, "
                f"but RIS FOV is ±{max_angle}°. "
                f"RIS cannot serve UE from this direction."
            )

        # Clamp local deflection to RIS FOV constraint (native RIS capability)
        # Calculate the ideal local deflection needed to reach the target
        ideal_local_deflection = compute_offset_from_normal(beam_angle_deg, ris_normal)
        beam_angle_requested_deg = float(beam_angle_deg)
        # Clamp to RIS maximum steering angle
        clamped_local_deflection = clamp_offset_to_fov(ideal_local_deflection, max_angle)

        # If clamping occurred, the actual beam angle changes
        if abs(clamped_local_deflection - ideal_local_deflection) > 0.01:  # Allow small numerical error
            # RIS steers to the clamped position
            beam_angle_deg = compute_absolute_angle_from_offset(ris_normal, clamped_local_deflection)
            # Note: We don't raise an error; RIS simply steers to nearest reachable position

        # Track whether a physical UE is illuminated by this beam
        beam_hits_ue = True

        # Check UE can receive from RIS (based on FINAL beam angle after clamping)
        # This validation uses the offset angle, not raw RIS direction
        ue_max_angle = getattr(ue, 'max_angle_deg', 180.0)  # Default: 180° FOV (nearly omnidirectional)
        ue_normal = getattr(ue, 'normal_angle_deg', 0.0)

        # From UE's perspective, the final beam comes from angle beam_angle_deg
        # We need to check if UE can receive from that direction
        beam_offset_to_ue = compute_offset_from_normal(beam_angle_requested_deg, ue_normal)

        if not is_within_fov(beam_offset_to_ue, ue_max_angle):
            beam_hits_ue = False

        # NOTE: With array factor integration, beam_hits_ue is now computed implicitly
        # via Physics.compute_array_factor(). The array factor naturally models
        # main lobe (~0 dB at steering direction) and sidelobes (~-10 to -30 dB).
        # This provides physically-accurate SNR across all angles without artificial cutoff.
        #
        # The old binary beam_hits_ue check is retained here for backward compatibility
        # and logging, but the SNR calculation in the array factor section replaces
        # the hard floor logic that was previously applied below.
        angle_to_ue = target_angle  # Where the UE actually is
        angular_distance_to_ue = abs((beam_angle_requested_deg - angle_to_ue + 180) % 360 - 180)  # Shortest angle

        presence_tol = getattr(self, 'presence_detection_tolerance_deg', 5.0)
        if angular_distance_to_ue > presence_tol:
            beam_hits_ue = False

        angle_loss = Physics.angle_loss_dB(beam_angle_deg, target_angle)
        # Track beam metadata on RIS for visualization
        try:
            ris.specular_angle_deg = float(target_angle)
            ris.abs_beam_angle_deg = float(beam_angle_deg)
            # Use the deflection angle from phase metadata if available, otherwise compute it
            if phase_metadata and 'deflection_angle_deg' in phase_metadata:
                ris.local_beam_deflection_deg = float(phase_metadata['deflection_angle_deg'])
            else:
                # Fallback: compute as the difference between incident and reflected angles
                ris.local_beam_deflection_deg = float(abs(beam_angle_deg - target_angle) if beam_angle_deg is not None else 0.0)
        except Exception:
            pass
        # Calculate max array gain (at peak)
        # We pass angle_loss_dB=0 here because we will apply the full directional loss
        # via the Array Factor (af_dB) later.
        # If we passed angle_loss here, we would double-count the penalty.
        gain_dBi = Physics.array_gain_dBi(N_total, ris.amplifier_gain, angle_loss_dB=0.0, frequency=ris.freq)

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
        extra_loss = 0.0
        impairments = self.impairments or {}
        if 'extra_path_loss_dB_ris' in impairments:
            extra_loss = float(impairments.get('extra_path_loss_dB_ris', 0.0))
        elif impairments.get('apply_extra_path_loss_to_ris', False):
            extra_loss = float(impairments.get('extra_path_loss_dB', 0.0))
        pwr_dBm = (ap.power_dBm + ap_antenna_gain_dBi + ue_antenna_gain_dBi + gain_dBi -
                   pl_ap_ris - pl_ris_ue - extra_loss + quant_loss_dB)

        # SNR calculation using physics module (100 MHz default, 6 dB NF)
        # This properly accounts for noise floor = -174 + 10*log10(BW) + NF
        total_loss_dB = pl_ap_ris + pl_ris_ue + extra_loss
        total_gain_dBi = (gain_dBi + quant_loss_dB +
                          ap_antenna_gain_dBi + ue_antenna_gain_dBi)


        # Always compute deterministic SNR first
        snr_computed_dB = Physics.compute_snr_dB(
            tx_power_dBm=ap.power_dBm,
            total_loss_dB=total_loss_dB,
            gain_dBi=total_gain_dBi,
            bandwidth_MHz=bandwidth_MHz,
            noise_figure_dB=noise_figure_dB
        )

        if seed is None:
            fading_coeff = Physics.rician_fading(ris.K_db)
            if fading_coeff < 1.0:
                snr_computed_dB += 20 * np.log10(fading_coeff)

        snr_dB = snr_computed_dB

        # ARRAY FACTOR INTEGRATION: Replace beam_hits_ue cutoff with physics-based array factor
        # Array factor naturally models sidelobe response without artificial binary cutoff
        if ris.current_phases is not None and len(ris.current_phases) > 0:
            # Compute array factor for actual beam position
            # This determines gain reduction due to sidelobe pattern
            af_dB = Physics.compute_array_factor(
                phases=ris.current_phases,
                element_positions=ris.element_positions,
                target_angle_deg=target_angle,  # Evaluate AF at UE location, not beam direction
                frequency=ris.freq,
                weights=getattr(ris, 'element_weights', None),
                ris_position=ris.pos,
                ap_position=ap.pos if ap is not None else None
            )

            # Apply array factor to gain
            # af_dB is normalized so peak (steering direction) = 0 dB
            # Sidelobes naturally show -10 to -30 dB depending on distance from steering dir
            # Apply array factor to gain
            # af_dB is normalized so peak (steering direction) = 0 dB
            # Sidelobes naturally show -10 to -30 dB depending on distance from steering dir
            # Since we set angle_loss_dB=0 in array_gain_dBi, this af_dB provides the
            # sole directional penalty, avoiding double-counting.
            total_gain_dBi_with_af = total_gain_dBi + af_dB

            # Recompute SNR with array factor included
            snr_computed_dB_with_af = Physics.compute_snr_dB(
                tx_power_dBm=ap.power_dBm,
                total_loss_dB=total_loss_dB,
                gain_dBi=total_gain_dBi_with_af,
                bandwidth_MHz=bandwidth_MHz,
                noise_figure_dB=noise_figure_dB
            )

            # Apply fading if not deterministic
            if seed is None:
                fading_coeff = Physics.rician_fading(ris.K_db)
                if fading_coeff < 1.0:
                    snr_computed_dB_with_af += 20 * np.log10(fading_coeff)

            snr_dB = snr_computed_dB_with_af
            gain_dBi = total_gain_dBi_with_af
        else:
            # No current phases available - use computed value as-is
            # This handles initialization before phase computation
            pass

        gain_linear = 10 ** (gain_dBi / 10)

        # Add phase data to result if computed
        phase_data = {}
        if compute_phases and ris.current_phases is not None:
            phase_data = {
                "current_phases": ris.current_phases.tolist() if hasattr(ris.current_phases, 'tolist') else ris.current_phases,
                "quantized_phases": ris.quantized_phases.tolist() if ris.quantized_phases is not None and hasattr(ris.quantized_phases, 'tolist') else ris.quantized_phases,
                "phase_states": ris.phase_states.tolist() if ris.phase_states is not None and hasattr(ris.phase_states, 'tolist') else ris.phase_states,
                "phase_grid": ris.get_phase_grid() if hasattr(ris, 'get_phase_grid') else None
            }

            # Add phase computation metadata (deflection angle, azimuths, FOV clamping) if available
            if hasattr(ris, 'phase_metadata') and ris.phase_metadata is not None:
                phase_data.update({
                    "deflection_angle_deg": float(ris.phase_metadata.get('deflection_angle_deg', 0)),
                    "deflection_angle_clamped_deg": float(ris.phase_metadata.get('deflection_angle_clamped_deg', 0)),
                    "fov_clamped": bool(ris.phase_metadata.get('fov_clamped', False)),
                    "incident_azimuth_deg": float(ris.phase_metadata.get('incident_azimuth_deg', 0)),
                    "reflected_azimuth_deg": float(ris.phase_metadata.get('reflected_azimuth_deg', 0)),
                    "angle_diff_deg": float(ris.phase_metadata.get('angle_diff_deg', 0)),
                    "source_height_m": float(ris.phase_metadata.get('source_height_m', 0)),
                })

            # Persist phase configuration on canonical RIS node for downstream tools (e.g., ris_panel shell)
            if ris_node is not None:
                ris_node.current_phases = np.array(ris.current_phases, copy=True)
                ris_node.quantized_phases = (np.array(ris.quantized_phases, copy=True)
                                             if ris.quantized_phases is not None else None)
                ris_node.phase_states = (np.array(ris.phase_states, copy=True)
                                         if ris.phase_states is not None else None)
                ris_node.current_beam_angle = float(beam_angle_deg) if beam_angle_deg is not None else None
                ris_node.specular_angle_deg = getattr(ris, 'specular_angle_deg', None)
                ris_node.abs_beam_angle_deg = getattr(ris, 'abs_beam_angle_deg', None)
                ris_node.local_beam_deflection_deg = getattr(ris, 'local_beam_deflection_deg', None)
                # Also persist phase metadata
                if hasattr(ris, 'phase_metadata') and ris.phase_metadata is not None:
                    ris_node.phase_metadata = ris.phase_metadata

        # Calculate local deflection from RIS normal
        local_deflection = compute_offset_from_normal(beam_angle_deg, ris_normal)

        # Calculate RSSI using standardized utility (after any UE-absence overrides)
        if beam_hits_ue:
            rssi_dBm = compute_rssi_dBm(
                tx_power_dBm=ap.power_dBm,
                total_loss_dB=total_loss_dB,
                gain_dBi=total_gain_dBi
            )
        else:
            rssi_dBm = float(pwr_dBm)

        result = {
            "snr_dB": float(snr_dB),
            "pwr_dBm": float(pwr_dBm),
            "rssi_dBm": float(rssi_dBm),
            "gain_linear": float(gain_linear),
            "gain_dBi": float(gain_dBi),
            "quant_loss_dB": float(quant_loss_dB),
            "beam_angle": float(beam_angle_deg),
            "beam_angle_requested_deg": float(beam_angle_requested_deg),
            "evm_percent": float(Physics.snr_to_evm(snr_dB)),
            # Beam steering metadata
            "ris_normal_angle_deg": float(ris_normal),
            "local_deflection_deg": float(local_deflection),
            "target_angle_deg": float(target_angle),
            "ue_present": bool(beam_hits_ue),
            **phase_data
        }
        result["no_ue_detected"] = not beam_hits_ue

        # Automatic CSI feedback and closed-loop adaptation
        if enable_feedback:
            result["feedback_info"] = self._run_adaptive_feedback_loop(
                ap_name, ris_name, ue_name, snr_dB, max_feedback_iterations,
                bandwidth_MHz, seed, use_isolated_copy=use_isolated_copy,
                store_in_active_links=store_in_active_links
            )

            # OPTION A: Persist UE measurement back to network node for future queries
            # This allows the messaging system to return measured SNR on subsequent connect() calls
            if result["feedback_info"] and "final_snr_dB" in result["feedback_info"]:
                final_measured_snr = result["feedback_info"]["final_snr_dB"]
                if final_measured_snr is not None:
                    # Update the actual network UE node with the measured SNR
                    ue_node = self.get(ue_name)
                    if ue_node is not None:
                        ue_node.snr_measurement_dB = float(final_measured_snr)

        metadata = {
            'ap_name': ap_key,
            'ris_name': ris_key,
            'ue_name': ue_key,
            'tx_power_dBm': float(ap.power_dBm),
            'total_loss_dB': float(total_loss_dB),
            'total_gain_dBi': float(total_gain_dBi),
            'bandwidth_MHz': float(bandwidth_MHz),
            'noise_figure_dB': float(noise_figure_dB),
            'beam_angle_deg': float(beam_angle_deg),
            'beam_angle_requested_deg': float(beam_angle_requested_deg),
            'target_angle_deg': float(target_angle),
            'quant_loss_dB': float(quant_loss_dB),
            'gain_dBi': float(gain_dBi),
            'ap_antenna_gain_dBi': float(ap_antenna_gain_dBi),
            'ue_antenna_gain_dBi': float(ue_antenna_gain_dBi),
            'pwr_dBm': float(pwr_dBm),
            'ue_present': bool(beam_hits_ue)
        }
        if ue_node is not None:
            ue_node.snr_measurement_dB = float(snr_computed_dB)
            ue_node.store_link_metadata(ap_key, ris_key, dict(metadata))

        # Use get_snr() via messaging system AFTER persisting metadata.
        # Check both the parameter and the global network setting.
        should_use_get_snr = use_get_snr or self.use_get_snr_global
        if should_use_get_snr and self.snr_messaging is not None:
            queried_snr = self.snr_messaging.get_snr(ue_key, ris_key, ap_name=ap_key)
            if queried_snr is not None:
                snr_dB = queried_snr
            else:
                snr_dB = snr_computed_dB
        else:
            snr_dB = snr_computed_dB

        if ue_node is not None:
            ue_node.snr_measurement_dB = float(snr_dB)

        # Track active link (only if not an intermediate sweep measurement)
        if store_in_active_links:
            link_key = f"{ap_key}→{ris_key}→{ue_key} (Connect)"
            self.active_links[link_key] = {
                'ap': ap_key,
                'ris': ris_key,
                'ue': ue_key,
                'snr_dB': result['snr_dB'],
                'pwr_dBm': result['pwr_dBm'],
                'beam_angle_local': float(local_deflection),  # LOCAL deflection (what to send to RIS: -60 to +60)
                'beam_angle_absolute': float(beam_angle_deg),  # ABSOLUTE angle (world/global reference)
                'ris_normal_angle': float(ris_normal),  # RIS normal angle (for coordinate conversion)
                'gain_dBi': result.get('gain_dBi', 0.0),
                'quant_loss_dB': result.get('quant_loss_dB', 0.0),
                'source': 'connect',
                # Store phase data for retrieval by phases command
                'current_phases': result.get('current_phases', None),
                'quantized_phases': result.get('quantized_phases', None),
                'phase_states': result.get('phase_states', None),
                # Store phase metadata (deflection angle and azimuths) for new format display
                'deflection_angle_deg': result.get('deflection_angle_deg', None),
                'incident_azimuth_deg': result.get('incident_azimuth_deg', None),
                'reflected_azimuth_deg': result.get('reflected_azimuth_deg', None),
            }

        self.last_connect_result = {
            'ap': ap_key,
            'ris': ris_key,
            'ue': ue_key,
            'captured_at': datetime.utcnow().isoformat() + 'Z',
            'parameters': {
                'beam_angle_deg': float(beam_angle_deg),
                'compute_phases': bool(compute_phases),
                'bandwidth_MHz': float(bandwidth_MHz) if bandwidth_MHz is not None else None,
                'seed': seed,
                'enable_feedback': bool(enable_feedback),
                'max_feedback_iterations': int(max_feedback_iterations)
            },
            'metrics': dict(result)
        }

        return result

    def _run_adaptive_feedback_loop(self, ap_name, ris_name, ue_name, initial_snr_dB,
                                    max_iterations, bandwidth_MHz, seed, use_isolated_copy=True,
                                    store_in_active_links=True):
        """Run closed-loop feedback between UE and AP for adaptation

        Mimics real hardware: UE measures SNR and sends feedback to AP,
        AP adapts power/modulation, then transmits again.

        OPTION 3 INTEGRATION: Automatically pushes measured SNR to feedback channel
        so RIS controller can query real measurements.

        Args:
            use_isolated_copy: Whether feedback loop uses isolated copies
            store_in_active_links: Whether to store feedback iteration results in active_links
        """
        ap = self.get(ap_name)
        ue = self.get(ue_name)

        if not ap or not ue:
            return {"error": "Invalid AP or UE"}

        # Use isolated clones for feedback loop if specified
        if use_isolated_copy:
            ap = ap.clone()
            ue = ue.clone()

        # Option 3: Get or create feedback channel for UE → RIS controller
        feedback_channel = self.get_feedback_channel(ue_name, ris_name)
        if feedback_channel is None:
            # Auto-create channel if it doesn't exist
            feedback_channel = self.create_feedback_channel(ue_name, ris_name, history_size=100)

        def _to_float(value):
            if isinstance(value, np.ndarray):
                if value.size == 0:
                    return 0.0
                return float(value.reshape(-1)[0])
            if isinstance(value, (np.floating, np.integer)):
                return float(value)
            return float(value) if isinstance(value, (int, float)) else value

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
                snr_measured = _to_float(initial_snr_dB)
            else:
                # Re-compute link with adapted power
                # Note: Keep compute_phases=False to match initial call setting
                link_result = self.connect(
                    ap_name, ris_name, ue_name,
                    compute_phases=False,  # Use same setting as parent call
                    bandwidth_MHz=bandwidth_MHz,
                    seed=seed,
                    enable_feedback=False,
                    store_in_active_links=store_in_active_links
                )
                snr_measured = _to_float(link_result["snr_dB"])

            # UE measures SNR and generates feedback
            ue.estimate_snr_from_waveform(
                rx_signal=np.random.randn(1000) + 1j * np.random.randn(1000),
                noise_power=0.01
            )
            ue.snr_measurement_dB = snr_measured

            # Option 3: Generate CSI and automatically push to feedback channel
            csi_feedback = ue.generate_csi_feedback(
                snr_dB=snr_measured,
                feedback_channel=feedback_channel  # Push to channel for controller
            )

            # AP receives feedback and adapts
            control_action = ap.process_csi_feedback(csi_feedback)

            snr_error = abs(ap.target_snr_dB - snr_measured)
            converged = snr_error < 1.0

            iteration_info = {
                "iteration": iteration,
                "measured_snr_dB": snr_measured,
                "ap_power_dBm": float(ap.power_dBm),
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
            "final_power_dBm": float(ap.power_dBm),
            "final_mcs": ap.get_current_mcs()["name"],
            "final_snr_dB": final_iteration["measured_snr_dB"] if final_iteration else None
        }

    def direct_link(self, ap_name: str, ue_name: str,
                    bandwidth_MHz: Optional[float] = None,
                    apply_extra_loss: bool = True,
                    apply_blockage: bool = True,
                    use_isolated_copy: bool = True) -> Dict:
        """Compute direct AP→UE link budget without RIS assistance.

        Args:
            ap_name: Access point name
            ue_name: UE name
            bandwidth_MHz: Optional bandwidth override
            apply_extra_loss: Apply global extra_path_loss_dB impairment
            apply_blockage: Apply direct_blockage_dB impairment
            use_isolated_copy: If True (default), use cloned nodes to prevent state pollution.

        Returns:
            Dict with distance, losses, SNR, and RSSI.
        """
        ap = self.get(ap_name)
        ue = self.get(ue_name)

        # Use isolated clones by default to prevent cross-node state pollution
        if use_isolated_copy:
            ap = ap.clone()
            ue = ue.clone()

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

    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, fine_span=5, fine_res=1, seed=0,
              use_isolated_copy=True, use_get_snr=False):
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
            use_isolated_copy: If True (default), use cloned nodes to prevent state pollution.
            use_get_snr: If False (default for training), compute SNR physically. If True, use messaging system.

        Returns:
            Dict with sweep results
        """
        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)

        # Use isolated clones by default to prevent cross-node state pollution
        if use_isolated_copy:
            ap = ap.clone()
            ris = ris.clone()
            ue = ue.clone()

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # Use optimal RIS normal as bisector of AP and UE directions
        # This ensures consistency with all sweep algorithms
        ap_vec = ap.pos - ris.pos
        ap_angle = np.degrees(np.arctan2(ap_vec[1], ap_vec[0]))
        ue_vec = ue.pos - ris.pos
        ue_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        base_dir = compute_optimal_ris_normal(ap_angle, ue_angle)

        # Coarse sweep
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = base_dir + local_coarse

        snr_coarse = []
        pwr_coarse = []

        # Use deterministic seed for consistent SNR measurements across sweep
        for abs_a in abs_angles:
            res = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a, seed=seed, use_get_snr=use_get_snr)
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        # Find best coarse angle
        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # Fine sweep
        local_fine = np.arange(best_local - fine_span,
                               best_local + fine_span + fine_res,
                               fine_res)
        local_fine = np.clip(local_fine, -fov, fov)
        local_fine = np.unique(local_fine)
        abs_angles_fine = base_dir + local_fine
        snr_fine = []

        for abs_a in abs_angles_fine:
            # Use same seed for consistent comparison
            r = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a, seed=seed, use_get_snr=use_get_snr)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        sweep_outputs = {
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': np.array(snr_coarse).tolist(),
            'pwr_coarse': np.array(pwr_coarse).tolist(),
            'local_fine': local_fine.tolist(),
            'snr_fine': np.array(snr_fine).tolist(),
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(np.max(snr_fine))
        }

        self.last_sweep_result = {
            'ap': ap_name,
            'ris': ris_name,
            'ue': ue_name,
            'captured_at': datetime.utcnow().isoformat() + 'Z',
            'algorithm': 'network.sweep',
            'parameters': {
                'fov': float(fov),
                'step': float(step),
                'fine_span': float(fine_span),
                'fine_res': float(fine_res),
                'seed': seed
            },
            'outputs': dict(sweep_outputs)
        }

        return sweep_outputs

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
