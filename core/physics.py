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
    def quantization_loss_dB(phase_bits, element_efficiency=0.95, model='standard'):
        """Quantization loss due to finite phase resolution

        Args:
            phase_bits: Number of quantization bits
            element_efficiency: Element amplitude efficiency (0-1)
            model: 'standard' (uniform quantization theory) or 'legacy' (original RISNet)

        Returns:
            Quantization loss in dB

        References:
            - Brookner, "Phased Array Handbook" (standard model)
            - Original RISNet formula for backward compatibility
        """
        if phase_bits == 0:
            return 0.0

        num_levels = 2 ** phase_bits

        if model == 'standard':
            # Standard uniform quantization theory
            # Phase step: 2π / 2^b radians
            phase_step = 2 * np.pi / num_levels

            # RMS quantization error for uniform distribution: Δφ / √12
            quantization_error_rms = phase_step / (2 * np.sqrt(3))

            # Directivity loss from quantization using sinc function
            # Loss = sinc²(error_rms / π)
            sinc_arg = quantization_error_rms / np.pi
            directivity_factor = np.sinc(sinc_arg) ** 2

            # Apply element efficiency (amplitude loss, converted to power)
            efficiency_factor = element_efficiency ** 2

            # Combined loss (negative dB = loss)
            combined_factor = directivity_factor * efficiency_factor

            loss_dB = 10 * np.log10(combined_factor)

            return loss_dB

        else:  # 'legacy' - original RISNet formula
            # Original formula for backward compatibility
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
    def quantization_loss_with_state(phase_bits, phase_state_fraction,
                                     element_efficiency=0.95, model='standard'):
        """Quantization loss with state-dependent variation

        Real phase shifters have different insertion loss for each state.
        This models the variation based on the phase state.

        Args:
            phase_bits: Number of quantization bits
            phase_state_fraction: Current state as fraction [0, 1]
                                 (0.0 = 0°, 0.5 = 180°, etc.)
            element_efficiency: Base element efficiency (0-1)
            model: 'standard' or 'legacy'

        Returns:
            Quantization loss in dB

        Example:
            For 2-bit shifter in state 0 (0°): loss ≈ -0.5 dB
            For 2-bit shifter in state 2 (180°): loss ≈ -1.0 dB
        """
        base_loss = Physics.quantization_loss_dB(phase_bits, element_efficiency, model)

        # State-dependent variation (typical for real phase shifters)
        # Loss varies between states due to different reflection coefficients
        num_states = 2 ** phase_bits
        state_idx = int(phase_state_fraction * num_states) % num_states

        # Even/odd state variation (empirical model from real hardware)
        # Typically: state 0,1 have lower loss, state 2,3 have higher loss
        state_variation = 0.2 * (state_idx % 2)  # ±0.2 dB variation

        return base_loss + state_variation

    @staticmethod
    def phase_error_per_element(element_idx, num_elements, phase_bits,
                               include_quantization=True,
                               include_manufacturing=True,
                               include_temperature=True,
                               mfg_std_deg=8.0,
                               temp_std_deg=5.0,
                               seed=None):
        """Compute per-element phase error including realistic imperfections

        Args:
            element_idx: Element index
            num_elements: Total number of elements
            phase_bits: Phase quantization bits
            include_quantization: Include quantization error
            include_manufacturing: Include manufacturing tolerance
            include_temperature: Include temperature variation
            mfg_std_deg: Manufacturing tolerance std dev (degrees)
            temp_std_deg: Temperature drift std dev (degrees)
            seed: Random seed for reproducibility

        Returns:
            Total phase error in radians

        Notes:
            - Quantization error: ±π/(2^bits)
            - Manufacturing tolerance: typically ±5-15° (default: ±8°)
            - Temperature drift: typically ±0.5°/°C for ΔT (default: ±5° for 10°C)
        """
        if seed is not None:
            np.random.seed(seed + element_idx)

        total_error = 0.0

        # Quantization error (uniform distribution)
        if include_quantization and phase_bits > 0:
            quantization_bound = np.pi / (2 ** phase_bits)
            quant_error = np.random.uniform(-quantization_bound / 2, quantization_bound / 2)
            total_error += quant_error

        # Manufacturing tolerance (normal distribution)
        if include_manufacturing:
            mfg_error = np.random.normal(0, np.radians(mfg_std_deg))
            total_error += mfg_error

        # Temperature drift (normal distribution)
        if include_temperature:
            temp_error = np.random.normal(0, np.radians(temp_std_deg))
            total_error += temp_error

        return total_error

    @staticmethod
    def quantize_phase_to_bits(ideal_phase_rad, phase_bits):
        """Quantize ideal phase to discrete level

        Args:
            ideal_phase_rad: Ideal phase in radians [0, 2π]
            phase_bits: Number of phase quantization bits

        Returns:
            Quantized phase in radians
        """
        if phase_bits == 0:
            return ideal_phase_rad

        num_levels = 2 ** phase_bits
        phase_step = 2 * np.pi / num_levels

        # Round to nearest quantization level
        quantized = np.round(ideal_phase_rad / phase_step) * phase_step

        return np.mod(quantized, 2 * np.pi)

    @staticmethod
    def compute_quantized_beam_angle(ideal_angle_deg, phase_bits, ris_elements):
        """Find achievable beam angle with phase quantization

        When phase shifters have limited quantization bits, only certain
        discrete beam angles can be achieved.

        Args:
            ideal_angle_deg: Target beam angle (degrees)
            phase_bits: Phase quantization bits
            ris_elements: Number of elements in linear array

        Returns:
            (achievable_angle_deg, quantization_error_deg)
        """
        if phase_bits == 0:
            return ideal_angle_deg, 0.0

        num_levels = 2 ** phase_bits
        phase_step = 2 * np.pi / num_levels

        # For linear array, beam angle relates to phase gradient
        # d*sin(θ) = λ*Δφ/(2π)
        # Minimum resolvable angle change for 1 element spacing (λ/2)
        min_angle_step = np.degrees(2 * phase_step / (2 * np.pi))

        # Quantize angle to achievable values
        achievable = np.round(ideal_angle_deg / min_angle_step) * min_angle_step

        error = ideal_angle_deg - achievable

        return achievable, error

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
