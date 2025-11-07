"""
Uniform phase quantization strategy
Standard approach: quantize phases to nearest discrete level
"""
import numpy as np
from .base import BaseQuantizer


class UniformQuantizer(BaseQuantizer):
    """Uniform quantization with equal-spaced phase levels

    This is the standard quantization approach where phases are rounded
    to the nearest discrete level. Phase levels are uniformly spaced
    from 0 to 2π.

    Example:
        For 2-bit quantization: 4 levels at 0°, 90°, 180°, 270°
    """

    def __init__(self):
        super().__init__(
            name='uniform',
            description='Standard uniform quantization with equal-spaced levels'
        )

    def quantize(self, ideal_phases, bits):
        """Quantize ideal phases using uniform quantization

        Args:
            ideal_phases: Ideal phases in radians (numpy array or float)
            bits: Number of quantization bits

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        if bits == 0:
            # No quantization - return ideal phases
            return ideal_phases, np.zeros_like(ideal_phases, dtype=int)

        num_levels = self.get_num_levels(bits)
        phase_step = self.get_phase_step(bits)

        # Ensure input is numpy array
        ideal_phases = np.asarray(ideal_phases)
        original_shape = ideal_phases.shape

        # Flatten for processing
        phases_flat = ideal_phases.flatten()

        # Quantize each phase to nearest level
        quantized = np.round(phases_flat / phase_step) * phase_step

        # Wrap to [0, 2π)
        quantized = np.mod(quantized, 2 * np.pi)

        # Compute state indices
        states = np.round(quantized / phase_step).astype(int) % num_levels

        # Reshape back to original shape
        quantized = quantized.reshape(original_shape)
        states = states.reshape(original_shape)

        return quantized, states
