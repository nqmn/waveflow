"""Beam sweep algorithms module

Provides a modular approach to beam sweeping with multiple algorithms available.
Each algorithm is implemented as a separate module and can be loaded dynamically.
"""

from .base import SweepAlgorithmBase
from .algorithms.linear_brute_force import LinearBruteForceSweep
from .algorithms.coarse_fine_sweep import CoarseFineSweep
from .algorithms.ml_sweep import MLGuidedSweep
from utils.snr import compute_snr
from .ml import MLPredictorLoader, SweepMLPredictor


class SweepAlgorithmLoader:
    """Loader for sweep algorithms

    Provides access to three core beam sweep algorithms:
    - linear (brute-force): Exhaustive search across FOV
    - coarse-fine (two-phase): Two-phase intelligent center-out search
    - ml (ml-guided): ML predictor-driven search

    Backward compatibility aliases:
    - 'adaptive' and 'center-out' map to 'coarse-fine'

    Note: Real signal-level emulation is integrated into each algorithm
    via the use_waveform parameter, not as a separate algorithm.
    """

    ALGORITHMS = {
        'linear': LinearBruteForceSweep,
        'brute-force': LinearBruteForceSweep,
        'coarse-fine': CoarseFineSweep,
        'two-phase': CoarseFineSweep,
        # Backward compatibility aliases
        'adaptive': CoarseFineSweep,
        'center-out': CoarseFineSweep,
        'ml': MLGuidedSweep,
        'ml-guided': MLGuidedSweep,
    }

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
        name_lower = name.lower()

        if name_lower not in cls.ALGORITHMS:
            available = ', '.join(cls.ALGORITHMS.keys())
            raise ValueError(
                f"Unknown sweep algorithm: {name}\n"
                f"Available algorithms: {available}"
            )

        AlgorithmClass = cls.ALGORITHMS[name_lower]
        return AlgorithmClass(network)

    @classmethod
    def list_algorithms(cls):
        """List all available algorithms with descriptions

        Returns:
            Dictionary of algorithm info
        """
        info = {}
        for name, AlgorithmClass in cls.ALGORITHMS.items():
            instance = AlgorithmClass(None)
            info[name] = {
                'class_name': instance.name,
                'description': instance.description
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
        return cls.get_algorithm('linear', network)


__all__ = [
    'SweepAlgorithmBase',
    'LinearBruteForceSweep',
    'CoarseFineSweep',
    'MLGuidedSweep',
    'SweepAlgorithmLoader',
    'SweepMLPredictor',
    'MLPredictorLoader',
    'compute_snr',
]
