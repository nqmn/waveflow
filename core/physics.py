"""
Physics and propagation models for RIS simulation
"""
import numpy as np
import math

# Physical constants
C = 3e8  # Speed of light (m/s)

class Physics:
    """Centralized physics calculations for RIS networks"""

    @staticmethod
    def path_loss_dB(distance, freq):
        """Free space path loss (FSPL) in dB

        Args:
            distance: Distance in meters
            freq: Frequency in Hz

        Returns:
            Path loss in dB
        """
        if distance <= 0:
            return 0.0
        return 20 * np.log10(4 * np.pi * distance * freq / C)

    @staticmethod
    def atmospheric_loss_dB(distance, freq_GHz):
        """Atmospheric absorption loss

        Args:
            distance: Distance in meters
            freq_GHz: Frequency in GHz

        Returns:
            Atmospheric loss in dB
        """
        alpha = 0.00001  # Default attenuation coefficient

        if freq_GHz >= 10 and freq_GHz < 24:
            alpha = 0.0001 + (freq_GHz - 10) * 0.00002
        elif freq_GHz >= 24 and freq_GHz < 50:
            alpha = 0.0003 + (freq_GHz - 24) * 0.00015
        elif freq_GHz >= 57 and freq_GHz <= 64:
            # Oxygen absorption peak around 60 GHz
            peak_factor = 1 - abs(freq_GHz - 60) / 3
            alpha = 0.005 + peak_factor * 0.010
        elif freq_GHz > 64:
            alpha = 0.003 + (freq_GHz - 64) * 0.00005

        return alpha * distance

    @staticmethod
    def rician_fading(K_factor_dB, size=1):
        """Rician fading channel model

        Args:
            K_factor_dB: Rician K-factor in dB
            size: Number of samples

        Returns:
            Fading coefficient magnitude
        """
        K_linear = 10 ** (K_factor_dB / 10)
        los_component = np.sqrt(K_linear / (K_linear + 1))
        scatter_std = np.sqrt(1 / (K_linear + 1))
        scatter = scatter_std * (np.random.randn(size) + 1j * np.random.randn(size)) / np.sqrt(2)
        h = los_component + scatter
        return np.abs(h)

    @staticmethod
    def quantization_loss_dB(phase_bits, element_efficiency=0.95):
        """Quantization loss due to finite phase resolution

        Args:
            phase_bits: Number of quantization bits
            element_efficiency: Element amplitude efficiency (0-1)

        Returns:
            Quantization loss in dB
        """
        if phase_bits == 0:
            return 0.0

        num_levels = 2 ** phase_bits
        phase_error_rad = np.pi / num_levels
        effective_gain_factor = element_efficiency * np.cos(phase_error_rad / 2)
        return -20 * np.log10(effective_gain_factor)

    @staticmethod
    def mutual_coupling_penalty(spacing_wavelengths, coupling_enabled=True):
        """Mutual coupling penalty between RIS elements

        Args:
            spacing_wavelengths: Element spacing in wavelengths
            coupling_enabled: Whether to apply coupling effects

        Returns:
            Coupling loss in dB
        """
        if not coupling_enabled:
            return 0.0
        if spacing_wavelengths <= 0.5:
            return 2.0
        elif spacing_wavelengths <= 0.7:
            return 1.0
        return 0.0

    @staticmethod
    def compute_ris_phases(target_pos, element_pos, ap_pos, wavelength):
        """Compute ideal RIS reflection phases for beamforming

        Args:
            target_pos: Target position (3D numpy array)
            element_pos: RIS element positions (Nx3 numpy array)
            ap_pos: Access point position (3D numpy array)
            wavelength: Wavelength in meters

        Returns:
            Phase shifts in radians (N-element array)
        """
        k = 2 * np.pi / wavelength
        r_ap = np.linalg.norm(element_pos - ap_pos, axis=1)
        r_tgt = np.linalg.norm(element_pos - target_pos, axis=1)
        ideal_phases = k * (r_ap + r_tgt)
        # Reference to element 0
        ideal_phases = ideal_phases - ideal_phases[0]
        return np.mod(ideal_phases, 2 * np.pi)

    @staticmethod
    def array_gain_dBi(N, amplifier_gain=1.0, insertion_loss_dB=0.5,
                       reflection_loss_dB=0.2, angle_loss_dB=0):
        """Calculate RIS array gain

        Args:
            N: Number of elements
            amplifier_gain: Amplifier gain (linear, 1.0 for passive)
            insertion_loss_dB: Insertion loss per element
            reflection_loss_dB: Reflection loss
            angle_loss_dB: Beam steering angle loss

        Returns:
            Array gain in dBi
        """
        theoretical_gain_dBi = 20 * np.log10(amplifier_gain * N)
        total_gain = theoretical_gain_dBi - insertion_loss_dB - reflection_loss_dB - angle_loss_dB
        return total_gain

    @staticmethod
    def angle_loss_dB(beam_angle_deg, target_angle_deg, sensitivity=0.16):
        """Calculate loss due to beam steering angle deviation

        Args:
            beam_angle_deg: Actual beam steering angle
            target_angle_deg: Target angle
            sensitivity: Loss per degree (dB/degree)

        Returns:
            Angle loss in dB
        """
        angular_deviation = abs(beam_angle_deg - target_angle_deg)
        # Normalize to [-180, 180]
        while angular_deviation > 180:
            angular_deviation = 360 - angular_deviation
        return min(angular_deviation * sensitivity, 12.0)

    @staticmethod
    def compute_snr_dB(tx_power_dBm, total_loss_dB, gain_dBi,
                       bandwidth_MHz, noise_figure_dB=10):
        """Calculate SNR

        Args:
            tx_power_dBm: Transmit power in dBm
            total_loss_dB: Total path loss in dB
            gain_dBi: Antenna/array gain in dBi
            bandwidth_MHz: Signal bandwidth in MHz
            noise_figure_dB: Receiver noise figure in dB

        Returns:
            SNR in dB
        """
        BW_Hz = bandwidth_MHz * 1e6
        noise_power_dBm = -174 + 10 * np.log10(BW_Hz) + noise_figure_dB
        received_power_dBm = tx_power_dBm - total_loss_dB + gain_dBi
        snr_dB = received_power_dBm - noise_power_dBm
        return snr_dB

    @staticmethod
    def snr_to_evm(snr_dB):
        """Convert SNR to EVM percentage

        Args:
            snr_dB: SNR in dB

        Returns:
            EVM in percentage
        """
        snr_linear = 10 ** (snr_dB / 10)
        evm = (1 / np.sqrt(snr_linear)) * 100
        return evm
