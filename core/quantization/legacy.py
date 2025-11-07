"""
Legacy RISNet phase quantization strategy (backward compatibility)
"""
import numpy as np
from .base import BaseQuantizer


class LegacyQuantizer(BaseQuantizer):
    """Legacy quantization method from original RISNet

    This quantizer uses the original RISNet quantization formula for
    backward compatibility with earlier simulations.

    Formula: phase_error = π / (2^bits)
    """

    def __init__(self):
        super().__init__(
            name='legacy',
            description='Original RISNet quantization formula (backward compatible)'
        )

    def quantize(self, ideal_phases, bits):
        """Quantize phases using legacy method

        Args:
            ideal_phases: Ideal phases in radians (numpy array or float)
            bits: Number of quantization bits

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        if bits == 0:
            # No quantization
            return ideal_phases, np.zeros_like(ideal_phases, dtype=int)

        num_levels = self.get_num_levels(bits)

        # Legacy formula: phase step based on π / 2^bits
        # This differs slightly from standard uniform quantization (2π / 2^bits)
        phase_step = np.pi / (2 ** (bits - 1)) if bits > 0 else 2 * np.pi

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
