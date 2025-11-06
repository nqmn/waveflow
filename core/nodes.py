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
    """Access Point (AP) node with transmission capabilities"""

    def __init__(self, name, x, y, z=0.0, power_dBm=20.0, freq=10e9):
        super().__init__(name, x, y, z)
        self.power_dBm = power_dBm
        self.freq = freq

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'power_dBm': self.power_dBm,
            'freq': self.freq
        })
        return d


class RIS(Node):
    """Reconfigurable Intelligent Surface with phase control"""

    def __init__(self, name, x, y, z=0.0, N=32, bits=2, spacing=None,
                 freq=10e9, max_angle_deg=60, active_mode=False, amplifier_gain=1.0):
        super().__init__(name, x, y, z)
        self.N = int(N)  # Array size (will create N x N grid)
        self.bits = int(bits)  # Phase quantization bits
        self.freq = freq
        self.max_angle_deg = max_angle_deg  # Maximum steering angle
        self.active_mode = active_mode  # Active vs passive RIS
        self.amplifier_gain = amplifier_gain if active_mode else 1.0

        # Element spacing (default: λ/2)
        wavelength = C / freq
        self.spacing = spacing if spacing is not None else wavelength / 2.0

        # Physical properties
        self.element_positions = None
        self.phase_rms = 8.0  # Phase error RMS (degrees)
        self.amp_std = 0.15  # Amplitude variation std dev
        self.coupling_enabled = True
        self.K_db = 10  # Rician K-factor
        self.P_tx_dBm = 20  # Default transmit power
        self.noise_floor = -90  # Noise floor in dBm

        # Current configuration
        self.current_phases = None
        self.current_beam_angle = None

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

    def to_dict(self):
        d = super().to_dict()
        d.update({
            'N': self.N,
            'bits': self.bits,
            'freq': self.freq,
            'max_angle_deg': self.max_angle_deg,
            'active_mode': self.active_mode,
            'amplifier_gain': self.amplifier_gain,
            'total_elements': self.N * self.N,
            'current_beam_angle': self.current_beam_angle
        })
        return d


class UE(Node):
    """User Equipment (receiver) node"""

    def __init__(self, name, x, y, z=0.0):
        super().__init__(name, x, y, z)

    def to_dict(self):
        return super().to_dict()
