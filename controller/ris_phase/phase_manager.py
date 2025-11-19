"""
RIS Phase Manager - Central controller for all RIS phase operations

Coordinates phase steering, quantization, and optimization operations.
Provides unified interface for RIS phase control.
"""

import numpy as np
from typing import Dict, Optional, Callable, List
import logging

from .phase_steering import PhaseSteeringEngine, BeamSteeringController
from .phase_quantization import (
    UniformQuantizer, OptimizedQuantizer, QuantizationAnalyzer, QuantizationController
)
from .phase_optimization import (
    GradientPhaseOptimizer, ExhaustivePhaseOptimizer,
    GeneticAlgorithmOptimizer, SimulatedAnnealingOptimizer
)

logger = logging.getLogger(__name__)


class RISPhaseManager:
    """
    Centralized RIS phase control manager.

    Manages:
    - Phase steering (linear, optimal path, deflection-based)
    - Phase quantization (uniform, non-uniform)
    - Phase optimization (gradient, genetic algorithm, SA)
    - Phase configuration and state management
    """

    def __init__(self, ris_node):
        """
        Initialize RIS phase manager.

        Args:
            ris_node: RIS node instance from core/nodes.py
        """
        self.ris = ris_node
        self.steering = BeamSteeringController(ris_node)
        self.quantizer = QuantizationController(ris_node)
        self.analyzer = QuantizationAnalyzer()
        self.steering_engine = PhaseSteeringEngine()

        # Optimization state
        self.optimizer = None
        self.snr_function = None
        self.use_optimized_quantization = False
        self.optimization_method = 'gradient_descent'

    # =========================================================================
    # Quantization Configuration
    # =========================================================================

    def enable_optimized_quantization(self, method: str = 'gradient_descent') -> Dict:
        """
        Enable optimized quantization for this RIS.

        Uses optimization to find best quantized phases that maximize array gain
        for the target steering angle, rather than simple nearest-level quantization.

        Args:
            method: Optimization method ('gradient_descent', 'particle_swarm', 'exhaustive')

        Returns:
            Status dictionary
        """
        try:
            self.use_optimized_quantization = True
            self.optimization_method = method
            self.quantizer = QuantizationController(
                self.ris,
                quantizer_type='optimized',
                optimization_method=method
            )
            logger.info(f"Enabled optimized quantization with {method} method")
            return {'status': 'success', 'method': method}
        except Exception as e:
            logger.error(f"Failed to enable optimized quantization: {e}")
            return {'status': 'failed', 'error': str(e)}

    def disable_optimized_quantization(self) -> Dict:
        """Disable optimized quantization, return to uniform quantization"""
        try:
            self.use_optimized_quantization = False
            self.quantizer = QuantizationController(self.ris, quantizer_type='uniform')
            logger.info("Disabled optimized quantization")
            return {'status': 'success'}
        except Exception as e:
            logger.error(f"Failed to disable optimized quantization: {e}")
            return {'status': 'failed', 'error': str(e)}

    # =========================================================================
    # Phase Steering Operations
    # =========================================================================

    def steer_to_angle(self, beam_angle_deg: float) -> Dict:
        """
        Steer RIS to specific beam angle.

        Args:
            beam_angle_deg: Target beam angle in degrees

        Returns:
            Dictionary with steering result and status
        """
        result = self.steering.steer_to_angle(beam_angle_deg)

        if result.get('status') == 'success':
            logger.info(f"RIS steered to {beam_angle_deg:.2f}°")

        return result

    def steer_to_target(
        self,
        ap_position: np.ndarray,
        ue_position: np.ndarray
    ) -> Dict:
        """
        Steer RIS to align with AP→UE path.

        Args:
            ap_position: Access Point position
            ue_position: User Equipment position

        Returns:
            Dictionary with steering result
        """
        result = self.steering.steer_to_target(ap_position, ue_position)

        if result.get('status') == 'success':
            logger.info("RIS steered to target path")

        return result

    def steer_from_deflection(
        self,
        deflection_angle_deg: float,
        specular_angle_deg: float
    ) -> Dict:
        """
        Set RIS phases from deflection angle.

        Args:
            deflection_angle_deg: Deflection from specular reflection
            specular_angle_deg: Specular reflection reference angle

        Returns:
            Dictionary with steering result
        """
        absolute_angle = specular_angle_deg + deflection_angle_deg

        return self.steer_to_angle(absolute_angle)

    def get_current_steering_angle(self) -> float:
        """
        Get current estimated beam steering angle.

        Returns:
            Beam angle in degrees
        """
        return self.steering.get_steering_angle()

    # =========================================================================
    # Phase Quantization Operations
    # =========================================================================

    def quantize_phases(self) -> Dict:
        """
        Quantize ideal phases to discrete levels.

        Returns:
            Quantization results with loss analysis
        """
        return self.quantizer.apply_quantization()

    def analyze_quantization(self) -> Dict:
        """
        Analyze quantization quality and losses.

        Returns:
            Quantization analysis results
        """
        return self.quantizer.analyze_current_quantization()

    def get_phase_state_distribution(self) -> Dict[int, int]:
        """
        Get distribution of phase states used.

        Returns:
            Dictionary mapping state index to element count
        """
        return self.quantizer.get_state_distribution()

    # =========================================================================
    # Phase Configuration Management
    # =========================================================================

    def set_ideal_phases(self, phases: np.ndarray) -> Dict:
        """
        Manually set ideal phase array.

        Args:
            phases: Phase array in radians

        Returns:
            Status dictionary
        """
        try:
            if len(phases) != self.ris.N ** 2:
                return {
                    'status': 'failed',
                    'error': f'Phase array size {len(phases)} != RIS size {self.ris.N**2}'
                }

            self.ris.current_phases = phases.copy()
            logger.info(f"Set {len(phases)} ideal phases")

            return {'status': 'success', 'num_phases': len(phases)}
        except Exception as e:
            logger.error(f"Failed to set ideal phases: {e}")
            return {'status': 'failed', 'error': str(e)}

    def get_phase_grid(self) -> Optional[Dict]:
        """
        Get current phase configuration as 2D grid.

        Returns:
            Dictionary with ideal_deg, quantized_deg, phase_states grids (N×N)
        """
        if self.ris.current_phases is None:
            return None

        return {
            'ideal_deg': np.degrees(self.ris.current_phases).reshape(self.ris.N, self.ris.N),
            'quantized_deg': np.degrees(self.ris.quantized_phases).reshape(self.ris.N, self.ris.N)
            if self.ris.quantized_phases is not None else None,
            'states': self.ris.phase_states.reshape(self.ris.N, self.ris.N)
            if self.ris.phase_states is not None else None
        }

    def reset_phases(self) -> Dict:
        """
        Reset phase array to zero.

        Returns:
            Status dictionary
        """
        try:
            self.ris.current_phases = np.zeros(self.ris.N ** 2)
            self.ris.quantized_phases = None
            self.ris.phase_states = None

            logger.info("Reset RIS phases to zero")
            return {'status': 'success'}
        except Exception as e:
            return {'status': 'failed', 'error': str(e)}

    # =========================================================================
    # Phase Optimization Operations
    # =========================================================================

    def optimize_phases(
        self,
        snr_function: Callable,
        algorithm: str = 'gradient',
        max_iterations: int = 100,
        **kwargs
    ) -> Dict:
        """
        Optimize RIS phases using specified algorithm.

        Args:
            snr_function: Function to compute SNR(phases)
            algorithm: Optimization method:
                - 'gradient': Gradient ascent
                - 'exhaustive': Exhaustive search
                - 'genetic': Genetic algorithm
                - 'simulated_annealing': Simulated annealing
            max_iterations: Maximum iterations for algorithm
            **kwargs: Algorithm-specific parameters

        Returns:
            Optimization results
        """
        if self.ris.current_phases is None:
            return {'status': 'failed', 'error': 'No initial phases set'}

        try:
            if algorithm == 'gradient':
                self.optimizer = GradientPhaseOptimizer(
                    self.ris,
                    snr_function,
                    learning_rate=kwargs.get('learning_rate', 0.01)
                )
            elif algorithm == 'exhaustive':
                self.optimizer = ExhaustivePhaseOptimizer(self.ris, snr_function)
            elif algorithm == 'genetic':
                self.optimizer = GeneticAlgorithmOptimizer(
                    self.ris,
                    snr_function,
                    population_size=kwargs.get('population_size', 20),
                    mutation_rate=kwargs.get('mutation_rate', 0.1)
                )
            elif algorithm == 'simulated_annealing':
                self.optimizer = SimulatedAnnealingOptimizer(
                    self.ris,
                    snr_function,
                    initial_temperature=kwargs.get('initial_temperature', 100.0),
                    cooling_rate=kwargs.get('cooling_rate', 0.95)
                )
            else:
                return {'status': 'failed', 'error': f'Unknown algorithm: {algorithm}'}

            self.snr_function = snr_function

            result = self.optimizer.optimize(max_iterations)

            logger.info(f"Phase optimization ({algorithm}) complete")
            return result

        except Exception as e:
            logger.error(f"Phase optimization failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def get_optimization_history(self) -> List[Dict]:
        """
        Get optimization history from last run.

        Returns:
            List of optimization iterations/generations
        """
        if self.optimizer is None:
            return []

        return self.optimizer.get_history()

    # =========================================================================
    # Phase Analysis and Reporting
    # =========================================================================

    def get_phase_summary(self) -> Dict:
        """
        Get comprehensive phase configuration summary.

        Returns:
            Dictionary with all phase metrics and statistics
        """
        summary = {
            'num_elements': self.ris.N ** 2,
            'array_size': f'{self.ris.N}×{self.ris.N}',
            'num_bits': self.ris.bits,
            'num_levels': 2 ** self.ris.bits
        }

        if self.ris.current_phases is not None:
            summary['ideal_phases'] = {
                'mean_deg': np.degrees(np.mean(self.ris.current_phases)),
                'min_deg': np.degrees(np.min(self.ris.current_phases)),
                'max_deg': np.degrees(np.max(self.ris.current_phases)),
                'range_deg': np.degrees(np.ptp(self.ris.current_phases))
            }

        if self.ris.quantized_phases is not None:
            rms_error = self.analyzer.compute_rms_error(
                self.ris.current_phases,
                self.ris.quantized_phases
            )
            loss_db = self.analyzer.compute_quantization_loss_db(rms_error)

            summary['quantization'] = {
                'rms_error_deg': np.degrees(rms_error),
                'loss_dB': loss_db,
                'states_used': len(np.unique(self.ris.phase_states))
            }

        return summary

    def print_phase_report(self):
        """Print formatted phase configuration report"""
        summary = self.get_phase_summary()

        print("\n" + "="*70)
        print("RIS Phase Configuration Report")
        print("="*70)

        print(f"\nArray Configuration:")
        print(f"  Size: {summary['array_size']}")
        print(f"  Total Elements: {summary['num_elements']}")
        print(f"  Phase Bits: {summary['num_bits']}-bit ({summary['num_levels']} levels)")

        if 'ideal_phases' in summary:
            phases = summary['ideal_phases']
            print(f"\nIdeal Phases (degrees):")
            print(f"  Mean: {phases['mean_deg']:.2f}°")
            print(f"  Min: {phases['min_deg']:.2f}°")
            print(f"  Max: {phases['max_deg']:.2f}°")
            print(f"  Range: {phases['range_deg']:.2f}°")

        if 'quantization' in summary:
            quant = summary['quantization']
            print(f"\nQuantization Analysis:")
            print(f"  RMS Error: {quant['rms_error_deg']:.4f}°")
            print(f"  Loss: {quant['loss_dB']:.4f} dB")
            print(f"  States Used: {quant['states_used']}/{summary['num_levels']}")

        # Phase grid (if small enough)
        if self.ris.N <= 8:
            grids = self.get_phase_grid()
            if grids and grids['quantized_deg'] is not None:
                print(f"\nQuantized Phase Grid (degrees, {self.ris.N}×{self.ris.N}):")
                for row in grids['quantized_deg']:
                    print("  " + "  ".join([f"{p:7.1f}°" for p in row]))

        print("\n" + "="*70 + "\n")

    # =========================================================================
    # Integrated Workflows
    # =========================================================================

    def configure_beam(
        self,
        beam_angle_deg: float,
        ap_position: Optional[np.ndarray] = None,
        ue_position: Optional[np.ndarray] = None,
        mode: str = 'steering'
    ) -> Dict:
        """
        Configure RIS beam with complete workflow.

        Args:
            beam_angle_deg: Target angle or deflection
            ap_position: AP position (for optimal path mode)
            ue_position: UE position (for optimal path mode)
            mode: 'steering' (linear) or 'optimal' (path-based)

        Returns:
            Combined results from steering and quantization
        """
        result = {}

        # Steering
        if mode == 'optimal' and ap_position is not None and ue_position is not None:
            result['steering'] = self.steer_to_target(ap_position, ue_position)
        else:
            result['steering'] = self.steer_to_angle(beam_angle_deg)

        # Quantization
        result['quantization'] = self.quantize_phases()

        # Analysis
        result['summary'] = self.get_phase_summary()

        return result

    def quick_search(
        self,
        angle_range: float = 60.0,
        angle_step: float = 10.0
    ) -> Dict:
        """
        Quick beam search over angle range (requires SNR function).

        Args:
            angle_range: Search range in degrees (±)
            angle_step: Step size in degrees

        Returns:
            Search results with best angle and SNR
        """
        if self.snr_function is None:
            return {'status': 'failed', 'error': 'SNR function not configured'}

        try:
            angles = np.arange(-angle_range, angle_range + angle_step, angle_step)
            results = []

            for angle in angles:
                self.steer_to_angle(angle)
                self.quantize_phases()

                snr = self.snr_function(self.ris.quantized_phases)
                snr_db = 10 * np.log10(snr) if snr > 0 else -np.inf

                results.append({
                    'angle': angle,
                    'snr_dB': snr_db,
                    'snr_linear': snr
                })

            # Find best
            best = max(results, key=lambda x: x['snr_dB'])

            return {
                'status': 'success',
                'best_angle': best['angle'],
                'best_snr_dB': best['snr_dB'],
                'num_angles_tested': len(angles),
                'results': results
            }

        except Exception as e:
            logger.error(f"Quick search failed: {e}")
            return {'status': 'failed', 'error': str(e)}
