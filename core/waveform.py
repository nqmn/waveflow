"""
Waveform-level simulation components for RISNet
Supports OFDM signals, multipath channels, and waveform processing
"""
import numpy as np
from scipy import signal
from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class OFDMConfig:
    """OFDM Signal Configuration"""
    bandwidth: float = 100e6  # Hz (100 MHz)
    num_subcarriers: int = 256
    num_pilot_subcarriers: int = 32
    cyclic_prefix_ratio: float = 0.25
    sampling_rate: Optional[float] = None
    center_frequency: float = 10e9  # Hz

    def __post_init__(self):
        if self.sampling_rate is None:
            self.sampling_rate = self.bandwidth * 2  # Nyquist

        self.subcarrier_spacing = self.bandwidth / self.num_subcarriers
        self.symbol_duration = 1.0 / self.subcarrier_spacing
        self.cp_duration = self.cyclic_prefix_ratio * self.symbol_duration
        self.samples_per_symbol = int(self.sampling_rate * self.symbol_duration)
        self.samples_cp = int(self.sampling_rate * self.cp_duration)


class OFDMSignal:
    """OFDM Signal Generator and Processor"""

    def __init__(self, config: OFDMConfig = None, num_symbols: int = 10):
        """
        Initialize OFDM signal

        Args:
            config: OFDM configuration
            num_symbols: Number of OFDM symbols
        """
        self.config = config or OFDMConfig()
        self.num_symbols = num_symbols

        # Initialize pilot and data subcarrier indices
        self._init_subcarriers()

    def _init_subcarriers(self):
        """Initialize pilot and data subcarrier mapping"""
        total_sc = self.config.num_subcarriers
        pilot_indices = np.linspace(0, total_sc - 1,
                                   self.config.num_pilot_subcarriers,
                                   dtype=int)
        self.pilot_indices = pilot_indices
        self.data_indices = np.setdiff1d(np.arange(total_sc), pilot_indices)

    def generate(self, seed: int = 42) -> np.ndarray:
        """
        Generate OFDM signal in time domain

        Args:
            seed: Random seed for reproducibility

        Returns:
            Complex time-domain signal (num_symbols * samples_per_symbol_with_cp,)
        """
        np.random.seed(seed)
        N = self.config.num_subcarriers
        num_symbols = self.num_symbols

        # Frequency domain symbols
        freq_symbols = np.zeros((num_symbols, N), dtype=complex)

        for sym_idx in range(num_symbols):
            # Pilot subcarriers: known reference signals
            freq_symbols[sym_idx, self.pilot_indices] = \
                np.exp(1j * np.random.uniform(0, 2*np.pi, len(self.pilot_indices)))

            # Data subcarriers: QPSK modulation
            freq_symbols[sym_idx, self.data_indices] = \
                (np.random.randint(0, 2, len(self.data_indices)) * 2 - 1 +
                 1j * (np.random.randint(0, 2, len(self.data_indices)) * 2 - 1)) / np.sqrt(2)

        # IFFT to get time domain
        time_symbols = np.fft.ifft(freq_symbols, axis=1) * N  # Scale for power

        # Add cyclic prefix and concatenate
        signal_td = np.zeros(num_symbols * (self.config.samples_per_symbol + self.config.samples_cp),
                             dtype=complex)

        idx = 0
        samples_per_symbol = self.config.samples_per_symbol
        samples_cp = self.config.samples_cp

        for sym_idx in range(num_symbols):
            symbol_samples = time_symbols[sym_idx, :]

            # Resample to actual sampling rate if needed
            if len(symbol_samples) != samples_per_symbol:
                symbol_samples = signal.resample(symbol_samples, samples_per_symbol)

            # Add cyclic prefix (last samples_cp samples)
            cp = symbol_samples[-samples_cp:]
            signal_td[idx:idx+samples_cp] = cp
            idx += samples_cp
            signal_td[idx:idx+samples_per_symbol] = symbol_samples
            idx += samples_per_symbol

        # Normalize power
        signal_td = signal_td / np.sqrt(np.mean(np.abs(signal_td)**2))

        return signal_td

    def get_subcarrier_grid(self) -> Dict:
        """Get OFDM subcarrier information"""
        return {
            'num_subcarriers': self.config.num_subcarriers,
            'subcarrier_spacing': self.config.subcarrier_spacing,
            'pilot_indices': self.pilot_indices.tolist(),
            'data_indices': self.data_indices.tolist(),
            'bandwidth': self.config.bandwidth,
            'symbol_duration': self.config.symbol_duration
        }


