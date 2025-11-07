"""
Node classes for RIS network simulation
"""
import numpy as np
from .physics import C

class Node:
    """Base class for all network nodes"""

    def __init__(self, name, x, y, z=0.0):
        self.name = name
        self.pos = np.array([float(x), float(y), float(z)])

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.name}', pos={self.pos.tolist()})"

    def to_dict(self):
        """Convert node to dictionary for API responses"""
        return {
            'name': self.name,
            'type': self.__class__.__name__,
            'pos': self.pos.tolist()
        }


class AccessPoint(Node):
    """Access Point (AP) node with transmission and RF impairments"""

    def __init__(self, name, x, y, z=0.0, power_dBm=20.0, freq=5.8e9,
                 bandwidth_MHz=20.0, antenna_gain_dBi=3.0,
                 noise_figure_dB=6.0):
        super().__init__(name, x, y, z)
        self.power_dBm = power_dBm
        self.freq = freq
        self.bandwidth_MHz = bandwidth_MHz
        self.antenna_gain_dBi = antenna_gain_dBi
        self.noise_figure_dB = noise_figure_dB

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'power_dBm': self.power_dBm,
            'freq': self.freq,
            'bandwidth_MHz': self.bandwidth_MHz,
            'antenna_gain_dBi': self.antenna_gain_dBi,
            'noise_figure_dB': self.noise_figure_dB
        })
        return d


class RIS(Node):
    """Reconfigurable Intelligent Surface with phase control"""

    def __init__(self, name, x, y, z=0.0, N=32, bits=2, spacing=None,
                 freq=10e9, max_angle_deg=60, active_mode=False,
                 amplifier_gain=1.0, element_efficiency=0.95,
                 phase_error_std_deg=8.0, amp_std=0.15,
                 coupling_enabled=True, K_db=10, noise_floor=-90.0):
        super().__init__(name, x, y, z)
        self.N = int(N)  # Array size (will create N x N grid)
        self.bits = int(bits)  # Phase quantization bits
        self.freq = freq
        self.max_angle_deg = max_angle_deg  # Maximum steering angle
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
            beam_angle: Beam steering angle in degrees
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
    """User Equipment (receiver) node with customizable impairments"""

    def __init__(self, name, x, y, z=0.0, antenna_gain_dBi=3.0,
                 noise_figure_dB=6.0):
        super().__init__(name, x, y, z)
        self.antenna_gain_dBi = antenna_gain_dBi
        self.noise_figure_dB = noise_figure_dB

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'antenna_gain_dBi': self.antenna_gain_dBi,
            'noise_figure_dB': self.noise_figure_dB
        })
        return d
