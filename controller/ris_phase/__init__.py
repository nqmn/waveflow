"""
RIS Phase Control Module

Comprehensive RIS phase management including:
- Phase steering (linear, optimal path, deflection-based)
- Phase quantization (uniform, multi-bit, loss analysis)
- Phase optimization (gradient, genetic algorithm, simulated annealing)
- Unified phase manager interface
"""

from .phase_steering import PhaseSteeringEngine, BeamSteeringController
from .phase_quantization import (
    PhaseQuantizer, UniformQuantizer, NonuniformQuantizer,
    QuantizationAnalyzer, QuantizationLookupTable, QuantizationController
)
from .phase_optimization import (
    PhaseOptimizer, GradientPhaseOptimizer, ExhaustivePhaseOptimizer,
    GeneticAlgorithmOptimizer, SimulatedAnnealingOptimizer
)
from .phase_manager import RISPhaseManager

__all__ = [
    # Steering
    'PhaseSteeringEngine',
    'BeamSteeringController',

    # Quantization
    'PhaseQuantizer',
    'UniformQuantizer',
    'NonuniformQuantizer',
    'QuantizationAnalyzer',
    'QuantizationLookupTable',
    'QuantizationController',

    # Optimization
    'PhaseOptimizer',
    'GradientPhaseOptimizer',
    'ExhaustivePhaseOptimizer',
    'GeneticAlgorithmOptimizer',
    'SimulatedAnnealingOptimizer',

    # Manager
    'RISPhaseManager'
]