@dataclass
class PathComponent:
    """Single multipath component"""
    delay: float  # seconds
    amplitude: float  # linear magnitude
    phase: float  # radians
    doppler_shift: float = 0.0  # Hz


class PropagationChannel:
    """Multipath fading channel model"""

    def __init__(self, center_freq: float, sampling_rate: float,
                 K_factor_dB: float = 10, model: str = '3GPP_UMi'):
        """
        Initialize channel model

        Args:
            center_freq: Center frequency in Hz
            sampling_rate: Sampling rate in Hz
            K_factor_dB: Rician K-factor (dB)
            model: Channel model ('3GPP_UMi', 'simple_multipath', 'awgn')
        """
        self.center_freq = center_freq
        self.sampling_rate = sampling_rate
        self.K_factor_dB = K_factor_dB
        self.model = model
        self.wavelength = 3e8 / center_freq

        self.paths: List[PathComponent] = []
        self._init_model()

    def _init_model(self):
        """Initialize channel model paths"""
        if self.model == 'simple_multipath':
            # Direct path + 2 reflected paths
            self.paths = [
                PathComponent(delay=0.0, amplitude=1.0, phase=0.0),  # Direct
                PathComponent(delay=10e-9, amplitude=0.5, phase=np.pi/4),  # First reflection
                PathComponent(delay=20e-9, amplitude=0.3, phase=-np.pi/3),  # Second reflection
            ]
        elif self.model == '3GPP_UMi':
            # Simplified 3GPP Urban Micro channel
            self.paths = [
                PathComponent(delay=0.0, amplitude=1.0, phase=0.0),  # LoS
                PathComponent(delay=50e-9, amplitude=0.2, phase=np.pi/2),  # NLoS
            ]
        elif self.model == 'awgn':
            # AWGN only
            self.paths = [
                PathComponent(delay=0.0, amplitude=1.0, phase=0.0),
            ]

    def get_impulse_response(self, duration: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get channel impulse response

        Args:
            duration: Duration in seconds

        Returns:
            (time vector, impulse response)
        """
        num_samples = int(duration * self.sampling_rate)
        h = np.zeros(num_samples, dtype=complex)

        for path in self.paths:
            delay_samples = int(path.delay * self.sampling_rate)
            if 0 <= delay_samples < num_samples:
                h[delay_samples] += path.amplitude * np.exp(1j * path.phase)

        time = np.arange(num_samples) / self.sampling_rate
        return time, h

    def propagate(self, signal_tx: np.ndarray) -> np.ndarray:
        """
        Propagate signal through channel

        Args:
            signal_tx: Transmitted signal

        Returns:
            Received signal (same length as input)
        """
        signal_rx = np.zeros_like(signal_tx)

        for path in self.paths:
            delay_samples = int(path.delay * self.sampling_rate)
            amplitude = path.amplitude * np.exp(1j * path.phase)

            # Apply Doppler shift if present
            if path.doppler_shift != 0:
                doppler_phase = 2 * np.pi * path.doppler_shift * np.arange(len(signal_tx)) / self.sampling_rate
                amplitude *= np.exp(1j * doppler_phase)

            if delay_samples >= 0:
                signal_rx[delay_samples:] += amplitude * signal_tx[:len(signal_rx) - delay_samples]

        return signal_rx

    def add_awgn(self, signal: np.ndarray, snr_dB: float) -> np.ndarray:
        """
        Add AWGN to signal

        Args:
            signal: Input signal
            snr_dB: SNR in dB

        Returns:
            Signal with noise added
        """
        snr_linear = 10 ** (snr_dB / 10)
        signal_power = np.mean(np.abs(signal)**2)
        noise_power = signal_power / snr_linear
        noise = np.sqrt(noise_power / 2) * (np.random.randn(len(signal)) +
                                            1j * np.random.randn(len(signal)))
        return signal + noise


class AntennaArray:
    """Antenna array with radiation patterns"""

    def __init__(self, array_type: str = 'ula', num_elements: int = 1,
                 spacing: float = 0.5, center_freq: float = 10e9):
        """
        Initialize antenna array

        Args:
            array_type: 'ula' (uniform linear), 'upa' (planar), or 'isotropic'
            num_elements: Number of elements
            spacing: Element spacing in wavelengths
            center_freq: Center frequency in Hz
        """
        self.array_type = array_type
        self.num_elements = num_elements
        self.spacing = spacing
        self.center_freq = center_freq
        self.wavelength = 3e8 / center_freq

        self._init_positions()

    def _init_positions(self):
        """Initialize element positions"""
        if self.array_type == 'ula':
            # Linear array along x-axis
            self.positions = np.zeros((self.num_elements, 3))
            for i in range(self.num_elements):
                self.positions[i, 0] = (i - (self.num_elements - 1) / 2) * self.spacing * self.wavelength
        elif self.array_type == 'upa':
            # Planar array (square grid)
            side = int(np.sqrt(self.num_elements))
            self.positions = np.zeros((self.num_elements, 3))
            idx = 0
            for i in range(side):
                for j in range(side):
                    self.positions[idx, 0] = (i - (side - 1) / 2) * self.spacing * self.wavelength
                    self.positions[idx, 1] = (j - (side - 1) / 2) * self.spacing * self.wavelength
                    idx += 1
        else:  # isotropic
            self.positions = np.zeros((self.num_elements, 3))

    def get_radiation_pattern(self, theta: float, phi: float = 0.0) -> np.ndarray:
        """
        Get array factor for given direction

        Args:
            theta: Elevation angle (radians, 0 = boresight)
            phi: Azimuth angle (radians)

        Returns:
            Array factor for each element (complex)
        """
        k = 2 * np.pi * self.center_freq / 3e8  # Wave number

        # Direction vector
        u = np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta)
        ])

        # Element response: phase shift due to steering
        phase_shifts = k * (self.positions @ u)
        return np.exp(1j * phase_shifts)

    def get_directional_gain_dB(self, theta: float, phi: float = 0.0,
                               element_gain_dBi: float = 3.0) -> float:
        """
        Get directional gain at given direction

        Args:
            theta: Elevation angle (radians)
            phi: Azimuth angle (radians)
            element_gain_dBi: Per-element gain (dBi)

        Returns:
            Gain in dBi (absolute)
        """
        # Array factor (normalized by num_elements for proper array gain)
        af = self.get_radiation_pattern(theta, phi)
        # Array gain: directivity of the array (peak normalized to 1)
        array_factor_magnitude = np.abs(np.sum(af)) / self.num_elements
        # Directivity in dB: 10*log10(N) for uniform array at boresight
        # Off-boresight: reduced by array factor
        array_gain_dB = 10 * np.log10(self.num_elements) + 20 * np.log10(np.clip(array_factor_magnitude, 1e-10, 1.0))

        # Element pattern (simplified: cosine pattern)
        cos_factor = max(0.01, np.cos(theta))  # Avoid log(0)
        element_pattern_dB = 10 * np.log10(cos_factor)

        return element_gain_dBi + array_gain_dB + element_pattern_dB

    def get_directional_gain_vector(self, theta_range: np.ndarray,
                                   element_gain_dBi: float = 3.0) -> np.ndarray:
        """Get gain across angle range"""
        gains = np.array([self.get_directional_gain_dB(theta, 0.0, element_gain_dBi)
                         for theta in theta_range])
        return gains


class RISReflectionModel:
    """RIS element-level reflection model"""

    def __init__(self, N: int, bits: int, center_freq: float,
                 coupling_enabled: bool = True):
        """
        Initialize RIS reflection model

        Args:
            N: Grid size (N×N elements)
            bits: Phase quantization bits
            center_freq: Center frequency in Hz
            coupling_enabled: Include mutual coupling
        """
        self.N = N
        self.bits = bits
        self.center_freq = center_freq
        self.num_elements = N * N
        self.wavelength = 3e8 / center_freq

        self.coupling_enabled = coupling_enabled
        self._init_coupling_matrix()

        # Phase states
        self.current_phases = np.zeros(self.num_elements)  # radians
        self.quantized_phases = np.zeros(self.num_elements)  # radians

    def _init_coupling_matrix(self):
        """Initialize mutual coupling matrix"""
        if not self.coupling_enabled:
            self.coupling_matrix = np.eye(self.num_elements, dtype=complex)
            return

        # Simplified mutual coupling: depends on element spacing
        spacing = 0.5  # wavelengths
        self.coupling_matrix = np.zeros((self.num_elements, self.num_elements), dtype=complex)

        for i in range(self.num_elements):
            for j in range(self.num_elements):
                if i == j:
                    self.coupling_matrix[i, j] = 1.0
                else:
                    # Distance-dependent coupling (simplified)
                    row_i, col_i = i // self.N, i % self.N
                    row_j, col_j = j // self.N, j % self.N
                    dist_sq = (row_i - row_j)**2 + (col_i - col_j)**2

                    # Coupling decreases with distance
                    coupling_coeff = 0.1 * np.exp(-dist_sq / 4)

                    # Phase due to path difference
                    k = 2 * np.pi / self.wavelength
                    path_diff = np.sqrt(dist_sq) * spacing * self.wavelength
                    phase = np.exp(1j * k * path_diff)

                    self.coupling_matrix[i, j] = coupling_coeff * phase

    def set_phase_config(self, phases: np.ndarray):
        """
        Set RIS phase configuration

        Args:
            phases: Ideal phases in radians (num_elements,)
        """
        self.current_phases = phases.copy()
        self.quantize_phases()

    def quantize_phases(self):
        """Quantize phases according to bit resolution"""
        num_states = 2 ** self.bits
        # Quantize to nearest state
        phase_step = 2 * np.pi / num_states
        self.quantized_phases = np.round(self.current_phases / phase_step) * phase_step
        # Wrap to [0, 2π)
        self.quantized_phases = self.quantized_phases % (2 * np.pi)

    def get_reflection_matrix(self) -> np.ndarray:
        """
        Get RIS reflection matrix including coupling

        Returns:
            Reflection matrix (num_elements × num_elements)
        """
        # Diagonal matrix of phase shifts
        phase_diag = np.diag(np.exp(1j * self.quantized_phases))

        # Apply coupling
        if self.coupling_enabled:
            return self.coupling_matrix @ phase_diag @ self.coupling_matrix
        else:
            return phase_diag

    def reflect_waveform(self, incident_field: np.ndarray) -> np.ndarray:
        """
        Reflect incident waveform

        Args:
            incident_field: Incident field at RIS elements (num_elements, num_samples)

        Returns:
            Reflected field (num_elements, num_samples)
        """
        num_samples = incident_field.shape[1]
        reflected = np.zeros_like(incident_field)

        for sample_idx in range(num_samples):
            incident_sample = incident_field[:, sample_idx]

            # Apply RIS transformation with coupling
            reflected_sample = self.get_reflection_matrix() @ incident_sample
            reflected[:, sample_idx] = reflected_sample

        return reflected


class OFDMReceiver:
    """OFDM receiver with channel estimation"""

    def __init__(self, config: OFDMConfig):
        """
        Initialize OFDM receiver

        Args:
            config: OFDM configuration
        """
        self.config = config

    def remove_cp_and_fft(self, signal_rx: np.ndarray) -> np.ndarray:
        """
        Remove cyclic prefix and perform FFT

        Args:
            signal_rx: Received time-domain signal

        Returns:
            Frequency-domain symbols (num_symbols, num_subcarriers)
        """
        samples_per_symbol = self.config.samples_per_symbol
        samples_cp = self.config.samples_cp
        N = self.config.num_subcarriers

        num_symbols = len(signal_rx) // (samples_per_symbol + samples_cp)
        freq_symbols = np.zeros((num_symbols, N), dtype=complex)

        idx = 0
        for sym_idx in range(num_symbols):
            # Skip CP
            idx += samples_cp

            # Extract symbol and resample if needed
            symbol_samples = signal_rx[idx:idx + samples_per_symbol]
            if len(symbol_samples) != N:
                symbol_samples = signal.resample(symbol_samples, N)

            # FFT
            freq_symbols[sym_idx] = np.fft.fft(symbol_samples) / N
            idx += samples_per_symbol

        return freq_symbols

    def estimate_channel(self, freq_symbols_rx: np.ndarray,
                        pilot_indices: np.ndarray,
                        freq_symbols_tx: np.ndarray) -> np.ndarray:
        """
        Estimate channel from pilots

        Args:
            freq_symbols_rx: Received frequency symbols
            pilot_indices: Indices of pilot subcarriers
            freq_symbols_tx: Transmitted frequency symbols

        Returns:
            Estimated channel (num_symbols, num_subcarriers)
        """
        num_symbols, num_subcarriers = freq_symbols_rx.shape
        channel_est = np.zeros((num_symbols, num_subcarriers), dtype=complex)

        for sym_idx in range(num_symbols):
            # Estimate at pilot subcarriers
            h_pilots = freq_symbols_rx[sym_idx, pilot_indices] / \
                      freq_symbols_tx[sym_idx, pilot_indices]

            # Interpolate to all subcarriers (simple linear)
            channel_est[sym_idx] = np.interp(
                np.arange(num_subcarriers),
                pilot_indices,
                h_pilots,
                left=h_pilots[0],
                right=h_pilots[-1]
            )

        return channel_est

    def equalize(self, freq_symbols_rx: np.ndarray,
                channel_est: np.ndarray) -> np.ndarray:
        """
        Equalize received symbols using ZF (Zero-Forcing)

        Args:
            freq_symbols_rx: Received frequency symbols
            channel_est: Estimated channel

        Returns:
            Equalized symbols
        """
        # Simple ZF: divide by channel estimate
        eps = 1e-10
        equalized = freq_symbols_rx / (channel_est + eps)
        return equalized

    def calculate_snr(self, signal: np.ndarray, noise_power: float) -> float:
        """
        Calculate SNR from waveform

        Args:
            signal: Signal samples
            noise_power: Noise power

        Returns:
            SNR in dB (clipped to reasonable range [-120, 120] dB)
        """
        signal_power = np.mean(np.abs(signal)**2)
        noise_power = np.clip(noise_power, 1e-20, np.inf)  # Guard against zero

        if signal_power <= 1e-20:
            return -120.0  # Minimum SNR

        snr_linear = signal_power / noise_power
        snr_linear = np.clip(snr_linear, 1e-12, 1e12)  # Clamp to reasonable range
        snr_dB = 10 * np.log10(snr_linear)

        # Final clipping to avoid extreme values
        return np.clip(snr_dB, -120.0, 120.0)


# Utility functions
def calculate_effective_snr(signal_rx: np.ndarray,
                           config: OFDMConfig,
                           channel_est: np.ndarray,
                           pilot_indices: np.ndarray) -> float:
    """
    Calculate effective SNR considering waveform and equalization

    Args:
        signal_rx: Received signal
        config: OFDM configuration
        channel_est: Estimated channel response
        pilot_indices: Pilot subcarrier indices

    Returns:
        Effective SNR in dB
    """
    receiver = OFDMReceiver(config)
    freq_symbols = receiver.remove_cp_and_fft(signal_rx)

    # Noise is reflected in estimation error at pilots
    pilot_error = np.abs(channel_est[:, pilot_indices])**2
    noise_estimate = np.mean(1.0 / (pilot_error + 1e-10))

    signal_power = np.mean(np.abs(freq_symbols)**2)
    snr_eff = 10 * np.log10(signal_power / noise_estimate)

    return snr_eff


def calculate_papr(signal: np.ndarray) -> float:
    """
    Calculate Peak-to-Average Power Ratio

    Args:
        signal: Complex signal

    Returns:
        PAPR in dB
    """
    peak_power = np.max(np.abs(signal)**2)
    avg_power = np.mean(np.abs(signal)**2)
    papr_linear = peak_power / avg_power
    return 10 * np.log10(papr_linear)
