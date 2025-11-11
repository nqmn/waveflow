"""
Node classes for RIS network simulation
"""
import numpy as np
from typing import Dict, Optional
import copy
from .physics import C

class Node:
    """Base class for all network nodes"""

    def __init__(self, name, x, y, z=0.0):
        self.name = name
        self.pos = np.array([float(x), float(y), float(z)])

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.name}', pos={self.pos.tolist()})"

    def clone(self):
        """Create a complete independent copy of this node with all state.

        Returns:
            Node: Deep copy with no shared references to original
        """
        return copy.deepcopy(self)

    def to_dict(self):
        """Convert node to dictionary for API responses"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'pos': self.pos.tolist()
        }


class AccessPoint(Node):
    """Access Point (AP) node with adaptive power control and rate adaptation"""

    MCS_TABLE = [
        {'name': 'BPSK-1/2', 'modulation': 'BPSK', 'coding_rate': 0.5,
         'bits_per_symbol': 1, 'req_snr_dB': 0.0, 'efficiency_bps_hz': 0.5},
        {'name': 'QPSK-1/2', 'modulation': 'QPSK', 'coding_rate': 0.5,
         'bits_per_symbol': 2, 'req_snr_dB': 3.0, 'efficiency_bps_hz': 1.0},
        {'name': 'QPSK-3/4', 'modulation': 'QPSK', 'coding_rate': 0.75,
         'bits_per_symbol': 2, 'req_snr_dB': 7.0, 'efficiency_bps_hz': 1.5},
        {'name': '16QAM-1/2', 'modulation': '16QAM', 'coding_rate': 0.5,
         'bits_per_symbol': 4, 'req_snr_dB': 10.0, 'efficiency_bps_hz': 2.0},
        {'name': '16QAM-3/4', 'modulation': '16QAM', 'coding_rate': 0.75,
         'bits_per_symbol': 4, 'req_snr_dB': 14.0, 'efficiency_bps_hz': 3.0},
        {'name': '64QAM-2/3', 'modulation': '64QAM', 'coding_rate': 0.667,
         'bits_per_symbol': 6, 'req_snr_dB': 18.0, 'efficiency_bps_hz': 4.0},
        {'name': '64QAM-5/6', 'modulation': '64QAM', 'coding_rate': 0.833,
         'bits_per_symbol': 6, 'req_snr_dB': 22.0, 'efficiency_bps_hz': 5.0},
    ]

    def __init__(self, name, x, y, z=0.0, power_dBm=20.0, freq=5.8e9,
                 bandwidth_MHz=20.0, antenna_gain_dBi=3.0,
                 noise_figure_dB=6.0):
        super().__init__(name, x, y, z)
        self.power_dBm = power_dBm
        self.power_dBm_init = power_dBm
        self.freq = freq
        self.bandwidth_MHz = bandwidth_MHz
        self.antenna_gain_dBi = antenna_gain_dBi
        self.noise_figure_dB = noise_figure_dB

        # Adaptive power control parameters
        self.target_snr_dB = 20.0
        self.power_dBm_max = 30.0
        self.power_dBm_min = 10.0
        self.power_step_dB = 1.0
        self._power_control_enabled = False
        self._power_control_override = False

        # Rate adaptation parameters
        self.current_mcs_index = 2
        self.mcs_hysteresis_dB = 2.0
        self._rate_adaptation_enabled = False
        self._rate_adaptation_override = False

        # Feedback from UE
        self.last_csi_feedback = None
        self.csi_history = []

    def set_power_control_enabled(self, enabled: bool,
                                  user_override: Optional[bool] = True):
        """Set power-control flag, tracking whether user explicitly overrode it."""
        self._power_control_enabled = bool(enabled)
        if user_override is True:
            self._power_control_override = True
        elif user_override is False:
            self._power_control_override = False

    @property
    def power_control_enabled(self) -> bool:
        return self._power_control_enabled

    @power_control_enabled.setter
    def power_control_enabled(self, enabled: bool):
        self.set_power_control_enabled(enabled, user_override=True)

    def power_control_override_active(self) -> bool:
        return self._power_control_override

    def set_rate_adaptation_enabled(self, enabled: bool,
                                    user_override: Optional[bool] = True):
        """Set rate-adaptation flag, tracking user overrides."""
        self._rate_adaptation_enabled = bool(enabled)
        if user_override is True:
            self._rate_adaptation_override = True
        elif user_override is False:
            self._rate_adaptation_override = False

    @property
    def rate_adaptation_enabled(self) -> bool:
        return self._rate_adaptation_enabled

    @rate_adaptation_enabled.setter
    def rate_adaptation_enabled(self, enabled: bool):
        self.set_rate_adaptation_enabled(enabled, user_override=True)

    def rate_adaptation_override_active(self) -> bool:
        return self._rate_adaptation_override

    def closed_loop_power_control(self, measured_snr_dB: float) -> Dict:
        """Adjust transmit power based on SNR feedback

        Args:
            measured_snr_dB: SNR measured by UE (dB)

        Returns:
            Control action dict with power change info
        """
        if not self.power_control_enabled:
            return {'status': 'disabled'}

        snr_error = self.target_snr_dB - measured_snr_dB
        power_adjustment = 0.5 * snr_error

        old_power = self.power_dBm
        new_power = self.power_dBm + power_adjustment
        new_power = np.clip(new_power, self.power_dBm_min, self.power_dBm_max)

        if abs(new_power - old_power) >= self.power_step_dB:
            self.power_dBm = new_power
            return {
                'status': 'updated',
                'old_power_dBm': old_power,
                'new_power_dBm': new_power,
                'adjustment_dB': new_power - old_power,
                'snr_error_dB': snr_error
            }
        else:
            return {
                'status': 'converged',
                'current_power_dBm': self.power_dBm,
                'snr_error_dB': snr_error
            }

    def select_mcs(self, measured_snr_dB: float) -> Dict:
        """Select modulation and coding scheme based on SNR

        Args:
            measured_snr_dB: SNR measured by UE (dB)

        Returns:
            MCS selection dict
        """
        if not self.rate_adaptation_enabled:
            current_mcs = self.MCS_TABLE[self.current_mcs_index]
            return {
                'status': 'disabled',
                'mcs': current_mcs['name'],
                'efficiency_bps_hz': current_mcs['efficiency_bps_hz']
            }

        current_req_snr = self.MCS_TABLE[self.current_mcs_index]['req_snr_dB']

        old_index = self.current_mcs_index

        if (measured_snr_dB > current_req_snr + self.mcs_hysteresis_dB and
            self.current_mcs_index < len(self.MCS_TABLE) - 1):
            self.current_mcs_index += 1

        elif (measured_snr_dB < current_req_snr - self.mcs_hysteresis_dB and
              self.current_mcs_index > 0):
            self.current_mcs_index -= 1

        current_mcs = self.MCS_TABLE[self.current_mcs_index]

        return {
            'status': 'updated' if old_index != self.current_mcs_index else 'unchanged',
            'mcs': current_mcs['name'],
            'modulation': current_mcs['modulation'],
            'coding_rate': current_mcs['coding_rate'],
            'bits_per_symbol': current_mcs['bits_per_symbol'],
            'efficiency_bps_hz': current_mcs['efficiency_bps_hz'],
            'old_index': old_index,
            'new_index': self.current_mcs_index
        }

    def process_csi_feedback(self, csi_feedback: Dict) -> Dict:
        """Process CSI feedback from UE

        Args:
            csi_feedback: CSI report from UE

        Returns:
            Processed feedback with control actions
        """
        if csi_feedback is None:
            return {'error': 'No CSI feedback received'}

        self.last_csi_feedback = csi_feedback
        self.csi_history.append(csi_feedback)

        snr_dB = csi_feedback.get('snr_dB')
        if snr_dB is None:
            return {'error': 'No SNR in CSI feedback'}

        result = {
            'ue_name': csi_feedback.get('ue_name'),
            'snr_dB': snr_dB,
            'power_control': self.closed_loop_power_control(snr_dB),
            'rate_adaptation': self.select_mcs(snr_dB)
        }

        return result

    def get_current_mcs(self) -> Dict:
        """Get currently configured MCS"""
        return self.MCS_TABLE[self.current_mcs_index].copy()

    def reset_adaptation(self):
        """Reset adaptation to initial state"""
        self.power_dBm = self.power_dBm_init
        self.current_mcs_index = 2
        self.last_csi_feedback = None
        self.csi_history.clear()

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'power_dBm': self.power_dBm,
            'freq': self.freq,
            'bandwidth_MHz': self.bandwidth_MHz,
            'antenna_gain_dBi': self.antenna_gain_dBi,
            'noise_figure_dB': self.noise_figure_dB,
            'current_mcs': self.get_current_mcs(),
            'power_control_enabled': self.power_control_enabled,
            'rate_adaptation_enabled': self.rate_adaptation_enabled,
            'target_snr_dB': self.target_snr_dB
        })
        return d


class RIS(Node):
    """Reconfigurable Intelligent Surface with phase control"""

    def __init__(self, name, x, y, z=0.0, N=32, bits=2, spacing=None,
                 freq=10e9, max_angle_deg=60, normal_angle_deg=0.0, active_mode=False,
                 amplifier_gain=1.0, element_efficiency=0.95,
                 phase_error_std_deg=8.0, amp_std=0.15,
                 coupling_enabled=True, K_db=10, noise_floor=-90.0):
        super().__init__(name, x, y, z)
        self.N = int(N)  # Array size (will create N x N grid)
        self.bits = int(bits)  # Phase quantization bits
        self.freq = freq
        self.max_angle_deg = max_angle_deg  # Maximum steering angle
        self.normal_angle_deg = normal_angle_deg  # RIS normal/facing direction (0° = east)
        self.active_mode = active_mode  # Active vs passive RIS
        self.amplifier_gain = amplifier_gain if active_mode else 1.0
        self.element_efficiency = element_efficiency

        # Element spacing (default: λ/2)
        wavelength = C / freq
        self.spacing = spacing if spacing is not None else wavelength / 2.0

        # Physical properties
        self.element_positions = None
        self.phase_rms = phase_error_std_deg  # Phase error RMS (degrees)
        self.amp_std = amp_std  # Amplitude variation std dev
        self.coupling_enabled = coupling_enabled
        self.K_db = K_db  # Rician K-factor
        self.P_tx_dBm = 20  # Default transmit power
        self.noise_floor = noise_floor  # Noise floor in dBm

        # Current configuration
        self.current_phases = None  # Ideal phases (radians)
        self.quantized_phases = None  # Quantized phases (radians)
        self.current_beam_angle = None
        self.phase_states = None  # Integer states (0 to 2^bits - 1)
        self.specular_angle_deg = None
        self.abs_beam_angle_deg = None
        self.local_beam_deflection_deg = None

        # Phase manager (lazy-loaded on demand)
        self._phase_manager = None

        self.update_geometry()

    def update_geometry(self):
        """Update element positions based on RIS position and spacing

        Creates a 2D grid of elements in the XY plane
        """
        self.element_positions = np.zeros((self.N * self.N, 3))
        idx = 0
        for i in range(self.N):
            for j in range(self.N):
                # Center the array at RIS position
                x_off = (i - (self.N - 1) / 2.0) * self.spacing
                y_off = (j - (self.N - 1) / 2.0) * self.spacing
                self.element_positions[idx] = self.pos + np.array([x_off, y_off, 0.0])
                idx += 1

    def set_bits(self, bits):
        """Update phase quantization bits"""
        self.bits = int(bits)

    def set_beam_config(self, beam_angle, phases=None):
        """Set current beam configuration

        Args:
            beam_angle: Beam steering angle in degrees.
                       IMPORTANT: This should be the LOCAL deflection angle (relative to RIS normal),
                       NOT the absolute world angle. For example, if RIS normal is 45° and you want
                       to steer +20° from normal, pass beam_angle=20.0, not 65.0.
                       Valid range: -max_angle_deg to +max_angle_deg (typically ±60°)
            phases: Optional explicit phase array (radians)
        """
        self.current_beam_angle = beam_angle
        if phases is not None:
            self.current_phases = phases

    def compute_phases(self, ap_pos, ue_pos):
        """Compute ideal RIS phases for AP->RIS->UE beamforming

        Args:
            ap_pos: Access Point position (3D array)
            ue_pos: User Equipment position (3D array)

        Returns:
            phase_array: Ideal phases in radians (N×N grid, flattened)
        """
        from .physics import Physics

        wavelength = C / self.freq

        # Compute ideal phases using wavefront matching
        phases = Physics.compute_ris_phases(ue_pos, self.element_positions, ap_pos, wavelength)

        # Store ideal phases
        self.current_phases = phases

        return phases

    def _get_phase_manager(self):
        """Lazy-load phase manager from controller module"""
        if self._phase_manager is None:
            from controller.ris_phase import RISPhaseManager
            self._phase_manager = RISPhaseManager(self)
        return self._phase_manager

    def quantize_phases(self):
        """Quantize current ideal phases to discrete levels based on bits

        Uses the controller phase quantization system.

        Returns:
            (quantized_phases, phase_states): Quantized phases and their integer states
        """
        if self.current_phases is None:
            return None, None

        # Use controller phase quantization
        phase_manager = self._get_phase_manager()
        result = phase_manager.quantize_phases()

        if result.get('status') == 'success':
            # Phases already updated by quantizer
            return self.quantized_phases, self.phase_states

        return None, None

    def get_phase_grid(self):
        """Get phases formatted as N×N grid for visualization

        Returns:
            Dict with ideal and quantized phase grids (in degrees)
        """
        if self.current_phases is None:
            return None

        ideal_deg = np.degrees(self.current_phases).reshape(self.N, self.N)

        result = {
            'ideal_deg': ideal_deg.tolist(),
            'quantized_deg': None,
            'phase_states': None
        }

        if self.quantized_phases is not None:
            quantized_deg = np.degrees(self.quantized_phases).reshape(self.N, self.N)
            result['quantized_deg'] = quantized_deg.tolist()

        if self.phase_states is not None:
            result['phase_states'] = self.phase_states.reshape(self.N, self.N).tolist()

        return result

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'N': self.N,
            'bits': self.bits,
            'freq': self.freq,
            'max_angle_deg': self.max_angle_deg,
            'active_mode': self.active_mode,
            'amplifier_gain': self.amplifier_gain,
            'element_efficiency': self.element_efficiency,
            'phase_error_std_deg': self.phase_rms,
            'amp_std': self.amp_std,
            'coupling_enabled': self.coupling_enabled,
            'K_db': self.K_db,
            'noise_floor': self.noise_floor,
            'total_elements': self.N * self.N,
            'current_beam_angle': self.current_beam_angle,
            'phase_manager': 'controller.ris_phase.RISPhaseManager'
        })
        return d


class UE(Node):
    """User Equipment (receiver) node with customizable impairments and CSI estimation"""

    def __init__(self, name, x, y, z=0.0, antenna_gain_dBi=3.0,
                 noise_figure_dB=6.0, max_angle_deg=180.0, normal_angle_deg=0.0):
        super().__init__(name, x, y, z)
        self.antenna_gain_dBi = antenna_gain_dBi
        self.noise_figure_dB = noise_figure_dB

        # Antenna FOV parameters for directional reception
        # max_angle_deg: Field of view (±angle from normal, 0-180°)
        # normal_angle_deg: Direction antenna points toward (0-360°)
        self.max_angle_deg = float(max_angle_deg)
        self.normal_angle_deg = float(normal_angle_deg)

        # CSI feedback mechanism
        self.csi_report = None
        self.snr_measurement_dB = None
        self.channel_estimate = None
        self.last_feedback_time = None
        self.feedback_enabled = True

    def estimate_snr_from_waveform(self, rx_signal: np.ndarray,
                                   noise_power: float = 0.01) -> float:
        """Estimate SNR from received waveform samples

        Args:
            rx_signal: Complex baseband signal samples
            noise_power: Estimated noise power

        Returns:
            SNR in dB
        """
        signal_power = np.mean(np.abs(rx_signal)**2)
        noise_power = np.clip(noise_power, 1e-20, np.inf)

        if signal_power <= 1e-20:
            self.snr_measurement_dB = -120.0
        else:
            snr_linear = signal_power / noise_power
            snr_linear = np.clip(snr_linear, 1e-12, 1e12)
            self.snr_measurement_dB = 10 * np.log10(snr_linear)
            self.snr_measurement_dB = np.clip(self.snr_measurement_dB, -120.0, 120.0)

        return self.snr_measurement_dB

    def generate_csi_feedback(self, channel_est: np.ndarray = None,
                            snr_dB: float = None) -> Dict:
        """Generate CSI feedback report for transmission to AP

        Args:
            channel_est: Estimated channel (optional)
            snr_dB: Measured SNR in dB (optional, uses internal measurement if not provided)

        Returns:
            CSI feedback dictionary
        """
        import time

        feedback = {
            'ue_name': self.name,
            'timestamp': time.time(),
            'snr_dB': snr_dB if snr_dB is not None else self.snr_measurement_dB,
            'channel_estimate': channel_est,
            'antenna_gain_dBi': self.antenna_gain_dBi,
            'noise_figure_dB': self.noise_figure_dB
        }

        self.csi_report = feedback
        self.last_feedback_time = feedback['timestamp']
        return feedback

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'antenna_gain_dBi': self.antenna_gain_dBi,
            'noise_figure_dB': self.noise_figure_dB,
            'max_angle_deg': self.max_angle_deg,
            'normal_angle_deg': self.normal_angle_deg,
            'snr_measurement_dB': self.snr_measurement_dB,
            'feedback_enabled': self.feedback_enabled
        })
        return d
