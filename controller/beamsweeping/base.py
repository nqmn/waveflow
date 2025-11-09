"""Base class for beam sweep algorithms"""

from abc import ABC, abstractmethod
from contextlib import contextmanager
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
              seed: int = 42, ml_angles=None) -> Dict:
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

    @contextmanager
    def _ap_state_guard(self, ap):
        """Ensure AP adaptation state is restored after each measurement."""
        if ap is None:
            yield
            return

        # Snapshot relevant adaptation fields
        state = {
            'power_dBm': getattr(ap, 'power_dBm', None),
            'current_mcs_index': getattr(ap, 'current_mcs_index', None),
            'power_control_enabled': getattr(ap, 'power_control_enabled', None),
            'rate_adaptation_enabled': getattr(ap, 'rate_adaptation_enabled', None),
            'last_csi_feedback': getattr(ap, 'last_csi_feedback', None),
            'csi_history': list(getattr(ap, 'csi_history', []))
        }

        try:
            yield
        finally:
            if state['power_dBm'] is not None:
                ap.power_dBm = state['power_dBm']
            if state['current_mcs_index'] is not None:
                ap.current_mcs_index = state['current_mcs_index']
            if state['last_csi_feedback'] is not None:
                ap.last_csi_feedback = state['last_csi_feedback']
            if state['csi_history'] is not None:
                ap.csi_history = list(state['csi_history'])

            if state['power_control_enabled'] is not None:
                if hasattr(ap, 'set_power_control_enabled'):
                    ap.set_power_control_enabled(state['power_control_enabled'], user_override=None)
                else:
                    ap.power_control_enabled = state['power_control_enabled']

            if state['rate_adaptation_enabled'] is not None:
                if hasattr(ap, 'set_rate_adaptation_enabled'):
                    ap.set_rate_adaptation_enabled(state['rate_adaptation_enabled'], user_override=None)
                else:
                    ap.rate_adaptation_enabled = state['rate_adaptation_enabled']
