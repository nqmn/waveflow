"""
Real-time RIS beam tracking algorithm
Adapts RIS phase configuration based on channel measurements
Implements greedy hill-climbing and gradient-based approaches
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class BeamTrackingConfig:
    """Beam tracking configuration"""
    algorithm: str = 'greedy_hill_climb'  # or 'gradient_descent'
    update_interval_symbols: int = 10  # How often to update
    search_resolution_deg: float = 5.0  # Step size for search
    learning_rate: float = 0.1  # For gradient methods
    convergence_threshold_dB: float = 0.5  # SNR improvement threshold
    enable_coarse_fine: bool = True  # Use coarse+fine search


class GreedyHillClimbTracker:
    """
    Greedy hill-climbing beam tracker
    - Measures SNR at current angle and neighbors
    - Steps toward best angle
    - Repeats until convergence
    """

    def __init__(self, ris, search_resolution_deg: float = 5.0,
                 convergence_threshold_dB: float = 0.5):
        """
        Args:
            ris: RIS node
            search_resolution_deg: Step size in degrees
            convergence_threshold_dB: SNR improvement threshold
        """
        self.ris = ris
        self.search_resolution = search_resolution_deg
        self.convergence_threshold = convergence_threshold_dB
        self.current_angle = 0.0
        self.last_snr = -np.inf
        self.iteration_count = 0
        self.converged = False
        self.measurement_history = []
        self.max_history = 50

    def step(self, snr_at_current: float, max_angle: float = 60.0) -> Dict:
        """
        Perform one tracking step

        Args:
            snr_at_current: Measured SNR at current beam angle
            max_angle: Maximum steering angle (RIS capability)

        Returns:
            Tracking step result
        """
        self.iteration_count += 1
        snr_improvement = snr_at_current - self.last_snr

        # Check convergence
        self.converged = snr_improvement < self.convergence_threshold

        # Candidate angles to evaluate
        candidates = [
            (self.current_angle, snr_at_current),  # Current
            (self.current_angle + self.search_resolution, None),  # Right
            (self.current_angle - self.search_resolution, None),  # Left
        ]

        # Clip to valid range
        candidates = [
            (np.clip(angle, -max_angle, max_angle), snr)
            for angle, snr in candidates
        ]

        # Remove duplicates
        candidates = list(dict.fromkeys(candidates))

        result = {
            'iteration': self.iteration_count,
            'current_angle': float(self.current_angle),
            'current_snr_dB': float(snr_at_current),
            'snr_improvement_dB': float(snr_improvement),
            'converged': self.converged,
            'candidates': [
                {'angle': float(a), 'snr': float(s) if s is not None else None}
                for a, s in candidates
            ]
        }

        # Record measurement
        self.measurement_history.append({
            'iteration': self.iteration_count,
            'angle': float(self.current_angle),
            'snr_dB': float(snr_at_current)
        })

        if len(self.measurement_history) > self.max_history:
            self.measurement_history.pop(0)

        self.last_snr = snr_at_current

        return result

    def predict_next_angle(self, measurements: List[Tuple[float, float]]) -> float:
        """
        Predict best next angle from measurements

        Args:
            measurements: List of (angle, snr_dB) tuples

        Returns:
            Next angle to try
        """
        if not measurements:
            return self.current_angle

        # Find best SNR
        best_angle, best_snr = max(measurements, key=lambda x: x[1])

        # If best is different from current, move toward it
        if best_angle != self.current_angle:
            step_direction = np.sign(best_angle - self.current_angle)
            next_angle = self.current_angle + step_direction * self.search_resolution
            self.current_angle = next_angle
        else:
            self.converged = True

        return self.current_angle

    def get_status(self) -> Dict:
        """Get tracker status"""
        if self.measurement_history:
            best_meas = max(self.measurement_history, key=lambda x: x['snr_dB'])
            return {
                'current_angle_deg': float(self.current_angle),
                'best_angle_deg': float(best_meas['angle']),
                'best_snr_dB': float(best_meas['snr_dB']),
                'iterations': self.iteration_count,
                'converged': self.converged,
                'history_length': len(self.measurement_history)
            }
        return {
            'current_angle_deg': float(self.current_angle),
            'iterations': self.iteration_count,
            'converged': self.converged
        }


class GradientDescentTracker:
    """
    Gradient descent beam tracker
    - Estimates SNR gradient w.r.t. beam angle
    - Updates angle in direction of steepest ascent
    - More efficient than grid search
    """

    def __init__(self, ris, learning_rate: float = 0.1,
                 convergence_threshold_dB: float = 0.5,
                 gradient_step_deg: float = 2.0):
        """
        Args:
            ris: RIS node
            learning_rate: Gradient descent step size
            convergence_threshold_dB: SNR improvement threshold
            gradient_step_deg: Angle step for gradient estimation
        """
        self.ris = ris
        self.learning_rate = learning_rate
        self.convergence_threshold = convergence_threshold_dB
        self.gradient_step = gradient_step_deg
        self.current_angle = 0.0
        self.last_snr = -np.inf
        self.iteration_count = 0
        self.converged = False
        self.measurement_history = []
        self.max_history = 50
        self.snr_minus = None  # SNR at (angle - gradient_step)
        self.snr_plus = None   # SNR at (angle + gradient_step)

    def step(self, snr_center: float, snr_minus: Optional[float] = None,
             snr_plus: Optional[float] = None, max_angle: float = 60.0) -> Dict:
        """
        Perform one gradient descent step

        Args:
            snr_center: SNR at current angle
            snr_minus: SNR at (angle - step) for gradient
            snr_plus: SNR at (angle + step) for gradient
            max_angle: Maximum steering angle

        Returns:
            Tracking step result
        """
        self.iteration_count += 1

        # Store gradient measurements
        self.snr_minus = snr_minus
        self.snr_plus = snr_plus

        # Estimate gradient
        if snr_minus is not None and snr_plus is not None:
            # Central difference gradient
            gradient = (snr_plus - snr_minus) / (2 * self.gradient_step)
        else:
            gradient = 0.0

        # Update angle in direction of gradient
        angle_adjustment = self.learning_rate * gradient
        old_angle = self.current_angle
        self.current_angle = old_angle + angle_adjustment
        self.current_angle = np.clip(self.current_angle, -max_angle, max_angle)

        snr_improvement = snr_center - self.last_snr
        self.converged = abs(snr_improvement) < self.convergence_threshold

        result = {
            'iteration': self.iteration_count,
            'old_angle': float(old_angle),
            'new_angle': float(self.current_angle),
            'angle_adjustment_deg': float(angle_adjustment),
            'current_snr_dB': float(snr_center),
            'snr_improvement_dB': float(snr_improvement),
            'estimated_gradient': float(gradient),
            'converged': self.converged
        }

        # Record measurement
        self.measurement_history.append({
            'iteration': self.iteration_count,
            'angle': float(self.current_angle),
            'snr_dB': float(snr_center),
            'gradient': float(gradient)
        })

        if len(self.measurement_history) > self.max_history:
            self.measurement_history.pop(0)

        self.last_snr = snr_center

        return result

    def get_status(self) -> Dict:
        """Get tracker status"""
        if self.measurement_history:
            best_meas = max(self.measurement_history, key=lambda x: x['snr_dB'])
            return {
                'current_angle_deg': float(self.current_angle),
                'best_angle_deg': float(best_meas['angle']),
                'best_snr_dB': float(best_meas['snr_dB']),
                'learning_rate': float(self.learning_rate),
                'iterations': self.iteration_count,
                'converged': self.converged,
                'history_length': len(self.measurement_history)
            }
        return {
            'current_angle_deg': float(self.current_angle),
            'learning_rate': float(self.learning_rate),
            'iterations': self.iteration_count,
            'converged': self.converged
        }


class RealTimeBeamTracker:
    """
    Manages real-time beam tracking for RIS-assisted links
    Supports multiple algorithms and per-link tracking
    """

    def __init__(self, network, config: BeamTrackingConfig = None):
        """
        Args:
            network: RISNetwork instance
            config: Beam tracking configuration
        """
        self.network = network
        self.config = config or BeamTrackingConfig()
        self.trackers = {}  # link_key -> tracker_instance
        self.update_counters = {}  # link_key -> update_count

    def enable_tracking(self, ap_name: str, ris_name: str, ue_name: str,
                       algorithm: str = None) -> Dict:
        """
        Enable beam tracking for a link

        Args:
            ap_name: AP name
            ris_name: RIS name
            ue_name: UE name
            algorithm: Tracking algorithm ('greedy_hill_climb' or 'gradient_descent')

        Returns:
            Tracker initialization status
        """
        ris = self.network.get(ris_name)
        if ris is None:
            raise ValueError(f"RIS not found: {ris_name}")

        algorithm = algorithm or self.config.algorithm
        link_key = f"{ap_name}→{ris_name}→{ue_name}"

        if algorithm == 'greedy_hill_climb':
            tracker = GreedyHillClimbTracker(
                ris, self.config.search_resolution_deg,
                self.config.convergence_threshold_dB
            )
        elif algorithm == 'gradient_descent':
            tracker = GradientDescentTracker(
                ris, self.config.learning_rate,
                self.config.convergence_threshold_dB
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

        self.trackers[link_key] = tracker
        self.update_counters[link_key] = 0

        return {
            'link': link_key,
            'algorithm': algorithm,
            'enabled': True,
            'initial_angle': float(tracker.current_angle)
        }

    def update_beam(self, ap_name: str, ris_name: str, ue_name: str,
                   snr_measurement_dB: float) -> Dict:
        """
        Update beam based on SNR measurement

        Args:
            ap_name: AP name
            ris_name: RIS name
            ue_name: UE name
            snr_measurement_dB: Measured SNR in dB

        Returns:
            Tracking update result
        """
        link_key = f"{ap_name}→{ris_name}→{ue_name}"

        if link_key not in self.trackers:
            raise ValueError(f"Tracking not enabled for: {link_key}")

        tracker = self.trackers[link_key]
        self.update_counters[link_key] += 1

        # Get tracking step
        if isinstance(tracker, GreedyHillClimbTracker):
            result = tracker.step(snr_measurement_dB)
        else:  # GradientDescentTracker
            result = tracker.step(snr_measurement_dB)

        # Update RIS beam angle
        ris = self.network.get(ris_name)
        if ris:
            ris.current_beam_angle = tracker.current_angle

        result['update_count'] = self.update_counters[link_key]

        return result

    def get_all_status(self) -> Dict:
        """Get status of all active trackers"""
        return {
            link_key: tracker.get_status()
            for link_key, tracker in self.trackers.items()
        }

    def disable_tracking(self, ap_name: str = None, ris_name: str = None,
                        ue_name: str = None):
        """Disable tracking for link(s)"""
        if ap_name and ris_name and ue_name:
            link_key = f"{ap_name}→{ris_name}→{ue_name}"
            if link_key in self.trackers:
                del self.trackers[link_key]
                del self.update_counters[link_key]
