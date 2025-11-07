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
        """Get node by name"""
        return self.nodes.get(name, None)

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

    # Basic connectivity (legacy method, kept for compatibility)
    def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None, compute_phases=True,
                bandwidth_MHz=None, seed=None):
        """Compute cascaded AP->RIS->UE link with proper SNR calculation

        Args:
            ap_name: AP node name
            ris_name: RIS node name
            ue_name: UE node name
            beam_angle_deg: Beam steering angle (None for auto)
            compute_phases: Whether to compute and quantize RIS phases
            bandwidth_MHz: Signal bandwidth in MHz for noise floor calculation
            seed: Random seed for reproducibility (None = use random fading each call)

        Returns:
            Dict with snr_dB, pwr_dBm, gain_dBi, quant_loss_dB
        """
        # Set seed for reproducibility if provided
        if seed is not None:
            np.random.seed(seed)

        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in connect")

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

        return {
            "snr_dB": float(snr_dB),
            "pwr_dBm": float(pwr_dBm),
            "rssi_dBm": float(pwr_dBm),
            "gain_linear": float(gain_linear),
            "gain_dBi": float(gain_dBi),
            "quant_loss_dB": float(quant_loss_dB),
            "beam_angle": float(beam_angle_deg),
            "evm_percent": float(Physics.snr_to_evm(snr_dB))
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
