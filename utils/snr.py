"""SNR Calculation Utilities

Provides unified SNR computation for the RIS network simulator.
Handles both high-level (position-based) and low-level (loss-based) calculations.

Used throughout beamforming, beam sweeping, and core network modules.
"""

import numpy as np
from typing import Optional, Union


def compute_snr(
    # Either position-based parameters OR loss-based parameters
    pos1: Optional[np.ndarray] = None,
    pos2: Optional[np.ndarray] = None,
    node1: Optional[str] = None,
    node2: Optional[str] = None,
    beam_angle: Optional[float] = None,
    specular_angle: Optional[float] = None,
    # OR low-level parameters
    tx_power_dbm: Optional[float] = None,
    total_loss_db: Optional[float] = None,
    gain_dbi: Optional[float] = None,
    # Common parameters
    bandwidth_mhz: float = 100.0,
    noise_figure_db: float = 6.0,
    # High-level only parameters
    ris_reflectors: int = 16,
    frequency_ghz: float = 10.0,
    transmit_power_dbm: float = 20.0,
    active_ris_mode: bool = False,
    amplifier_gain: float = 0.0,
    return_db: bool = False,
) -> float:
    """
    Unified SNR computation with flexible input modes.

    Mode 1 - Position-based (detailed calculation):
        Provide: pos1, pos2, node1, node2, beam_angle, specular_angle
        Function calculates path loss, atmospheric loss, and gains

    Mode 2 - Loss-based (simple calculation):
        Provide: tx_power_dbm, total_loss_db, gain_dbi
        Function uses pre-calculated parameters

    Args:
        # Position-based mode:
        pos1: Transmitter position (3D array)
        pos2: Receiver position (3D array)
        node1: Transmitter node type ('AP', 'RIS', etc.)
        node2: Receiver node type ('target', 'RIS', 'H', etc.)
        beam_angle: Steering angle in degrees
        specular_angle: Specular reflection angle in degrees

        # Loss-based mode:
        tx_power_dbm: Transmit power in dBm
        total_loss_db: Total path loss in dB
        gain_dbi: Antenna/array gain in dBi

        # Common:
        bandwidth_mhz: Signal bandwidth in MHz (default: 100)
        noise_figure_db: Receiver noise figure in dB (default: 6)
        return_db: Return SNR in dB (default: False, returns linear)

        # Position-based only:
        ris_reflectors: Number of RIS reflectors (default: 16)
        frequency_ghz: Operating frequency in GHz (default: 10)
        transmit_power_dbm: Transmit power in dBm (default: 20)
        active_ris_mode: RIS amplifier mode (default: False)
        amplifier_gain: RIS amplifier gain in dB (default: 0)

    Returns:
        SNR in linear scale (or dB if return_db=True)
    """

    # Determine which mode we're in
    is_position_mode = pos1 is not None and pos2 is not None and node1 is not None and node2 is not None
    is_loss_mode = tx_power_dbm is not None and total_loss_db is not None and gain_dbi is not None

    if not is_position_mode and not is_loss_mode:
        raise ValueError(
            "Must provide either:\n"
            "  Position mode: pos1, pos2, node1, node2, beam_angle, specular_angle\n"
            "  Loss mode: tx_power_dbm, total_loss_db, gain_dbi"
        )

    if is_position_mode:
        # Position-based mode: calculate everything
        return _compute_snr_from_positions(
            pos1=pos1,
            pos2=pos2,
            node1=node1,
            node2=node2,
            beam_angle=beam_angle,
            specular_angle=specular_angle,
            ris_reflectors=ris_reflectors,
            frequency_ghz=frequency_ghz,
            bandwidth_mhz=bandwidth_mhz,
            transmit_power_dbm=transmit_power_dbm,
            noise_figure_db=noise_figure_db,
            active_ris_mode=active_ris_mode,
            amplifier_gain=amplifier_gain,
            return_db=return_db,
        )
    else:
        # Loss-based mode: use pre-calculated parameters
        return _compute_snr_from_loss(
            tx_power_dbm=tx_power_dbm,
            total_loss_db=total_loss_db,
            gain_dbi=gain_dbi,
            bandwidth_mhz=bandwidth_mhz,
            noise_figure_db=noise_figure_db,
            return_db=return_db,
        )


def _compute_snr_from_loss(
    tx_power_dbm: float,
    total_loss_db: float,
    gain_dbi: float,
    bandwidth_mhz: float = 100.0,
    noise_figure_db: float = 6.0,
    return_db: bool = False,
) -> float:
    """
    Calculate SNR from pre-computed loss and gain parameters.

    This is the simpler, faster path used when loss budgets are already calculated.
    """
    bw_hz = bandwidth_mhz * 1e6
    noise_power_dbm = -174 + 10 * np.log10(bw_hz) + noise_figure_db
    received_power_dbm = tx_power_dbm - total_loss_db + gain_dbi
    snr_db = received_power_dbm - noise_power_dbm

    if return_db:
        return snr_db
    else:
        return 10 ** (snr_db / 10)


