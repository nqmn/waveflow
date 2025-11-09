"""Beam sweep algorithms module

Provides a modular approach to beam sweeping with multiple algorithms available.
Each algorithm is implemented as a separate module and can be loaded dynamically.
"""

from .base import SweepAlgorithmBase
from .linear_brute_force import LinearBruteForceSweep
from .adaptive_center_out import AdaptiveCenterOutSweep
from .beamsweeping import compute_snr, adaptive_center_out_beam_sweep


class SweepAlgorithmLoader:
    """Loader for sweep algorithms"""

    ALGORITHMS = {
        'linear': LinearBruteForceSweep,
        'brute-force': LinearBruteForceSweep,
        'adaptive': AdaptiveCenterOutSweep,
        'center-out': AdaptiveCenterOutSweep,
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
    'AdaptiveCenterOutSweep',
    'SweepAlgorithmLoader',
    'compute_snr',
    'adaptive_center_out_beam_sweep',
]
