"""Beam sweep algorithms module

Provides a modular approach to beam sweeping with multiple algorithms available.
Each algorithm is implemented as a separate module and can be loaded dynamically.
"""

from .base import SweepAlgorithmBase
from .algorithms import (
    CoarseFineSweep,
    EdgeCenterSweep,
    LinearBruteForceSweep,
    MLGuidedSweep,
    ANMLocalizationSweep,
    get_algorithm_class,
    list_registered_algorithms,
)
from utils.snr import compute_snr
from .ml import MLPredictorLoader, SweepMLPredictor


class SweepAlgorithmLoader:
    """Loader for sweep algorithms

    Provides access to three core beam sweep algorithms:
    - linear (brute-force): Exhaustive search across FOV
    - coarse-fine (two-phase): Two-phase intelligent center-out search
    - ml (ml-guided): ML-guided beam sweep with validation

    Backward compatibility aliases:
    - 'adaptive' and 'center-out' map to 'coarse-fine'

    Note: Real signal-level emulation is integrated into each algorithm
    via the use_waveform parameter, not as a separate algorithm.
    """
    DEFAULT_ALGORITHM = 'linear'

    @classmethod
    def get_algorithm(cls, name: str, network):
        """Load sweep algorithm by name

        Args:
            name: Algorithm name (case-insensitive)
            network: RISNet network object

        Returns:
            Initialized sweep algorithm instance

        Raises:
            ValueError: If algorithm not found
        """
        AlgorithmClass = get_algorithm_class(name)
        return AlgorithmClass(network)

    @classmethod
    def list_algorithms(cls):
        """List all available algorithms with descriptions

        Returns:
            Dictionary of algorithm info
        """
        info = {}
        for registration in list_registered_algorithms():
            AlgorithmClass = registration.cls
            instance = AlgorithmClass(None)
            info[registration.primary_name] = {
                'class_name': instance.name,
                'description': instance.description,
                'aliases': tuple(registration.aliases),
            }
        return info

    @classmethod
    def get_default(cls, network):
        """Get default algorithm (linear brute-force)

        Args:
            network: RISNet network object

        Returns:
            Default sweep algorithm instance
        """
        return cls.get_algorithm(cls.DEFAULT_ALGORITHM, network)


__all__ = [
    'SweepAlgorithmBase',
    'LinearBruteForceSweep',
    'CoarseFineSweep',
    'MLGuidedSweep',
    'EdgeCenterSweep',
    'ANMLocalizationSweep',
    'SweepAlgorithmLoader',
    'SweepMLPredictor',
    'MLPredictorLoader',
    'compute_snr',
]