def _compute_snr_from_positions(
    pos1: np.ndarray,
    pos2: np.ndarray,
    node1: str,
    node2: str,
    beam_angle: float,
    specular_angle: float,
    ris_reflectors: int = 16,
    frequency_ghz: float = 10.0,
    bandwidth_mhz: float = 100.0,
    transmit_power_dbm: float = 20.0,
    noise_figure_db: float = 6.0,
    active_ris_mode: bool = False,
    amplifier_gain: float = 0.0,
    return_db: bool = False,
) -> float:
    """
    Compute SNR for a given beam angle.

    Calculates path loss, atmospheric loss, gain, and thermal noise.

    Args:
        pos1: Transmitter position (3D array)
        pos2: Receiver position (3D array)
        node1: Transmitter node type ('AP', 'RIS', etc.)
        node2: Receiver node type ('target', 'RIS', 'H', etc.)
        beam_angle: Steering angle in degrees
        specular_angle: Specular reflection angle in degrees
        ris_reflectors: Number of RIS reflectors (NxN array)
        frequency_ghz: Operating frequency in GHz
        bandwidth_mhz: Signal bandwidth in MHz
        transmit_power_dbm: Transmit power in dBm
        noise_figure_db: Noise figure in dB
        active_ris_mode: Whether RIS is in active mode (default: passive RIS)
        amplifier_gain: RIS amplifier gain in dB (only used if active_ris_mode=True)

    Returns:
        SNR in linear scale
    """

    # Calculate distance
    distance = np.linalg.norm(pos2 - pos1)

    if distance < 0.01:
        return 1e-6  # Too close

    # Free-space path loss (dB)
    wavelength = 3e8 / (frequency_ghz * 1e9)  # meters
    path_loss_db = 20 * np.log10(4 * np.pi * distance / wavelength)

    # Atmospheric loss (frequency dependent)
    # Simplified: ~0.5 dB/km at 28 GHz
    atm_loss_db = (distance / 1000) * 0.5

    # Gain calculation
    reflectors_per_dim = max(int(ris_reflectors), 1)
    if reflectors_per_dim > 64:
        # Interpret large values as already representing total elements
        total_elements = reflectors_per_dim
    else:
        total_elements = reflectors_per_dim * reflectors_per_dim
    array_gain_dbi = 10 * np.log10(total_elements)
    insertion_loss = 2.0  # dB
    reflection_loss = 1.0  # dB
    aligned_gain_dbi = array_gain_dbi - insertion_loss - reflection_loss
    misalignment_penalty_db = 10.0  # ≈ -10 dB when off target

    if node1 == 'AP' and node2.startswith('R'):
        # AP→RIS: treat as omnidirectional AP illuminating RIS
        gain_dbi = 3.0
        if active_ris_mode:
            gain_dbi += amplifier_gain

    elif node1.startswith('R') and (node2 == 'H' or node2.startswith('R') or node2 == 'target'):
        # RIS→target/RIS: Blind beam steering - angle matters
        target_angle = np.arctan2(pos2[1] - pos1[1], pos2[0] - pos1[0]) * 180 / np.pi
        target_deflection = target_angle - specular_angle

        # Normalize to [-180, 180]
        while target_deflection > 180:
            target_deflection -= 360
        while target_deflection < -180:
            target_deflection += 360

        # Check alternate direction
        target_deflection_alt = target_deflection
        if abs(target_deflection) > 90:
            target_deflection_alt = target_deflection - 180 if target_deflection > 0 else target_deflection + 180
            if target_deflection_alt < -180:
                target_deflection_alt += 360
            if target_deflection_alt > 180:
                target_deflection_alt -= 360

        # Angle error to target
        angle_error = min(abs(beam_angle - target_deflection),
                         abs(beam_angle - target_deflection_alt))

        # Target within 5° of beam: aligned
        if angle_error < 5:
            gain_dbi = aligned_gain_dbi
            if active_ris_mode:
                gain_dbi += amplifier_gain
        else:
            gain_dbi = aligned_gain_dbi - misalignment_penalty_db
            if active_ris_mode:
                gain_dbi += max(amplifier_gain - misalignment_penalty_db, amplifier_gain * 0.1)

        # RIS→RIS: Apply relay efficiency penalty (~70% efficiency -> -1.55 dB)
        if node2.startswith('R'):
            gain_dbi -= 10 * np.log10(1 / 0.70)

    else:
        # Default: minimal gain
        gain_dbi = 3.0

    # Quantization loss
    quantization_loss_db = 0.5  # dB

    # Total loss
    total_loss_db = path_loss_db + atm_loss_db + quantization_loss_db - gain_dbi

    # Thermal noise
    bw_hz = bandwidth_mhz * 1e6
    noise_power_dbm = -174 + 10 * np.log10(bw_hz) + noise_figure_db

    # SNR calculation
    snr_db = transmit_power_dbm - total_loss_db - noise_power_dbm

    if return_db:
        return snr_db
    else:
        snr_linear = 10 ** (snr_db / 10)
        return max(snr_linear, 1e-6)  # Ensure positive
