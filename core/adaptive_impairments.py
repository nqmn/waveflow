"""
Adaptive channel impairments based on SNR conditions
Phase noise and CFO scale with link quality
"""

import numpy as np
from typing import Dict
from dataclasses import dataclass


@dataclass
class ImpairmentProfile:
    """Channel impairment levels"""
    snr_threshold_excellent: float = 30.0  # SNR >= 30 dB
    snr_threshold_good: float = 20.0      # SNR >= 20 dB
    snr_threshold_poor: float = 10.0      # SNR >= 10 dB

    # Phase noise std (radians/sample)
    phase_noise_excellent: float = 0.001
    phase_noise_good: float = 0.005
    phase_noise_poor: float = 0.015
    phase_noise_very_poor: float = 0.03

    # CFO (Hz)
    cfo_excellent: float = 10.0
    cfo_good: float = 50.0
    cfo_poor: float = 200.0
    cfo_very_poor: float = 500.0


class AdaptiveChannelImpairments:
    """
    Adapts impairments (phase noise, CFO) based on SNR
    - Good SNR → tight oscillator (low phase noise, CFO)
    - Poor SNR → loose oscillator (high phase noise, CFO)
    Mimics realistic hardware behavior
    """

    def __init__(self, profile: ImpairmentProfile = None):
        """
        Args:
            profile: Impairment profile configuration
        """
        self.profile = profile or ImpairmentProfile()
        self.snr_history = []
        self.max_history = 10

    def record_snr(self, snr_dB: float):
        """Record SNR measurement for trend tracking"""
        self.snr_history.append(float(snr_dB))
        if len(self.snr_history) > self.max_history:
            self.snr_history.pop(0)

    def get_current_snr(self) -> float:
        """Get average SNR from recent measurements"""
        if not self.snr_history:
            return 0.0
        return float(np.mean(self.snr_history))

    def _classify_snr_condition(self, snr_dB: float) -> str:
        """Classify SNR condition"""
        if snr_dB >= self.profile.snr_threshold_excellent:
            return 'excellent'
        elif snr_dB >= self.profile.snr_threshold_good:
            return 'good'
        elif snr_dB >= self.profile.snr_threshold_poor:
            return 'poor'
        else:
            return 'very_poor'

    def get_phase_noise(self, snr_dB: float) -> float:
        """
        Get adaptive phase noise std

        Args:
            snr_dB: Current SNR in dB

        Returns:
            Phase noise standard deviation (radians/sample)
        """
        condition = self._classify_snr_condition(snr_dB)

        mapping = {
            'excellent': self.profile.phase_noise_excellent,
            'good': self.profile.phase_noise_good,
            'poor': self.profile.phase_noise_poor,
            'very_poor': self.profile.phase_noise_very_poor
        }

        return mapping[condition]

    def get_cfo(self, snr_dB: float) -> float:
        """
        Get adaptive CFO

        Args:
            snr_dB: Current SNR in dB

        Returns:
            Carrier frequency offset (Hz)
        """
        condition = self._classify_snr_condition(snr_dB)

        mapping = {
            'excellent': self.profile.cfo_excellent,
            'good': self.profile.cfo_good,
            'poor': self.profile.cfo_poor,
            'very_poor': self.profile.cfo_very_poor
        }

        return mapping[condition]

    def get_impairments(self, snr_dB: float) -> Dict[str, float]:
        """
        Get all adapted impairments for current SNR

        Args:
            snr_dB: Current SNR in dB

        Returns:
            Dict with phase_noise_std, cfo_hz
        """
        return {
            'phase_noise_std': self.get_phase_noise(snr_dB),
            'cfo_hz': self.get_cfo(snr_dB),
            'snr_condition': self._classify_snr_condition(snr_dB)
        }

    def interpolate_linearly(self, snr_dB: float) -> Dict[str, float]:
        """
        Interpolate impairments linearly between thresholds
        Smoother than discrete stepping

        Args:
            snr_dB: Current SNR in dB

        Returns:
            Dict with interpolated impairments
        """
        p = self.profile

        # Determine which interval
        if snr_dB >= p.snr_threshold_excellent:
            alpha = 1.0  # Excellent condition
            phase_noise = p.phase_noise_excellent
            cfo = p.cfo_excellent
            condition = 'excellent'
        elif snr_dB >= p.snr_threshold_good:
            # Interpolate between good and excellent
            alpha = (snr_dB - p.snr_threshold_good) / (p.snr_threshold_excellent - p.snr_threshold_good)
            phase_noise = p.phase_noise_good + alpha * (p.phase_noise_excellent - p.phase_noise_good)
            cfo = p.cfo_good + alpha * (p.cfo_excellent - p.cfo_good)
            condition = 'good'
        elif snr_dB >= p.snr_threshold_poor:
            # Interpolate between poor and good
            alpha = (snr_dB - p.snr_threshold_poor) / (p.snr_threshold_good - p.snr_threshold_poor)
            phase_noise = p.phase_noise_poor + alpha * (p.phase_noise_good - p.phase_noise_poor)
            cfo = p.cfo_poor + alpha * (p.cfo_good - p.cfo_poor)
            condition = 'poor'
        else:
            # Very poor
            phase_noise = p.phase_noise_very_poor
            cfo = p.cfo_very_poor
            condition = 'very_poor'

        return {
            'phase_noise_std': float(phase_noise),
            'cfo_hz': float(cfo),
            'snr_condition': condition,
            'snr_dB': float(snr_dB)
        }


class ChannelQualityMonitor:
    """
    Monitors channel quality and predicts when to increase/decrease impairments
    """

    def __init__(self):
        self.snr_samples = []
        self.max_samples = 20
        self.degradation_threshold = 2.0  # dB drop triggers warning

    def add_measurement(self, snr_dB: float):
        """Add SNR sample"""
        self.snr_samples.append(float(snr_dB))
        if len(self.snr_samples) > self.max_samples:
            self.snr_samples.pop(0)

    def detect_degradation(self) -> bool:
        """Detect if channel quality is degrading"""
        if len(self.snr_samples) < 2:
            return False

        recent_avg = np.mean(self.snr_samples[-5:])
        older_avg = np.mean(self.snr_samples[:-5]) if len(self.snr_samples) > 5 else recent_avg

        degradation = older_avg - recent_avg
        return degradation > self.degradation_threshold

    def get_trend(self) -> str:
        """Get SNR trend"""
        if len(self.snr_samples) < 2:
            return 'stable'

        recent_avg = np.mean(self.snr_samples[-5:])
        older_avg = np.mean(self.snr_samples[:-5]) if len(self.snr_samples) > 5 else recent_avg

        diff = recent_avg - older_avg
        if diff > 1.0:
            return 'improving'
        elif diff < -1.0:
            return 'degrading'
        else:
            return 'stable'

    def get_statistics(self) -> Dict:
        """Get channel quality statistics"""
        if not self.snr_samples:
            return {}

        snr_array = np.array(self.snr_samples)
        return {
            'current_snr_dB': float(snr_array[-1]),
            'mean_snr_dB': float(np.mean(snr_array)),
            'std_snr_dB': float(np.std(snr_array)),
            'min_snr_dB': float(np.min(snr_array)),
            'max_snr_dB': float(np.max(snr_array)),
            'trend': self.get_trend(),
            'num_samples': len(self.snr_samples)
        }
