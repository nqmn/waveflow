"""
RIS Phase Quantization - Discrete phase level mapping and quantization control

Implements quantization strategies for RIS phase shifters:
- Uniform quantization to discrete phase levels
- Phase state mapping and lookup tables
- Quantization loss analysis and modeling
- Multi-bit vs single-bit quantizer behavior
"""

import numpy as np
from typing import Dict, Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)


class PhaseQuantizer:
    """Base class for phase quantization strategies"""

    def __init__(self, num_bits: int):
        """
        Initialize phase quantizer.

        Args:
            num_bits: Number of bits for phase shifter (1, 2, 3, etc.)
        """
        self.num_bits = num_bits
        self.num_levels = 2 ** num_bits
        self.phase_step = 2 * np.pi / self.num_levels

    def quantize(self, ideal_phases: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quantize ideal phases to discrete levels.

        Args:
            ideal_phases: Ideal phases in radians (can be any value)

        Returns:
            Tuple of (quantized_phases, phase_states)
            - quantized_phases: Phases rounded to nearest discrete level (radians)
            - phase_states: Integer state indices (0 to 2^bits - 1)
        """
        raise NotImplementedError

    def get_discrete_levels(self) -> np.ndarray:
        """
        Get all possible discrete phase levels.

        Returns:
            Array of discrete phase levels in radians
        """
        from risnet.arrays.quantization import uniform_phase_levels

        return uniform_phase_levels(self.num_bits)

    def phase_to_state(self, phase_rad: float) -> int:
        """Convert phase to discrete state number."""
        from risnet.arrays.quantization import phase_to_state

        return phase_to_state(phase_rad, self.num_bits)

    def state_to_phase(self, state: int) -> float:
        """Convert state number to phase value."""
        from risnet.arrays.quantization import state_to_phase

        return state_to_phase(state, self.num_bits)

    def get_quantization_error(self, ideal_phase: float) -> float:
        """
        Calculate quantization error for ideal phase.

        Args:
            ideal_phase: Ideal phase in radians

        Returns:
            Quantization error in radians
        """
        quantized = self.state_to_phase(self.phase_to_state(ideal_phase))
        error = ideal_phase - quantized

        # Wrap error to [-π, π]
        while error > np.pi:
            error -= 2 * np.pi
        while error < -np.pi:
            error += 2 * np.pi

        return error


class UniformQuantizer(PhaseQuantizer):
    """Uniform quantization to evenly-spaced phase levels"""

    def quantize(self, ideal_phases: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quantize using uniform levels.

        For N-bit quantizer:
        - Number of levels: 2^N
        - Phase step: 2π / 2^N
        - Quantized phase: round(φ / step) * step

        Args:
            ideal_phases: Ideal phases in radians

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        from risnet.arrays.quantization import quantize_uniform_phases

        return quantize_uniform_phases(ideal_phases, self.num_bits)


class NonuniformQuantizer(PhaseQuantizer):
    """Non-uniform quantization (e.g., logarithmic spacing)"""

    def __init__(self, num_bits: int, distribution: str = 'log'):
        """
        Initialize non-uniform quantizer.

        Args:
            num_bits: Number of bits
            distribution: 'log', 'sqrt', or custom
        """
        super().__init__(num_bits)
        self.distribution = distribution
        self._compute_levels()

    def _compute_levels(self):
        """Compute non-uniform level spacing"""
        if self.distribution == 'log':
            # Logarithmic spacing (finer resolution at low phases)
            x = np.logspace(0, 1, self.num_levels) - 1  # [0, 9]
            self.custom_levels = (x / x[-1]) * (2 * np.pi)
        elif self.distribution == 'sqrt':
            # Square root spacing
            x = np.sqrt(np.linspace(0, self.num_levels - 1, self.num_levels))
            self.custom_levels = (x / x[-1]) * (2 * np.pi)
        else:
            # Default to uniform
            self.custom_levels = np.arange(self.num_levels) * self.phase_step

    def quantize(self, ideal_phases: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quantize using non-uniform levels.

        Args:
            ideal_phases: Ideal phases in radians

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        normalized = ideal_phases % (2 * np.pi)

        # Find nearest custom level for each phase
        quantized = np.zeros_like(normalized)
        states = np.zeros(len(normalized), dtype=int)

        for i, phase in enumerate(normalized):
            distances = np.abs(self.custom_levels - phase)
            state = np.argmin(distances)
            states[i] = state
            quantized[i] = self.custom_levels[state]

        return quantized, states


class OptimizedQuantizer(PhaseQuantizer):
    """Optimization-aware quantization to maximize array gain for target angle"""

    def __init__(self, num_bits: int, optimization_method: str = 'gradient_descent'):
        """
        Initialize optimized quantizer.

        Args:
            num_bits: Number of bits for phase quantization
            optimization_method: 'gradient_descent', 'particle_swarm', or 'exhaustive'
        """
        super().__init__(num_bits)
        self.optimization_method = optimization_method

    def quantize(self, ideal_phases: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quantize using optimization to find best 1-bit phases for target angle.

        This method finds quantized phases that minimize deviation from ideal
        while respecting quantization constraints.

        Args:
            ideal_phases: Ideal phases in radians

        Returns:
            Tuple of (quantized_phases, phase_states)
        """
        from controller.ris_phase.phase_steering import PhaseSteeringEngine

        # Use optimization method to find best quantized phases
        quantized_phases, metadata = PhaseSteeringEngine.optimize_quantized_phases(
            ideal_phases=ideal_phases,
            bits=self.num_bits,
            ris_array_size=int(np.sqrt(len(ideal_phases))),
            method=self.optimization_method
        )

        # Convert to states
        normalized = quantized_phases % (2 * np.pi)
        states = np.round(normalized / self.phase_step).astype(int) % self.num_levels

        return quantized_phases, states

    def get_optimization_metadata(self) -> Dict:
        """Get metadata from last optimization run"""
        return getattr(self, '_last_metadata', {})


class QuantizationAnalyzer:
    """Analyze quantization effects and losses"""

    @staticmethod
    def compute_rms_error(ideal_phases: np.ndarray, quantized_phases: np.ndarray) -> float:
        """
        Compute RMS phase error.

        Args:
            ideal_phases: Ideal phases (radians)
            quantized_phases: Quantized phases (radians)

        Returns:
            RMS error in radians
        """
        # Compute error with wrapping
        error = ideal_phases - quantized_phases

        # Wrap errors to [-π, π]
        error = np.angle(np.exp(1j * error))

        # RMS
        rms_error = np.sqrt(np.mean(error ** 2))

        return rms_error

    @staticmethod
    def compute_quantization_loss_db(
        rms_error_rad: float,
        model: str = 'standard'
    ) -> float:
        """
        Estimate SNR loss from phase quantization error.

        Uses different models:
        - 'standard': Based on sinc function of phase error
        - 'legacy': Simplified formula

        Args:
            rms_error_rad: RMS phase error in radians
            model: Quantization model ('standard' or 'legacy')

        Returns:
            Loss in dB (negative value)
        """
        if model == 'standard':
            # Loss based on array gain reduction
            # Directivity loss: sinc²(error)
            if rms_error_rad < 1e-6:
                return 0.0

            loss_linear = np.sinc(rms_error_rad / np.pi) ** 2
            loss_db = 10 * np.log10(max(loss_linear, 1e-6))

        elif model == 'legacy':
            # Legacy model: simpler approximation
            loss_db = -1.67 * (rms_error_rad / (np.pi / 2)) ** 2

        else:
            logger.warning(f"Unknown model '{model}', using standard")
            loss_db = QuantizationAnalyzer.compute_quantization_loss_db(
                rms_error_rad, model='standard'
            )

        return loss_db

    @staticmethod
    def compare_quantizers(
        ideal_phases: np.ndarray,
        bit_widths: List[int]
    ) -> Dict[int, Dict]:
        """
        Compare quantization performance across different bit widths.

        Args:
            ideal_phases: Ideal phases (radians)
            bit_widths: List of bit widths to compare (e.g., [1, 2, 3, 4])

        Returns:
            Dictionary with results for each bit width
        """
        results = {}

        for bits in bit_widths:
            quantizer = UniformQuantizer(bits)
            quantized, states = quantizer.quantize(ideal_phases)

            rms_error = QuantizationAnalyzer.compute_rms_error(ideal_phases, quantized)
            loss_db = QuantizationAnalyzer.compute_quantization_loss_db(rms_error)

            # FIXED: Wrap error to [-π, π] before computing max (issue: raw diff can exceed ±π)
            error_wrapped = np.angle(np.exp(1j * (ideal_phases - quantized)))
            max_error_deg = np.degrees(np.max(np.abs(error_wrapped)))

            results[bits] = {
                'num_levels': 2 ** bits,
                'phase_step_deg': (2 * np.pi / (2 ** bits)) * 180 / np.pi,
                'rms_error_rad': rms_error,
                'rms_error_deg': np.degrees(rms_error),
                'quantization_loss_dB': loss_db,
                'max_error_deg': max_error_deg
            }

        return results


class QuantizationLookupTable:
    """Precomputed lookup tables for fast quantization"""

    def __init__(self, num_bits: int, num_phase_values: int = 360):
        """
        Initialize lookup table for phase quantization.

        Args:
            num_bits: Number of bits in phase shifter
            num_phase_values: Resolution of lookup table (degrees)
        """
        self.num_bits = num_bits
        self.num_levels = 2 ** num_bits
        self.phase_step_deg = 360 / self.num_levels

        # Build lookup table: phase_deg -> (quantized_phase_deg, state)
        self.lut = {}
        for deg in range(num_phase_values):
            rad = np.radians(deg)
            quantizer = UniformQuantizer(num_bits)
            quantized_rad, state = quantizer.quantize(np.array([rad]))
            quantized_deg = np.degrees(quantized_rad[0])
            self.lut[deg] = (quantized_deg, int(state[0]))

    def quantize(self, phase_deg: float) -> Tuple[float, int]:
        """
        Fast quantization using lookup table.

        Args:
            phase_deg: Phase in degrees

        Returns:
            Tuple of (quantized_phase_deg, state)
        """
        # Normalize to [0, 360)
        phase_normalized = phase_deg % 360

        # Find nearest lookup entry
        lookup_key = int(np.round(phase_normalized))
        if lookup_key >= 360:
            lookup_key = 0

        if lookup_key in self.lut:
            return self.lut[lookup_key]
        else:
            # Fallback: compute on the fly
            rad = np.radians(phase_deg)
            quantizer = UniformQuantizer(self.num_bits)
            quantized_rad, state = quantizer.quantize(np.array([rad]))
            return np.degrees(quantized_rad[0]), int(state[0])

    def get_discrete_levels(self) -> np.ndarray:
        """Get all discrete phase levels in degrees."""
        return np.arange(self.num_levels) * self.phase_step_deg


class QuantizationController:
    """Control RIS phase quantization"""

    def __init__(self, ris_node, quantizer_type: str = 'uniform', optimization_method: str = None):
        """
        Initialize quantization controller.

        Args:
            ris_node: RIS node instance
            quantizer_type: Type of quantizer ('uniform', 'nonuniform', or 'optimized')
            optimization_method: For optimized quantizer: 'gradient_descent', 'particle_swarm', etc.
        """
        self.ris = ris_node
        self.quantizer_type = quantizer_type

        # Create appropriate quantizer type
        if quantizer_type == 'optimized':
            self.quantizer = OptimizedQuantizer(
                ris_node.bits,
                optimization_method=optimization_method or 'gradient_descent'
            )
        elif quantizer_type == 'nonuniform':
            self.quantizer = NonuniformQuantizer(ris_node.bits)
        else:  # 'uniform' or default
            self.quantizer = UniformQuantizer(ris_node.bits)

        self.analyzer = QuantizationAnalyzer()
        self.lut = QuantizationLookupTable(ris_node.bits)

    def apply_quantization(self) -> Dict:
        """
        Apply quantization to current ideal phases.

        Returns:
            Dictionary with quantization results
        """
        if self.ris.current_phases is None:
            return {'status': 'failed', 'error': 'No ideal phases set'}

        try:
            quantized, states = self.quantizer.quantize(self.ris.current_phases)

            # Store in RIS node
            self.ris.quantized_phases = quantized
            self.ris.phase_states = states

            # Analyze
            rms_error = self.analyzer.compute_rms_error(
                self.ris.current_phases, quantized
            )
            loss_db = self.analyzer.compute_quantization_loss_db(rms_error)

            return {
                'status': 'success',
                'num_elements': len(quantized),
                'rms_error_rad': rms_error,
                'rms_error_deg': np.degrees(rms_error),
                'quantization_loss_dB': loss_db,
                'num_levels': self.quantizer.num_levels,
                'phase_step_deg': np.degrees(self.quantizer.phase_step)
            }
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def analyze_current_quantization(self) -> Dict:
        """
        Analyze quantization quality of current phase configuration.

        Returns:
            Quantization analysis results
        """
        if self.ris.current_phases is None or self.ris.quantized_phases is None:
            return {'status': 'no_phases'}

        rms_error = self.analyzer.compute_rms_error(
            self.ris.current_phases,
            self.ris.quantized_phases
        )
        loss_db = self.analyzer.compute_quantization_loss_db(rms_error)

        max_error = np.max(np.abs(self.ris.current_phases - self.ris.quantized_phases))

        return {
            'status': 'success',
            'num_bits': self.ris.bits,
            'num_levels': self.quantizer.num_levels,
            'rms_error_rad': rms_error,
            'rms_error_deg': np.degrees(rms_error),
            'max_error_deg': np.degrees(max_error),
            'quantization_loss_dB': loss_db,
            'phase_step_deg': np.degrees(self.quantizer.phase_step),
            'states_used': len(np.unique(self.ris.phase_states))
        }

    def get_state_distribution(self) -> Dict[int, int]:
        """
        Get distribution of phase states used.

        Returns:
            Dictionary mapping state index to count
        """
        if self.ris.phase_states is None:
            return {}

        distribution = {}
        for state in self.ris.phase_states:
            state_idx = int(state)
            distribution[state_idx] = distribution.get(state_idx, 0) + 1

        return dict(sorted(distribution.items()))
