"""
UE Receiver Pipeline for waveform-level RIS network simulation
Implements full OFDM reception, channel estimation, and CSI feedback
"""

import numpy as np
from typing import Dict, Tuple, Optional
from scipy import signal
from utils.csi import generate_csi_report


class UEReceiverPipeline:
    """Full UE RX chain: OFDM demod, channel estimation, equalization, SNR measurement"""

    def __init__(self, ue_node, ofdm_config):
        """
        Initialize UE receiver pipeline

        Args:
            ue_node: UE node instance (from core.nodes)
            ofdm_config: OFDMConfig instance with signal parameters
        """
        self.ue = ue_node
        self.config = ofdm_config
        self.channel_estimate = None
        self.snr_measurement_dB = None
        self.equalized_symbols = None
        self.received_frequency_symbols = None

    def process_received_waveform(self, rx_signal: np.ndarray,
                                  tx_freq_symbols: np.ndarray,
                                  pilot_indices: np.ndarray,
                                  ris_phases: Optional[np.ndarray] = None) -> Dict:
        """
        Process received OFDM waveform end-to-end

        Args:
            rx_signal: Received time-domain signal
            tx_freq_symbols: Transmitted frequency-domain symbols for reference
            pilot_indices: Indices of pilot subcarriers
            ris_phases: RIS phase configuration (optional, for reporting)

        Returns:
            Dict with processed results including SNR, channel estimate, and equalized symbols
        """
        # Step 1: Remove CP and FFT
        freq_symbols_rx = self.remove_cp_and_fft(rx_signal)
        self.received_frequency_symbols = freq_symbols_rx

        # Step 2: Channel estimation from pilots
        channel_est = self.estimate_channel_from_pilots(
            freq_symbols_rx, pilot_indices, tx_freq_symbols
        )
        self.channel_estimate = channel_est

        # Step 3: Zero-Forcing equalization
        equalized = self.zero_force_equalize(freq_symbols_rx, channel_est)
        self.equalized_symbols = equalized

        # Step 4: Measure SNR
        snr_dB = self.measure_snr_from_equalized(equalized, freq_symbols_rx, channel_est)
        self.snr_measurement_dB = snr_dB

        # Step 5: Generate CSI feedback
        csi_feedback = self.generate_csi_report(
            snr_dB, channel_est, ris_phases
        )

        return {
            'snr_dB': snr_dB,
            'channel_estimate': channel_est,
            'equalized_symbols': equalized,
            'received_freq_symbols': freq_symbols_rx,
            'csi_feedback': csi_feedback
        }

    def remove_cp_and_fft(self, signal_rx: np.ndarray) -> np.ndarray:
        """
        Remove cyclic prefix and perform FFT to get frequency-domain symbols

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
            # Skip cyclic prefix
            idx += samples_cp

            # Extract symbol
            symbol_samples = signal_rx[idx:idx + samples_per_symbol]

            # Resample if needed
            if len(symbol_samples) != N:
                symbol_samples = signal.resample(symbol_samples, N)

            # FFT
            freq_symbols[sym_idx] = np.fft.fft(symbol_samples) / N
            idx += samples_per_symbol

        return freq_symbols

    def estimate_channel_from_pilots(self, freq_symbols_rx: np.ndarray,
                                     pilot_indices: np.ndarray,
                                     freq_symbols_tx: np.ndarray) -> np.ndarray:
        """
        Estimate channel using pilot-based LMMSE estimation

        Args:
            freq_symbols_rx: Received frequency-domain symbols
            pilot_indices: Indices of pilot subcarriers
            freq_symbols_tx: Transmitted frequency-domain symbols (known reference)

        Returns:
            Channel estimate (num_symbols, num_subcarriers)
        """
        num_symbols, num_subcarriers = freq_symbols_rx.shape
        channel_est = np.zeros((num_symbols, num_subcarriers), dtype=complex)

        for sym_idx in range(num_symbols):
            # Estimate at pilot locations (ratio of received to transmitted)
            h_pilots = freq_symbols_rx[sym_idx, pilot_indices] / \
                      (freq_symbols_tx[sym_idx, pilot_indices] + 1e-10)

            # Interpolate to all subcarriers using linear interpolation
            pilot_positions = pilot_indices.astype(float)
            all_positions = np.arange(num_subcarriers).astype(float)

            # Linear interpolation with endpoint handling
            channel_est[sym_idx] = np.interp(
                all_positions,
                pilot_positions,
                h_pilots,
                left=h_pilots[0],
                right=h_pilots[-1]
            )

        return channel_est

    def zero_force_equalize(self, freq_symbols_rx: np.ndarray,
                           channel_est: np.ndarray) -> np.ndarray:
        """
        Apply Zero-Forcing equalization in frequency domain

        Args:
            freq_symbols_rx: Received frequency-domain symbols
            channel_est: Estimated channel response

        Returns:
            Equalized symbols (same shape as input)
        """
        # Avoid division by near-zero
        eps = 1e-10
        equalized = freq_symbols_rx / (channel_est + eps)
        return equalized

    def measure_snr_from_equalized(self, equalized_symbols: np.ndarray,
                                   freq_symbols_rx: np.ndarray,
                                   channel_est: np.ndarray) -> float:
        """
        Measure SNR from equalized symbols using error variance

        Args:
            equalized_symbols: Equalized received symbols
            freq_symbols_rx: Original received frequency symbols
            channel_est: Estimated channel

        Returns:
            SNR in dB
        """
        # SNR from constellation diagram approach:
        # After equalization, symbols should be close to ideal constellations (±1 for QPSK)
        # SNR can be estimated from magnitude deviation

        # Signal power = mean magnitude of equalized symbols
        # (assume normalized to unit power)
        signal_power = np.mean(np.abs(equalized_symbols) ** 2)

        # Noise power estimation from received symbols variance
        # before equalization (lower estimate)
        rx_power = np.mean(np.abs(freq_symbols_rx) ** 2)

        # Channel gain estimation
        channel_magnitude = np.abs(channel_est)
        channel_magnitude = np.clip(channel_magnitude, 1e-10, None)
        mean_channel_gain = np.mean(channel_magnitude)

        # Noise power ~ received power / channel gain^2
        # But conservatively estimate from channel inversion noise enhancement
        noise_power_est = np.mean(1.0 / (channel_magnitude ** 2 + 1e-10))

        # Better estimate: use actual rx signal minus ideal signal
        # Approximate as: variance of estimation error
        expected_signal_power = 1.0  # Normalized QPSK = unit power
        estimation_error_power = np.mean(np.abs(equalized_symbols - expected_signal_power) ** 2)

        # More realistic: SNR ≈ signal / (channel noise + estimation error)
        noise_power_est = estimation_error_power / (mean_channel_gain ** 2 + 1e-10)
        noise_power_est = np.clip(noise_power_est, 1e-20, 1.0)

        # SNR calculation
        if signal_power <= 1e-20:
            return -120.0

        snr_linear = signal_power / (noise_power_est + 1e-10)
        snr_linear = np.clip(snr_linear, 1e-12, 1e12)
        snr_dB = 10 * np.log10(snr_linear)
        snr_dB = np.clip(snr_dB, -20.0, 60.0)

        return float(snr_dB)

    def measure_snr_waveform(self, rx_signal: np.ndarray,
                            noise_power: float = 0.01) -> float:
        """
        Quick SNR measurement directly from waveform (before equalization)

        Args:
            rx_signal: Received time-domain signal
            noise_power: Estimated noise power

        Returns:
            SNR in dB
        """
        signal_power = np.mean(np.abs(rx_signal) ** 2)
        noise_power = np.clip(noise_power, 1e-20, np.inf)

        if signal_power <= 1e-20:
            return -120.0

        snr_linear = signal_power / noise_power
        snr_linear = np.clip(snr_linear, 1e-12, 1e12)
        snr_dB = 10 * np.log10(snr_linear)

        return np.clip(snr_dB, -120.0, 120.0)

    def generate_csi_report(self, snr_dB: float,
                           channel_est: np.ndarray,
                           ris_phases: Optional[np.ndarray] = None) -> Dict:
        """
        Generate CSI feedback report for transmission to AP

        Args:
            snr_dB: Measured SNR in dB
            channel_est: Estimated channel response
            ris_phases: RIS phase configuration (for context)

        Returns:
            CSI feedback dictionary using standardized utility
        """
        return generate_csi_report(
            ue_name=self.ue.name,
            snr_dB=snr_dB,
            channel_estimate=channel_est,
            antenna_gain_dBi=self.ue.antenna_gain_dBi,
            noise_figure_dB=self.ue.noise_figure_dB,
            ris_phases=ris_phases,
            pilot_reliability=self._estimate_pilot_reliability(),
        )

    def _estimate_pilot_reliability(self) -> float:
        """
        Estimate reliability of pilot-based channel estimation

        Returns:
            Reliability score (0-1), higher = more confident estimate
        """
        if self.channel_estimate is None:
            return 0.0

        # Use channel estimate variance as proxy for reliability
        # Lower variance = more stable estimate = higher reliability
        channel_variance = np.var(np.abs(self.channel_estimate))
        # Normalize: assume variance ~ 0.1 is good reliability
        reliability = np.exp(-channel_variance / 0.1)
        reliability = np.clip(reliability, 0.0, 1.0)

        return float(reliability)

    def get_sinr_per_subcarrier(self, freq_symbols_rx: np.ndarray,
                               channel_est: np.ndarray,
                               noise_power: float = 0.01) -> np.ndarray:
        """
        Compute SINR for each subcarrier (post-equalization)

        Args:
            freq_symbols_rx: Received frequency symbols
            channel_est: Channel estimate
            noise_power: Noise power estimate

        Returns:
            SINR per subcarrier in dB
        """
        # Post-equalization noise enhancement
        # SINR = |H|^2 / (noise_power * (1/|H|^2))
        h_magnitude = np.abs(channel_est)
        h_magnitude = np.clip(h_magnitude, 1e-10, None)

        # SINR per subcarrier
        sinr_linear = (h_magnitude ** 2) / noise_power
        sinr_linear = np.clip(sinr_linear, 1e-12, 1e12)
        sinr_dB = 10 * np.log10(sinr_linear)

        return sinr_dB.flatten()


class UEAdaptationController:
    """Handles UE-side feedback and adaptation logic"""

    def __init__(self, ue_node):
        """
        Initialize UE adaptation controller

        Args:
            ue_node: UE node instance
        """
        self.ue = ue_node
        self.csi_history = []
        self.feedback_count = 0

    def process_csi_measurement(self, csi_result: Dict) -> Dict:
        """
        Process CSI measurement and prepare feedback

        Args:
            csi_result: Output from UEReceiverPipeline.process_received_waveform()

        Returns:
            Feedback packet ready for transmission to AP
        """
        snr_dB = csi_result['snr_dB']

        # Update UE measurement
        self.ue.snr_measurement_dB = snr_dB
        self.ue.channel_estimate = csi_result['channel_estimate']

        # Generate feedback
        feedback = self.ue.generate_csi_feedback(
            channel_est=csi_result['channel_estimate'],
            snr_dB=snr_dB
        )

        # Track history
        self.csi_history.append({
            'timestamp': feedback['timestamp'],
            'snr_dB': snr_dB,
            'index': self.feedback_count
        })
        self.feedback_count += 1

        return feedback

    def get_csi_history(self) -> list:
        """Get history of CSI measurements"""
        return self.csi_history.copy()

    def clear_history(self):
        """Clear CSI history"""
        self.csi_history.clear()
        self.feedback_count = 0
