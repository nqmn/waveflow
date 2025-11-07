"""
Adaptive phase quantization strategy

This is an example custom quantizer that adapts quantization levels
based on phase magnitude to minimize error in high-impact regions.
"""
import numpy as np
from core.quantization.base import BaseQuantizer


class Quantizer(BaseQuantizer):
    """Adaptive quantization that concentrates levels where needed

    This quantizer adapts the quantization levels to minimize error
    in regions with high phase magnitudes, which tend to have greater
    impact on beamforming performance.
    """

    def __init__(self):
        super().__init__(
            name='adaptive',
            description='Adaptive quantization concentrating levels in high-impact regions'
        )

    def quantize(self, ideal_phases, bits):
        """Adaptively quantize phases based on magnitude

        Args:
            ideal_phases: Ideal phases in radians (numpy array or float)
            bits: Number of quantization bits

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        if bits == 0:
            return ideal_phases, np.zeros_like(ideal_phases, dtype=int)

        num_levels = self.get_num_levels(bits)

        # Ensure input is numpy array
        ideal_phases = np.asarray(ideal_phases)
        original_shape = ideal_phases.shape

        # Flatten for processing
        phases_flat = ideal_phases.flatten()

        # Standard phase step
        phase_step = self.get_phase_step(bits)

        # Adaptive quantization: weight levels based on phase magnitude
        # Phases near 0 and π have more impact on beamforming
        magnitude_weight = np.abs(np.cos(phases_flat))

        # Compute adaptive quantization levels
        quantized = np.zeros_like(phases_flat)
        states = np.zeros(len(phases_flat), dtype=int)

        for i, phase in enumerate(phases_flat):
            # Find nearest quantization level
            potential_states = np.arange(num_levels)
            potential_phases = potential_states * phase_step

            # Weight error by impact (phases near 0, π have more weight)
            errors = np.abs(potential_phases - phase)
            weighted_errors = errors * (1.0 + magnitude_weight[i])

            best_state = np.argmin(weighted_errors)

            quantized[i] = potential_phases[best_state]
            states[i] = best_state

        # Wrap to [0, 2π)
        quantized = np.mod(quantized, 2 * np.pi)

        # Reshape back to original shape
        quantized = quantized.reshape(original_shape)
        states = states.reshape(original_shape)

        return quantized, states
