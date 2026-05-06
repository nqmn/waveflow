"""Steering and array-factor primitives."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np


def steering_unit_vector(angle_deg: float) -> np.ndarray:
    """Return the 2D azimuth steering unit vector as ``(x, y, z)``."""
    angle_rad = np.radians(angle_deg)
    return np.array([np.cos(angle_rad), np.sin(angle_rad), 0.0], dtype=float)


def _relative_positions(
    element_positions: np.ndarray,
    array_center: Optional[Sequence[float]] = None,
) -> np.ndarray:
    positions = np.asarray(element_positions, dtype=float)
    if positions.ndim != 2 or positions.shape[1] != 3:
        raise ValueError("element_positions must have shape (N, 3)")

    if array_center is None:
        return positions - np.mean(positions, axis=0)

    center_vec = np.asarray(array_center, dtype=float)
    if center_vec.shape != (3,):
        raise ValueError("array_center must be a 3D coordinate")
    return positions - center_vec


def linear_steering_phases(
    angle_deg: float,
    wavelength: float,
    element_positions: np.ndarray,
    array_center: Optional[Sequence[float]] = None,
) -> np.ndarray:
    """Compute planar far-field steering phases for an arbitrary element grid.

    This mirrors ``PhaseSteeringEngine.linear_steering_phases`` for explicit
    element positions:

    ``phase_n = -k * dot(relative_position_n, steering_unit_vector) mod 2π``.
    """
    if wavelength <= 0:
        raise ValueError("wavelength must be positive")

    k = 2.0 * np.pi / wavelength
    rel_positions = _relative_positions(element_positions, array_center)
    steering_dir = steering_unit_vector(angle_deg)
    projections = rel_positions[:, 0] * steering_dir[0] + rel_positions[:, 1] * steering_dir[1]
    return (-k * projections) % (2.0 * np.pi)


def normalized_array_factor_dB(
    phases: np.ndarray,
    element_positions: np.ndarray,
    target_angle_deg: float,
    frequency: float,
    weights: Optional[np.ndarray] = None,
    array_center: Optional[Sequence[float]] = None,
) -> float:
    """Return normalized far-field array factor in dB.

    The result is clipped to ``[-60, 0]`` dB and matches the current
    ``Physics.compute_array_factor(..., observation_type='far_field')`` behavior.
    """
    phase_array = np.asarray(phases, dtype=float)
    if phase_array.size == 0:
        return 0.0
    if frequency <= 0:
        raise ValueError("frequency must be positive")

    rel_positions = _relative_positions(element_positions, array_center)
    if rel_positions.shape[0] != phase_array.shape[0]:
        raise ValueError("phases and element_positions must have the same length")

    if weights is None:
        weight_array = np.ones(phase_array.shape[0], dtype=float)
    else:
        weight_array = np.asarray(weights, dtype=float)
        if weight_array.shape[0] != phase_array.shape[0]:
            raise ValueError("weights and phases must have the same length")

    weight_array = weight_array / (np.sum(weight_array) + 1e-10)

    wavelength = 3e8 / frequency
    k = 2.0 * np.pi / wavelength
    observation_dir = steering_unit_vector(target_angle_deg)
    spatial_phase = k * (
        rel_positions[:, 0] * observation_dir[0] + rel_positions[:, 1] * observation_dir[1]
    )
    af_complex = np.sum(weight_array * np.exp(1j * (phase_array + spatial_phase)))

    magnitude = np.clip(np.abs(af_complex), 1e-6, 10.0)
    return float(np.clip(20.0 * np.log10(magnitude), -60.0, 0.0))
