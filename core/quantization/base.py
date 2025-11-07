"""
Base quantizer class for RIS phase quantization strategies
"""
import numpy as np
from abc import ABC, abstractmethod


class BaseQuantizer(ABC):
    """Abstract base class for phase quantizers

    All quantizers must implement the quantize method to convert ideal phases
    to discrete quantization levels.
    """

    def __init__(self, name, description=""):
        """Initialize quantizer

        Args:
            name: Unique identifier for this quantizer
            description: Human-readable description
        """
        self.name = name
        self.description = description

    @abstractmethod
    def quantize(self, ideal_phases, bits):
        """Quantize ideal phases to discrete levels

        Args:
            ideal_phases: Ideal phases in radians (numpy array)
            bits: Number of quantization bits

        Returns:
            Tuple of (quantized_phases, phase_states)
                - quantized_phases: Quantized phases in radians
                - phase_states: Integer states (0 to 2^bits - 1)
        """
        pass

    def get_phase_step(self, bits):
        """Get phase step size for given bit width

        Args:
            bits: Number of quantization bits

        Returns:
            Phase step in radians
        """
        if bits == 0:
            return 2 * np.pi  # No quantization
        return 2 * np.pi / (2 ** bits)

    def get_num_levels(self, bits):
        """Get number of quantization levels

        Args:
            bits: Number of quantization bits

        Returns:
            Number of discrete levels
        """
        if bits == 0:
            return 1
        return 2 ** bits

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', description='{self.description}')"
