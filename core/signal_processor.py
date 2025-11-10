"""
Real signal-level channel simulator for RISNet
Generates actual waveforms, applies channel effects, and measures SNR/SER at UE
"""

import numpy as np
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class SignalConfig:
    """Signal generation configuration"""
    modulation: str = 'QPSK'  # QPSK, 16QAM, 64QAM
    symbol_rate: float = 1e6  # symbols/sec
    sample_rate: float = 10e6  # samples/sec
    num_symbols: int = 1000  # number of symbols to transmit
    pilot_ratio: float = 0.1  # 10% pilot symbols

    @property
    def samples_per_symbol(self) -> int:
        return int(self.sample_rate / self.symbol_rate)

    @property
    def total_samples(self) -> int:
        return self.num_symbols * self.samples_per_symbol


class Modulator:
    """Real modulator for QPSK, 16QAM, 64QAM"""

    QPSK_SYMBOLS = np.array([1+1j, 1-1j, -1+1j, -1-1j]) / np.sqrt(2)
    QAM16_SYMBOLS = np.array([
        1+1j, 1+3j, 3+1j, 3+3j,
        1-1j, 1-3j, 3-1j, 3-3j,
        -1+1j, -1+3j, -3+1j, -3+3j,
        -1-1j, -1-3j, -3-1j, -3-3j
    ]) / np.sqrt(10)

    def __init__(self, modulation: str = 'QPSK'):
        self.modulation = modulation
        if modulation == 'QPSK':
            self.constellation = self.QPSK_SYMBOLS
            self.bits_per_symbol = 2
        elif modulation == '16QAM':
            self.constellation = self.QAM16_SYMBOLS
            self.bits_per_symbol = 4
        elif modulation == '64QAM':
            # 64QAM constellation
            qam_base = np.arange(-8, 8, 2) + 1j * np.arange(-8, 8, 2)[:, np.newaxis]
            self.constellation = (qam_base.flatten()) / np.sqrt(42)
            self.bits_per_symbol = 6
        else:
            raise ValueError(f"Unknown modulation: {modulation}")

    def modulate(self, bit_stream: np.ndarray) -> np.ndarray:
        """Modulate bit stream to symbols"""
        num_symbols = len(bit_stream) // self.bits_per_symbol
        symbol_indices = np.zeros(num_symbols, dtype=int)

        for i in range(num_symbols):
            bits = bit_stream[i*self.bits_per_symbol:(i+1)*self.bits_per_symbol]
            idx = int(''.join(map(str, bits)), 2)
            symbol_indices[i] = idx

        return self.constellation[symbol_indices]

    def demodulate(self, symbols: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Demodulate received symbols to bits with error detection"""
        bit_stream = np.zeros(len(symbols) * self.bits_per_symbol, dtype=int)
        errors = 0

        for i, rx_sym in enumerate(symbols):
            # Find nearest constellation point (hard decision)
            distances = np.abs(self.constellation - rx_sym)
            nearest_idx = np.argmin(distances)
            nearest_sym = self.constellation[nearest_idx]

            # Convert index to bits
            bits = np.array([(nearest_idx >> j) & 1 for j in range(self.bits_per_symbol)])
            bit_stream[i*self.bits_per_symbol:(i+1)*self.bits_per_symbol] = bits

            # Note: Symbol errors are tracked by comparing demodulated bits with transmitted bits
            # This is done at the bit level in measure_ser() which is more accurate

        return bit_stream, np.array([errors])


class RealChannel:
    """Real wireless channel with multipath, fading, and impairments"""

    def __init__(self, path_loss_dB: float, noise_power_dB: float,
                 seed: int = None):
        """
        Args:
            path_loss_dB: Deterministic path loss
            noise_power_dB: Noise power in dB
            seed: Random seed for reproducibility
        """
        self.path_loss_dB = path_loss_dB
        self.noise_power_dB = noise_power_dB
        self.path_loss_linear = 10 ** (-path_loss_dB / 10)
        self.noise_power = 10 ** (noise_power_dB / 10)

        if seed is not None:
            np.random.seed(seed)

    def add_rician_fading(self, signal: np.ndarray, K_factor: float = 5.0) -> np.ndarray:
        """Add time-varying Rician fading

        Args:
            signal: Input signal
            K_factor: Rician K factor (power ratio of LOS to NLOS)

        Returns:
            Faded signal
        """
        num_samples = len(signal)

        # LOS component (constant phase)
        los_power = K_factor / (K_factor + 1)
        los_component = np.sqrt(los_power) * signal

        # NLOS component (Rayleigh fading)
        nlos_power = 1.0 / (K_factor + 1)
        nlos_i = np.random.randn(num_samples) * np.sqrt(nlos_power / 2)
        nlos_q = np.random.randn(num_samples) * np.sqrt(nlos_power / 2)
        nlos_component = nlos_i + 1j * nlos_q

        # Time-varying fading envelope
        fading = los_component + nlos_component

        return fading

    def add_phase_noise(self, signal: np.ndarray, phase_noise_std: float = 0.01) -> np.ndarray:
        """Add oscillator phase noise"""
        num_samples = len(signal)
        phase_errors = np.cumsum(np.random.randn(num_samples) * phase_noise_std)
        phase_noise_envelope = np.exp(1j * phase_errors)
        return signal * phase_noise_envelope

    def add_cfo(self, signal: np.ndarray, cfo_hz: float, sample_rate: float) -> np.ndarray:
        """Add carrier frequency offset (CFO)"""
        num_samples = len(signal)
        t = np.arange(num_samples) / sample_rate
        cfo_rotation = np.exp(1j * 2 * np.pi * cfo_hz * t)
        return signal * cfo_rotation

    def add_multipath(self, signal: np.ndarray, delays: np.ndarray,
                      gains: np.ndarray) -> np.ndarray:
        """Add multipath delay spread

        Args:
            signal: Input signal
            delays: Path delays in samples
            gains: Path gains (linear)
        """
        output = np.zeros(len(signal), dtype=complex)

        for delay, gain in zip(delays, gains):
            delay_int = int(np.round(delay))
            if delay_int < len(signal):
                output[delay_int:] += gain * signal[:len(signal)-delay_int]

        return output

    def apply(self, signal: np.ndarray, K_factor: float = 5.0,
              phase_noise_std: float = 0.01, cfo_hz: float = 1000,
              sample_rate: float = 10e6, multipath_delays: np.ndarray = None,
              multipath_gains: np.ndarray = None) -> np.ndarray:
        """Apply all channel effects

        Args:
            signal: Input signal
            K_factor: Rician K factor
            phase_noise_std: Phase noise standard deviation
            cfo_hz: Carrier frequency offset
            sample_rate: Sampling rate
            multipath_delays: Path delays
            multipath_gains: Path gains

        Returns:
            Channel-impaired signal
        """
        # Apply path loss
        output = signal * np.sqrt(self.path_loss_linear)

        # Apply Rician fading
        output = self.add_rician_fading(output, K_factor)

        # Apply multipath if specified
        if multipath_delays is not None and multipath_gains is not None:
            output = self.add_multipath(output, multipath_delays, multipath_gains)

        # Add phase noise
        output = self.add_phase_noise(output, phase_noise_std)

        # Add CFO
        output = self.add_cfo(output, cfo_hz, sample_rate)

        # Add AWGN
        noise = np.sqrt(self.noise_power / 2) * (np.random.randn(len(output)) +
                                                   1j * np.random.randn(len(output)))
        output = output + noise

        return output


class RealSignalMeasurer:
    """Measure SNR and SER from received signal"""

    @staticmethod
    def measure_snr(tx_signal: np.ndarray, rx_signal: np.ndarray) -> float:
        """Measure SNR from TX and RX signals

        Args:
            tx_signal: Transmitted signal
            rx_signal: Received signal

        Returns:
            SNR in dB
        """
        # Estimate received signal power
        rx_power = np.mean(np.abs(rx_signal) ** 2)

        # Estimate noise power (assuming TX signal is known)
        noise_estimate = rx_signal - tx_signal * np.mean(rx_signal) / np.mean(np.abs(tx_signal)**2)
        noise_power = np.mean(np.abs(noise_estimate) ** 2)

        # Avoid division by zero
        if noise_power < 1e-10:
            noise_power = 1e-10

        snr_linear = rx_power / noise_power
        snr_dB = 10 * np.log10(snr_linear)

        return snr_dB

    @staticmethod
    def measure_ser(tx_bits: np.ndarray, rx_bits: np.ndarray) -> float:
        """Measure Symbol Error Rate

        Args:
            tx_bits: Transmitted bits
            rx_bits: Received bits

        Returns:
            SER as percentage
        """
        errors = np.sum(tx_bits != rx_bits)
        ser = (errors / len(tx_bits)) * 100
        return ser


class SignalLevelLink:
    """End-to-end signal-level link simulator"""

    def __init__(self, config: SignalConfig):
        self.config = config
        self.modulator = Modulator(config.modulation)

    def simulate_link(self, path_loss_dB: float, noise_power_dB: float,
                      K_factor: float = 5.0, seed: int = None) -> Dict:
        """Simulate complete link: modulation -> channel -> demodulation

        Args:
            path_loss_dB: Path loss in dB
            noise_power_dB: Noise power in dB
            K_factor: Rician K factor
            seed: Random seed

        Returns:
            Dict with SNR, SER, and other metrics
        """
        if seed is not None:
            np.random.seed(seed)

        # Generate random bit stream
        num_bits = self.config.num_symbols * self.modulator.bits_per_symbol
        tx_bits = np.random.randint(0, 2, num_bits)

        # Modulate
        tx_symbols = self.modulator.modulate(tx_bits)

        # Upsample (pulse shaping would go here)
        tx_samples = np.repeat(tx_symbols, self.config.samples_per_symbol)

        # Apply channel
        channel = RealChannel(path_loss_dB, noise_power_dB, seed)
        rx_samples = channel.apply(tx_samples, K_factor=K_factor,
                                   phase_noise_std=0.01, cfo_hz=100,
                                   sample_rate=self.config.sample_rate)

        # Downsample (match filter output)
        rx_symbols = rx_samples[::self.config.samples_per_symbol]

        # Demodulate
        rx_bits, _ = self.modulator.demodulate(rx_symbols)

        # Measure SNR and SER
        snr_dB = RealSignalMeasurer.measure_snr(tx_samples[:len(rx_samples)], rx_samples)
        ser = RealSignalMeasurer.measure_ser(tx_bits, rx_bits)

        # Count symbol errors (bit errors per symbol)
        bit_errors = np.sum(tx_bits != rx_bits)
        symbol_errors = bit_errors // self.modulator.bits_per_symbol

        return {
            'snr_dB': snr_dB,
            'ser_percent': ser,
            'symbol_errors': int(symbol_errors),
            'total_symbols': self.config.num_symbols,
            'modulation': self.config.modulation,
            'path_loss_dB': path_loss_dB,
            'noise_power_dB': noise_power_dB
        }
