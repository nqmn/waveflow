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
            Quantization loss in dB (negative value, e.g., -1.67 dB means subtract 1.67 dB from gain)

        Notes:
            - Return value is NEGATIVE (e.g., -1.67 dB for 1-bit)
            - When used in link budget: Pr = Pt + G - PL - |loss| = Pt + G - PL - loss
            - To use in calculations: subtract the returned value (double negative = add loss)

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
    def compute_array_factor(phases, element_positions, target_angle_deg,
                            frequency, weights=None, ris_position=None,
                            ap_position=None, observation_type='far_field'):
        """Calculate array factor (AF) magnitude for a 2D planar RIS array.

        Array factor models how a phased array antenna radiates in different
        directions. This is the fundamental physics that determines sidelobe
        levels naturally without special-case logic.

        Theory:
            AF(θ, φ) = |∑_n w_n * e^(j*φ_n) * e^(j*k*r_n·θ̂)|
            where:
                w_n = amplitude weight for element n
                φ_n = phase at element n (steering + quantization)
                k = 2π/λ = wave number
                r_n = position vector of element n
                θ̂ = observation direction unit vector

        The result naturally shows:
            - Peak ~0 dB (or N dB if normalized to N) at steering direction
            - Sidelobes at -13 to -30 dB for uniform weights
            - Smooth transition (no artificial cutoff at beam_hits_ue)

        Args:
            phases: Ideal/quantized steering phases (N-element array, radians)
            element_positions: Element positions (N×3 numpy array, meters)
            target_angle_deg: Observation angle in degrees (azimuth in 2D, or elevation)
            frequency: Operating frequency in Hz
            weights: Optional amplitude weights (N-element array, default: ones)
                    Use for tapering to reduce sidelobes (e.g., Hamming window)
            ris_position: RIS center position (3D array, meters). If provided, converts
                         target_angle to 3D observation direction.
            ap_position: AP position (3D array, meters). If provided with ris_position,
                        uses AP→RIS geometry for observation angle reference.
            observation_type: 'far_field' (default) or 'near_field'
                            'far_field': simple angular-based calculation
                            'near_field': uses actual element-target geometry

        Returns:
            array_factor_magnitude_dB: Array factor in dB (normalized to peak)
                                       At steering direction: ~0 dB
                                       At sidelobes: -10 to -30 dB typical
                                       At nulls: -∞ dB (clipped to -60 dB)
        """
        if phases is None or len(phases) == 0:
            return 0.0

        wavelength = C / frequency
        k = 2 * np.pi / wavelength
        num_elements = len(phases)

        # Default weights (uniform, no tapering)
        if weights is None:
            weights = np.ones(num_elements)
        else:
            weights = np.array(weights)

        # Normalize weights to unit energy
        weights = weights / np.sqrt(np.sum(weights ** 2) + 1e-10)

        # Convert target_angle_deg to observation direction vector
        if observation_type == 'far_field':
            # Far-field: use simple angular observation direction
            if ris_position is not None and ap_position is not None:
                # Reference direction: AP→RIS direction
                ap_to_ris = ris_position - ap_position
                ap_to_ris_angle_deg = np.degrees(np.arctan2(ap_to_ris[1], ap_to_ris[0]))
                # Observation angle relative to AP→RIS direction
                obs_angle_deg = ap_to_ris_angle_deg + target_angle_deg
            else:
                obs_angle_deg = target_angle_deg

            # 2D observation direction (assuming elevation=0, azimuth only)
            obs_angle_rad = np.radians(obs_angle_deg)
            observation_dir = np.array([np.cos(obs_angle_rad), np.sin(obs_angle_rad), 0.0])
        else:
            # Near-field: observe from specific position (would be UE position)
            if element_positions.shape[0] == 0:
                return 0.0
            observation_dir = None  # Will be computed per-element

        # Compute array factor
        af_complex = 0.0 + 0.0j

        if observation_type == 'far_field':
            # Far-field array factor: simple phase summation
            for n in range(num_elements):
                # Steering phase
                phase_steering = phases[n]

                # Spatial phase: k·r_n·θ̂
                element_pos = element_positions[n] if isinstance(element_positions, np.ndarray) else element_positions[n]
                if ris_position is not None:
                    element_pos = element_pos - ris_position  # Relative to RIS center

                # Project onto observation direction
                spatial_phase = k * np.dot(element_pos[:2], observation_dir[:2])  # 2D projection

                # Total phase for this element
                total_phase = phase_steering + spatial_phase

                # Contribution to array factor
                af_complex += weights[n] * np.exp(1j * total_phase)

        else:
            # Near-field array factor (would require observation point)
            # For now, fall back to far-field
            for n in range(num_elements):
                phase_steering = phases[n]
                element_pos = element_positions[n]
                if ris_position is not None:
                    element_pos = element_pos - ris_position

                # Approximate near-field using angular observation
                obs_angle_rad = np.radians(target_angle_deg)
                observation_dir = np.array([np.cos(obs_angle_rad), np.sin(obs_angle_rad), 0.0])
                spatial_phase = k * np.dot(element_pos[:2], observation_dir[:2])

                total_phase = phase_steering + spatial_phase
                af_complex += weights[n] * np.exp(1j * total_phase)

        # Array factor magnitude (normalized to number of elements for steered case)
        af_magnitude_linear = np.abs(af_complex) / num_elements

        # Convert to dB (normalized so peak at steering direction ≈ 0 dB)
        # Clamp to avoid log(0)
        af_magnitude_linear = np.clip(af_magnitude_linear, 1e-6, 1.0)
        af_magnitude_dB = 20 * np.log10(af_magnitude_linear)

        # Clamp sidelobe floor to -60 dB (represents far sidelobes)
        af_magnitude_dB = np.clip(af_magnitude_dB, -60.0, 0.0)

        return float(af_magnitude_dB)

    @staticmethod
    def array_gain_dBi(N, amplifier_gain=1.0, insertion_loss_dB=0.5,
                       reflection_loss_dB=0.2, angle_loss_dB=0, frequency=5.8e9):
        """Calculate RIS array gain based on aperture directivity

        Uses aperture-based directivity formula: D = 4π·A_ris / λ²
        This is more realistic than the element-count formula 20*log10(N).

        Args:
            N: Total number of elements (for square array: N_side = sqrt(N))
            amplifier_gain: Amplifier gain (linear, 1.0 for passive)
            insertion_loss_dB: Insertion loss per element
            reflection_loss_dB: Reflection loss
            angle_loss_dB: Beam steering angle loss
            frequency: Operating frequency in Hz (default 5.8 GHz)

        Returns:
            Array gain in dBi
        """
        # Calculate aperture directivity for square RIS panel
        # Assume element spacing λ/2, so for N elements: side_length = sqrt(N) * λ/2
        c = 3e8
        wavelength = c / frequency

        # For N_side × N_side array with λ/2 spacing:
        N_side = np.sqrt(N)
        side_length = N_side * (wavelength / 2.0)
        aperture_area = side_length ** 2

        # Aperture directivity: D = 4π·A / λ²
        directivity_linear = (4 * np.pi * aperture_area) / (wavelength ** 2)
        directivity_dBi = 10 * np.log10(directivity_linear)

        # Apply realistic losses
        # Amplifier gain (only matters for active RIS; passive has gain=1.0)
        amp_gain_dB = 10 * np.log10(amplifier_gain)

        # Total realized gain
        total_gain = directivity_dBi + amp_gain_dB - insertion_loss_dB - reflection_loss_dB - angle_loss_dB
        return total_gain

    @staticmethod
    def angle_loss_dB(beam_angle_deg, target_angle_deg, sensitivity=0.16):
        """Calculate loss due to beam steering angle deviation

        Args:
            beam_angle_deg: Actual beam steering angle
            target_angle_deg: Target angle
            sensitivity: Loss per degree (dB/degree) - UNUSED (kept for compatibility)

        Returns:
            Angle loss in dB
        """
        # Compute shortest angular distance between two angles
        delta = (beam_angle_deg - target_angle_deg) % 360
        if delta > 180:
            angular_deviation = 360 - delta
        else:
            angular_deviation = delta

        # CRITICAL FIX: Use quadratic penalty function instead of sinc
        # Sinc at small angles has floating-point precision issues causing plateaus
        # Quadratic function provides smooth, monotonic loss variation
        # Loss = k * (angular_deviation)^2, where k provides reasonable scaling

        # Loss magnitude: -20 dB at ±60°, -0 dB at 0°
        # This means: loss = -20 * (angular_deviation / 60)^2
        # Or more generally: loss = -a * angular_deviation^2
        # where 'a' is chosen so peak loss = -20 dB at max deviation

        # For ±60° max deviation: a = 20 / (60^2) = 0.00556
        # This gives smooth penalty without artifacts

        a = 20.0 / (60.0 ** 2)  # Scaling factor: -20 dB at ±60°
        loss_dB = -a * (angular_deviation ** 2)

        # Clamp to maximum loss of -30 dB (more than -60° away)
        loss_dB = max(loss_dB, -30.0)

        return loss_dB

    @staticmethod
    def compute_snr_dB(tx_power_dBm, total_loss_dB, gain_dBi,
                       bandwidth_MHz, noise_figure_dB=10):
        """Calculate SNR in dB using unified SNR computation.

        This is a convenience wrapper around utils.compute_snr() for backward compatibility.

        Args:
            tx_power_dBm: Transmit power in dBm
            total_loss_dB: Total path loss in dB
            gain_dBi: Antenna/array gain in dBi
            bandwidth_MHz: Signal bandwidth in MHz
            noise_figure_dB: Receiver noise figure in dB

        Returns:
            SNR in dB
        """
        from utils.snr import compute_snr
        return compute_snr(
            tx_power_dbm=tx_power_dBm,
            total_loss_db=total_loss_dB,
            gain_dbi=gain_dBi,
            bandwidth_mhz=bandwidth_MHz,
            noise_figure_db=noise_figure_dB,
            return_db=True,
        )

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

    # =====================================================================
    # Waveform-Level Physics Functions
    # =====================================================================

    @staticmethod
    def directional_gain_from_position(source_pos, target_pos, array_type='ula',
                                      num_elements=16, element_spacing=0.5,
                                      center_freq=10e9, element_gain_dBi=3.0):
        """Calculate directional antenna gain based on geometry

        Args:
            source_pos: Source position (3D array)
            target_pos: Target position (3D array)
            array_type: 'ula' or 'isotropic'
            num_elements: Number of array elements
            element_spacing: Element spacing in wavelengths
            center_freq: Center frequency in Hz
            element_gain_dBi: Per-element gain in dBi

        Returns:
            Directional gain in dB
        """
        from .waveform import AntennaArray

        wavelength = C / center_freq
        spacing_m = element_spacing * wavelength

        array = AntennaArray(array_type=array_type,
                           num_elements=num_elements,
                           spacing=spacing_m / wavelength,
                           center_freq=center_freq)

        # Direction from source to target
        direction = target_pos - source_pos
        direction_norm = np.linalg.norm(direction)
        if direction_norm == 0:
            return 0.0

        direction_unit = direction / direction_norm

        # Calculate angles (simplified: assuming linear array)
        theta = np.arctan2(direction_unit[2], np.sqrt(direction_unit[0]**2 +
                                                      direction_unit[1]**2))
        phi = np.arctan2(direction_unit[1], direction_unit[0])

        return array.get_directional_gain_dB(theta, phi, element_gain_dBi)

    @staticmethod
    def multipath_ris_gain(paths_info: list, ris_phases: np.ndarray,
                          element_spacing=0.5, center_freq=10e9):
        """Calculate RIS gain considering multipath contributions

        Args:
            paths_info: List of path dicts with 'amplitude', 'phase', 'delay'
            ris_phases: RIS phase configuration (radians)
            element_spacing: RIS element spacing in wavelengths
            center_freq: Center frequency in Hz

        Returns:
            Effective RIS gain in dB
        """
        k = 2 * np.pi * center_freq / C
        wavelength = C / center_freq

        # Calculate contribution from each path
        total_power = 0.0

        for path_info in paths_info:
            amplitude = path_info.get('amplitude', 1.0)
            phase = path_info.get('phase', 0.0)

            # Apply RIS phase response
            ris_response = np.sum(np.exp(1j * ris_phases))
            path_contribution = amplitude * np.abs(ris_response)**2

            total_power += path_contribution

        # Normalize by number of elements
        num_elements = len(ris_phases)
        gain_linear = total_power / (num_elements**2)
        gain_dB = 10 * np.log10(max(gain_linear, 1e-10))

        return gain_dB

    @staticmethod
    def effective_snr_with_waveform_distortion(ideal_snr_dB, quantization_error_rms_deg,
                                              papr_dB=8.0, equalization_error_dB=0.5):
        """Calculate SNR reduction due to waveform impairments

        Args:
            ideal_snr_dB: SNR without impairments
            quantization_error_rms_deg: RMS phase quantization error in degrees
            papr_dB: Peak-to-Average Power Ratio in dB
            equalization_error_dB: Channel equalization error in dB

        Returns:
            Effective SNR in dB
        """
        # Phase quantization penalty
        quant_error_rad = np.radians(quantization_error_rms_deg)
        sinc_val = np.sinc(quant_error_rad / np.pi)
        # Clamp to prevent log10 of zero/negative
        sinc_val = np.clip(sinc_val, 1e-10, 1.0)
        quant_loss_dB = 20 * np.log10(sinc_val)

        # PAPR clipping loss (approximation)
        papr_loss_dB = -papr_dB / 5  # Empirical factor

        # Equalization loss
        eq_loss_dB = equalization_error_dB

        # Total effective SNR
        effective_snr_dB = ideal_snr_dB + quant_loss_dB + papr_loss_dB - eq_loss_dB

        return effective_snr_dB

    @staticmethod
    def ris_coupling_loss_dB(element_spacing_wavelengths, num_elements,
                            coupling_model='simplified'):
        """Calculate RIS coupling and mismatch losses

        Args:
            element_spacing_wavelengths: Element spacing in wavelengths
            num_elements: Total number of elements
            coupling_model: 'simplified' or 'detailed'

        Returns:
            Total coupling loss in dB
        """
        if coupling_model == 'simplified':
            # Spacing-dependent coupling loss
            if element_spacing_wavelengths <= 0.5:
                spacing_loss = 2.0
            elif element_spacing_wavelengths <= 0.7:
                spacing_loss = 1.0
            else:
                spacing_loss = 0.1

            # Element count dependent efficiency
            count_factor = 20 * np.log10(np.sqrt(num_elements) / 16)

            return spacing_loss + count_factor

        else:  # detailed
            # More complex model considering mutual coupling matrix
            k = 2 * np.pi / element_spacing_wavelengths
            coupling_loss = 0.0

            for i in range(num_elements):
                for j in range(i+1, num_elements):
                    dist = abs(i - j) * element_spacing_wavelengths
                    # Distance-dependent coupling
                    coupling_coeff = 0.1 * np.exp(-dist / 2)
                    # Phase mismatch
                    phase_diff = k * dist
                    coupling_loss += 0.1 * np.abs(coupling_coeff * np.exp(1j * phase_diff))**2

            return 10 * np.log10(coupling_loss / num_elements + 0.01)

    @staticmethod
    def compute_channel_capacity_bps(snr_dB, bandwidth_Hz):
        """Shannon capacity calculation

        Args:
            snr_dB: SNR in dB
            bandwidth_Hz: Bandwidth in Hz

        Returns:
            Capacity in bits per second
        """
        snr_linear = 10 ** (snr_dB / 10)
        capacity = bandwidth_Hz * np.log2(1 + snr_linear)
        return capacity

    @staticmethod
    def validate_quantization_error(ideal_phases_rad, quantized_phases_rad, bits):
        """Validate that quantization error is physically reasonable

        Quantization error must be ≤ phase_step / 2 after wrapping to [-π, π].

        Args:
            ideal_phases_rad: Ideal phases (radians)
            quantized_phases_rad: Quantized phases (radians)
            bits: Number of quantization bits

        Returns:
            Dict with validation result and error statistics

        Raises:
            ValueError: If quantization error exceeds theoretical maximum
        """
        # Wrap errors to [-π, π]
        error = np.angle(np.exp(1j * (ideal_phases_rad - quantized_phases_rad)))

        # Max error should be ≤ phase_step / 2
        phase_step = 2 * np.pi / (2 ** bits)
        max_allowed_error = phase_step / 2

        max_error = np.max(np.abs(error))
        mean_error = np.mean(np.abs(error))
        rms_error = np.sqrt(np.mean(error ** 2))

        # Allow 1% tolerance for floating-point errors
        if max_error > max_allowed_error * 1.01:
            raise ValueError(
                f"Quantization error {np.degrees(max_error):.1f}° exceeds "
                f"maximum {np.degrees(max_allowed_error):.1f}° for {bits}-bit quantizer"
            )

        return {
            'status': 'valid',
            'max_error_deg': np.degrees(max_error),
            'mean_error_deg': np.degrees(mean_error),
            'rms_error_deg': np.degrees(rms_error),
            'max_allowed_deg': np.degrees(max_allowed_error)
        }
