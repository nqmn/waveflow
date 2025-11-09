"""Base class for beam sweep algorithms"""

from abc import ABC, abstractmethod
from typing import Dict


class SweepAlgorithmBase(ABC):
    """Base class for all sweep algorithms"""

    def __init__(self, network):
        """Initialize sweep algorithm

        Args:
            network: RISNet network object
        """
        self.network = network

    @property
    @abstractmethod
    def name(self) -> str:
        """Return algorithm name"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return algorithm description"""
        pass

    @abstractmethod
    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42) -> Dict:
        """Execute beam sweep

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees
            step: Step size in degrees
            seed: Random seed for reproducibility

        Returns:
            Dictionary with sweep results
        """
        pass

    def get_info(self) -> Dict:
        """Get algorithm information"""
        return {
            'name': self.name,
            'description': self.description
        }
