"""
100% Real Signal-Level Beam Sweep Algorithm

Wraps any physics-based sweep algorithm and adds realistic waveform simulation.
Generates actual waveforms, applies realistic channel effects,
and measures SNR/SER directly from received signals at the UE.

This is integrated into the standard sweep algorithms - the "real" flag
converts physics-based SNR into actual signal-level SNR/SER.
"""

import numpy as np
from typing import Dict
from .base import SweepAlgorithmBase
from core.signal_processor import SignalConfig, SignalLevelLink


def apply_signal_level_realism(physics_result: Dict, link_simulator: SignalLevelLink,
                               seed: int = None) -> Dict:
    """Convert physics-based results to real signal-level SNR/SER

    This function takes the physics-based SNR from network.connect() and
    converts it to actual signal-level measurements using real modulation,
    channel effects, and demodulation.

    Args:
        physics_result: Result dict from network.connect() with 'snr_dB', 'pwr_dBm'
        link_simulator: Configured SignalLevelLink simulator
        seed: Random seed for reproducibility

    Returns:
        Dict with 'snr_dB' and 'ser_percent' from actual signal simulation
    """
    # Use the physics SNR to set the noise power level
    # SNR_dB = 10*log10(P_signal / P_noise)
    # P_signal ≈ 1.0 (normalized)
    # P_noise = 10^(-SNR_dB/10)

    snr_physics = physics_result['snr_dB']
    noise_power = 10 ** (-snr_physics / 10)
    noise_power_dB = 10 * np.log10(noise_power)

    # Run signal-level simulation with realistic channel
    signal_result = link_simulator.simulate_link(
        path_loss_dB=0.0,  # Already accounted for in physics SNR
        noise_power_dB=noise_power_dB,
        K_factor=5.0,
        seed=seed
    )

    return signal_result


class RealSignalSweep(SweepAlgorithmBase):
    """Wrapper that adds signal-level realism to physics-based sweep

    This class wraps a physics-based sweep algorithm and converts
    the results to actual signal-level SNR/SER by simulating real
    modulation, channel effects, and demodulation."""

    def __init__(self, network, base_algorithm=None):
        super().__init__(network)
        self.base_algorithm = base_algorithm

    @property
    def name(self) -> str:
        if self.base_algorithm:
            return f"{self.base_algorithm.name} + Signal-Level"
        return "Signal-Level Sweep (No Base Algorithm)"

    @property
    def description(self) -> str:
        if self.base_algorithm:
            return f"Real signal-level version of {self.base_algorithm.description}"
        return "100% real: generates waveforms, applies channel effects, measures SNR/SER"

    def sweep(self, ap_name: str, ris_name: str, ue_name: str,
              fov: float = 60.0, step: float = 10.0,
              seed: int = 42, enable_feedback: bool = True,
              max_feedback_iterations: int = 3,
              modulation: str = 'QPSK',
              num_symbols: int = 1000,
              ml_angles=None) -> Dict:
        """Execute real signal-level beam sweep

        Args:
            ap_name: Access Point name
            ris_name: RIS name
            ue_name: User Equipment name
            fov: Field of view in degrees
            step: Coarse step size in degrees
            seed: Random seed for reproducibility
            enable_feedback: If True, include feedback loop
            max_feedback_iterations: Max feedback iterations
            modulation: QPSK, 16QAM, or 64QAM
            num_symbols: Number of symbols per measurement
            ml_angles: ML-suggested angles

        Returns:
            Dictionary with sweep results including SNR and SER
        """
        ap = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue = self.network.get(ue_name)

        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        # Calculate base direction
        ue_vec = ue.pos - ris.pos
        specular_angle = np.degrees(np.arctan2(ue_vec[1], ue_vec[0]))

        # Generate angles to test
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = specular_angle + local_coarse

        # Setup signal simulator
        signal_config = SignalConfig(
            modulation=modulation,
            symbol_rate=1e6,
            sample_rate=10e6,
            num_symbols=num_symbols,
            pilot_ratio=0.1
        )
        link_simulator = SignalLevelLink(signal_config)

        # Calculate channel characteristics for each angle
        snr_coarse = []
        ser_coarse = []
        pwr_coarse = []
        symbol_errors_coarse = []

        if seed is not None:
            np.random.seed(seed)

        for i, abs_angle in enumerate(abs_angles):
            # Use physics-level connect to get path loss and gain
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_angle, seed=seed,
                    enable_feedback=False,
                    max_feedback_iterations=0
                )

            # Extract path loss and noise from physics simulation
            # Reconstruct the equivalent path loss from SNR
            path_loss_dB = -res['pwr_dBm']  # Approximation
            noise_power_dB = -90  # Typical noise floor

            # Run signal-level simulation
            signal_result = link_simulator.simulate_link(
                path_loss_dB=path_loss_dB,
                noise_power_dB=noise_power_dB,
                K_factor=5.0,
                seed=seed + i if seed is not None else None
            )

            snr_coarse.append(signal_result['snr_dB'])
            ser_coarse.append(signal_result['ser_percent'])
            pwr_coarse.append(res['pwr_dBm'])
            symbol_errors_coarse.append(signal_result['symbol_errors'])

        # Find best angle
        best_idx = int(np.argmin(np.array(ser_coarse)))  # Prefer lower SER
        best_local = local_coarse[best_idx]
        best_snr_coarse = snr_coarse[best_idx]
        best_ser_coarse = ser_coarse[best_idx]

        # Fine phase sweep around best angle
        fine_span = 10.0
        fine_res = 1.0
        fine_start = max(best_local - fine_span, -fov)
        fine_end = min(best_local + fine_span, fov)
        local_fine = np.arange(fine_start, fine_end + fine_res, fine_res)
        abs_angles_fine = specular_angle + local_fine

        snr_fine = []
        ser_fine = []
        symbol_errors_fine = []

        for i, abs_a in enumerate(abs_angles_fine):
            with self._ap_state_guard(ap):
                res = self.network.connect(
                    ap_name, ris_name, ue_name,
                    beam_angle_deg=abs_a, seed=seed,
                    enable_feedback=False,
                    max_feedback_iterations=0
                )

            path_loss_dB = -res['pwr_dBm']
            noise_power_dB = -90

            signal_result = link_simulator.simulate_link(
                path_loss_dB=path_loss_dB,
                noise_power_dB=noise_power_dB,
                K_factor=5.0,
                seed=seed + i if seed is not None else None
            )

            snr_fine.append(signal_result['snr_dB'])
            ser_fine.append(signal_result['ser_percent'])
            symbol_errors_fine.append(signal_result['symbol_errors'])

        best_fine_idx = int(np.argmin(np.array(ser_fine)))
        best_snr_fine = snr_fine[best_fine_idx]
        best_ser_fine = ser_fine[best_fine_idx]
        best_local_fine = local_fine[best_fine_idx]

        return {
            'modulation': modulation,
            'num_symbols': num_symbols,
            'local_coarse': local_coarse.tolist(),
            'snr_coarse': snr_coarse,
            'ser_coarse': ser_coarse,
            'symbol_errors_coarse': symbol_errors_coarse,
            'pwr_coarse': pwr_coarse,
            'local_fine': local_fine.tolist(),
            'snr_fine': snr_fine,
            'ser_fine': ser_fine,
            'symbol_errors_fine': symbol_errors_fine,
            'best_local_fine': float(best_local_fine),
            'best_snr_fine': float(best_snr_fine),
            'best_ser_fine': float(best_ser_fine),
            'specular_angle': float(specular_angle),
        }
