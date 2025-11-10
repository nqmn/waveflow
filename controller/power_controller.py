"""
Real-time power control loop that regulates SNR to target setpoint
Implements closed-loop feedback with adaptation during transmission
"""

import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class PowerControlParams:
    """Power control configuration"""
    target_snr_dB: float = 20.0
    power_min_dBm: float = 10.0
    power_max_dBm: float = 30.0
    step_size_dB: float = 1.0
    convergence_threshold_dB: float = 1.0
    hysteresis_dB: float = 0.5


class SNRRegulator:
    """
    Regulates AP transmit power to maintain target SNR at UE
    - Closed-loop feedback from UE SNR measurements
    - Prevents excess power (and interference) when SNR is good
    - Boosts power when SNR drops
    """

    def __init__(self, ap, params: PowerControlParams = None):
        """
        Args:
            ap: AccessPoint node
            params: Power control parameters
        """
        self.ap = ap
        self.params = params or PowerControlParams()

        # State tracking
        self.last_snr_dB = None
        self.last_power_dBm = ap.power_dBm
        self.iteration_count = 0
        self.converged = False
        self.adaptation_history = []
        self.max_history = 50

    def regulate(self, measured_snr_dB: float) -> Dict:
        """
        Perform one power regulation iteration

        Args:
            measured_snr_dB: Measured SNR at UE (dB)

        Returns:
            Control action dict
        """
        self.last_snr_dB = measured_snr_dB
        self.iteration_count += 1

        # Compute SNR error
        snr_error = self.params.target_snr_dB - measured_snr_dB

        # Apply proportional + integral control
        # P-control: adjust power proportional to error
        p_gain = 0.5  # Power adjustment per dB of error
        power_adjustment = p_gain * snr_error

        # I-control: accumulate past errors to eliminate steady-state offset
        integral_term = 0.0
        if len(self.adaptation_history) > 0:
            errors = [h['snr_error_dB'] for h in self.adaptation_history[-5:]]
            integral_term = 0.1 * np.mean(errors)  # Small integral gain

        total_adjustment = power_adjustment + integral_term

        # Compute new power
        old_power = self.ap.power_dBm
        new_power = old_power + total_adjustment
        new_power = np.clip(new_power, self.params.power_min_dBm, self.params.power_max_dBm)

        # Apply hysteresis to reduce oscillation
        power_change = new_power - old_power
        if abs(power_change) < self.params.hysteresis_dB:
            new_power = old_power
            power_change = 0.0

        # Update AP power
        self.ap.power_dBm = new_power
        self.last_power_dBm = new_power

        # Check convergence
        snr_error_magnitude = abs(snr_error)
        self.converged = snr_error_magnitude < self.params.convergence_threshold_dB

        # Record history
        history_entry = {
            'iteration': self.iteration_count,
            'measured_snr_dB': float(measured_snr_dB),
            'snr_error_dB': float(snr_error),
            'old_power_dBm': float(old_power),
            'new_power_dBm': float(new_power),
            'power_change_dB': float(power_change),
            'p_term_dB': float(power_adjustment),
            'i_term_dB': float(integral_term),
            'converged': self.converged
        }
        self.adaptation_history.append(history_entry)

        # Trim history
        if len(self.adaptation_history) > self.max_history:
            self.adaptation_history.pop(0)

        return history_entry

    def get_status(self) -> Dict:
        """Get current regulator status"""
        return {
            'current_power_dBm': float(self.ap.power_dBm),
            'last_snr_dB': float(self.last_snr_dB) if self.last_snr_dB is not None else None,
            'target_snr_dB': float(self.params.target_snr_dB),
            'converged': self.converged,
            'iterations': self.iteration_count,
            'history_length': len(self.adaptation_history)
        }

    def reset(self):
        """Reset regulator state"""
        self.ap.power_dBm = self.ap.power_dBm_init if hasattr(self.ap, 'power_dBm_init') else 20.0
        self.last_snr_dB = None
        self.iteration_count = 0
        self.converged = False
        self.adaptation_history.clear()


class PowerControlSystem:
    """
    Manages power control for multiple AP-UE links
    Allows per-link power regulation
    """

    def __init__(self, network):
        """
        Args:
            network: RISNetwork instance
        """
        self.network = network
        self.regulators = {}  # link_key -> SNRRegulator

    def enable_regulation(self, ap_name: str, ue_name: str,
                         target_snr_dB: float = 20.0,
                         params: PowerControlParams = None) -> SNRRegulator:
        """
        Enable power control for an AP-UE link

        Args:
            ap_name: AP node name
            ue_name: UE node name
            target_snr_dB: Target SNR setpoint
            params: Power control parameters

        Returns:
            SNRRegulator instance
        """
        ap = self.network.get(ap_name)
        if ap is None:
            raise ValueError(f"AP not found: {ap_name}")

        if params is None:
            params = PowerControlParams(target_snr_dB=target_snr_dB)
        else:
            params.target_snr_dB = target_snr_dB

        link_key = f"{ap_name}→{ue_name}"
        regulator = SNRRegulator(ap, params)
        self.regulators[link_key] = regulator

        return regulator

    def regulate_link(self, ap_name: str, ue_name: str, measured_snr_dB: float) -> Dict:
        """
        Regulate power for a specific link

        Args:
            ap_name: AP node name
            ue_name: UE node name
            measured_snr_dB: Measured SNR at UE

        Returns:
            Control action dict
        """
        link_key = f"{ap_name}→{ue_name}"
        if link_key not in self.regulators:
            raise ValueError(f"Regulation not enabled for link: {link_key}")

        regulator = self.regulators[link_key]
        return regulator.regulate(measured_snr_dB)

    def get_all_status(self) -> Dict:
        """Get status of all active regulators"""
        return {
            link_key: regulator.get_status()
            for link_key, regulator in self.regulators.items()
        }

    def disable_regulation(self, ap_name: str, ue_name: str = None):
        """Disable power control for a link or all links from AP"""
        if ue_name is not None:
            link_key = f"{ap_name}→{ue_name}"
            if link_key in self.regulators:
                self.regulators[link_key].reset()
                del self.regulators[link_key]
        else:
            # Disable all links from this AP
            keys_to_remove = [k for k in self.regulators.keys() if k.startswith(ap_name)]
            for key in keys_to_remove:
                self.regulators[key].reset()
                del self.regulators[key]
