"""RSSI (Received Signal Strength Indicator) Calculation Utilities

Provides unified RSSI computation from various parameters:
- From TX power and losses
- From SNR and noise figure
- Conversion between dBm and linear scales

Used throughout the RIS network simulator for received power analysis.
"""

import numpy as np
from typing import Optional


def compute_rssi_dBm(
    tx_power_dBm: float,
    total_loss_dB: float,
    gain_dBi: float = 0.0,
) -> float:
    """
    Calculate RSSI (received signal strength) in dBm.

    This is the fundamental link budget calculation: received power after
    accounting for path loss, atmospheric loss, and antenna gains.

    Args:
        tx_power_dBm: Transmit power in dBm
        total_loss_dB: Total path loss in dB (positive value)
        gain_dBi: Antenna/array gain in dBi (default 0)

    Returns:
        RSSI in dBm
    """
    rssi_dBm = tx_power_dBm - total_loss_dB + gain_dBi
    return float(rssi_dBm)


def compute_rssi_linear(
    tx_power_dBm: float,
    total_loss_dB: float,
    gain_dBi: float = 0.0,
) -> float:
    """
    Calculate RSSI in linear (watts) scale.

    Args:
        tx_power_dBm: Transmit power in dBm
        total_loss_dB: Total path loss in dB
        gain_dBi: Antenna/array gain in dBi

    Returns:
        RSSI in watts
    """
    rssi_dBm = compute_rssi_dBm(tx_power_dBm, total_loss_dB, gain_dBi)
    rssi_watts = 10 ** (rssi_dBm / 10) / 1000  # Convert dBm to watts
    return float(rssi_watts)


def rssi_from_snr(
    snr_dB: float,
    noise_power_dBm: float,
) -> float:
    """
    Derive RSSI from SNR and noise power.

    RSSI = Noise + SNR (in dB scale)

    Args:
        snr_dB: Signal-to-Noise Ratio in dB
        noise_power_dBm: Noise power floor in dBm

    Returns:
        RSSI in dBm
    """
    rssi_dBm = noise_power_dBm + snr_dB
    return float(rssi_dBm)


def rssi_from_noise_figure(
    tx_power_dBm: float,
    total_loss_dB: float,
    gain_dBi: float,
    snr_dB: float,
    noise_figure_dB: float = 6.0,
) -> float:
    """
    Calculate RSSI using noise figure relationship.

    This accounts for receiver noise figure in the SNR calculation.
    Useful for deriving RSSI when SNR is measured with specific noise figure.

    Args:
        tx_power_dBm: Transmit power in dBm
        total_loss_dB: Total path loss in dB
        gain_dBi: Antenna gain in dBi
        snr_dB: Measured SNR in dB (with receiver noise figure)
        noise_figure_dB: Receiver noise figure in dB (default 6)

    Returns:
        RSSI in dBm
    """
    # RSSI is independent of noise figure - it's just received power
    rssi_dBm = compute_rssi_dBm(tx_power_dBm, total_loss_dB, gain_dBi)
    return float(rssi_dBm)


def convert_rssi_dBm_to_linear(rssi_dBm: float) -> float:
    """
    Convert RSSI from dBm to linear watts.

    Args:
        rssi_dBm: RSSI in dBm

    Returns:
        RSSI in watts
    """
    rssi_watts = 10 ** (rssi_dBm / 10) / 1000
    return float(rssi_watts)


def convert_rssi_linear_to_dBm(rssi_watts: float) -> float:
    """
    Convert RSSI from linear watts to dBm.

    Args:
        rssi_watts: RSSI in watts

    Returns:
        RSSI in dBm
    """
    rssi_dBm = 10 * np.log10(rssi_watts * 1000)
    return float(rssi_dBm)


def rssi_to_power_level(rssi_dBm: float) -> str:
    """
    Classify RSSI into signal strength categories.

    Common classification for wireless signals:
    - Excellent: > -30 dBm
    - Good: -30 to -67 dBm
    - Fair: -67 to -90 dBm
    - Poor: -90 to -110 dBm
    - Very Poor: < -110 dBm

    Args:
        rssi_dBm: RSSI in dBm

    Returns:
        Signal strength category
    """
    if rssi_dBm > -30:
        return "Excellent"
    elif rssi_dBm > -67:
        return "Good"
    elif rssi_dBm > -90:
        return "Fair"
    elif rssi_dBm > -110:
        return "Poor"
    else:
        return "Very Poor"


def compute_snr_from_rssi_and_noise(
    rssi_dBm: float,
    noise_power_dBm: float,
) -> float:
    """
    Calculate SNR from RSSI and noise power floor.

    Inverse of rssi_from_snr: SNR = RSSI - Noise (in dB)

    Args:
        rssi_dBm: Received signal strength in dBm
        noise_power_dBm: Noise power floor in dBm

    Returns:
        SNR in dB
    """
    snr_dB = rssi_dBm - noise_power_dBm
    return float(snr_dB)
