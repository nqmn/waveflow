"""Phase quantization primitives for array calculations."""

from __future__ import annotations

from typing import Literal

import numpy as np


def _validate_bits(bits: int) -> int:
    bits = int(bits)
    if bits < 0:
        raise ValueError("bits must be non-negative")
    return bits


def uniform_phase_levels(bits: int) -> np.ndarray:
    """Return evenly spaced phase levels for a uniform phase shifter."""
    bits = _validate_bits(bits)
    if bits == 0:
        return np.array([], dtype=float)

    num_levels = 2**bits
    phase_step = 2 * np.pi / num_levels
    return np.arange(num_levels, dtype=float) * phase_step


def phase_to_state(phase_rad: float | np.ndarray, bits: int) -> int | np.ndarray:
    """Map phase values to nearest uniform quantization state indices."""
    bits = _validate_bits(bits)
    if bits == 0:
        if np.isscalar(phase_rad):
            return 0
        return np.zeros_like(np.asarray(phase_rad), dtype=int)

    num_levels = 2**bits
    phase_step = 2 * np.pi / num_levels
    states = np.round(np.asarray(phase_rad) / phase_step).astype(int) % num_levels

    if np.isscalar(phase_rad):
        return int(states)
    return states


def state_to_phase(state: int | np.ndarray, bits: int) -> float | np.ndarray:
    """Map uniform quantization state indices to phase values in radians."""
    bits = _validate_bits(bits)
    if bits == 0:
        if np.isscalar(state):
            return 0.0
        return np.zeros_like(np.asarray(state), dtype=float)

    num_levels = 2**bits
    phase_step = 2 * np.pi / num_levels
    phases = (np.asarray(state) % num_levels) * phase_step

    if np.isscalar(state):
        return float(phases)
    return phases


def quantize_uniform_phases(
    ideal_phases: np.ndarray,
    bits: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Quantize phases to nearest evenly spaced phase levels."""
    bits = _validate_bits(bits)
    ideal_phases = np.asarray(ideal_phases)
    if bits == 0:
        return ideal_phases.copy(), np.zeros_like(ideal_phases, dtype=int)

    states = phase_to_state(ideal_phases % (2 * np.pi), bits)
    return state_to_phase(states, bits), states


def wrapped_phase_error(
    ideal_phases: np.ndarray,
    quantized_phases: np.ndarray,
) -> np.ndarray:
    """Return phase error wrapped to [-pi, pi]."""
    return np.angle(np.exp(1j * (np.asarray(ideal_phases) - np.asarray(quantized_phases))))


def rms_phase_error(
    ideal_phases: np.ndarray,
    quantized_phases: np.ndarray,
) -> float:
    """Compute wrapped RMS phase error in radians."""
    error = wrapped_phase_error(ideal_phases, quantized_phases)
    return float(np.sqrt(np.mean(error**2)))


def quantization_loss_dB(
    rms_error_rad: float,
    model: Literal["standard", "legacy"] = "standard",
) -> float:
    """Estimate array gain loss from RMS phase quantization error."""
    if model == "standard":
        if rms_error_rad < 1e-6:
            return 0.0
        loss_linear = np.sinc(rms_error_rad / np.pi) ** 2
        return float(10 * np.log10(max(loss_linear, 1e-6)))

    if model == "legacy":
        return float(-1.67 * (rms_error_rad / (np.pi / 2)) ** 2)

    return quantization_loss_dB(rms_error_rad, model="standard")
