"""Equivalence tests for additive array primitives."""

import numpy as np
import pytest

from controller.ris_phase.phase_steering import PhaseSteeringEngine
from core import RIS
from core.physics import Physics
from risnet.arrays import (
    centered_planar_grid,
    linear_steering_phases,
    normalized_array_factor_dB,
    square_planar_grid,
    steering_unit_vector,
)


def test_square_planar_grid_matches_ris_node_geometry():
    ris = RIS("ris1", 4.0, -2.0, 1.0, N=4, spacing=0.25)

    positions = square_planar_grid(4, 0.25, center=ris.pos)

    np.testing.assert_allclose(positions, ris.element_positions)


def test_centered_planar_grid_matches_phase_steering_synthetic_positions():
    wavelength = 0.1

    positions = centered_planar_grid(5, 5, wavelength / 2.0)
    legacy = PhaseSteeringEngine._synthetic_element_positions(5, wavelength)

    np.testing.assert_allclose(positions, legacy)


@pytest.mark.parametrize(
    "angle_deg, expected",
    [
        (0, np.array([1.0, 0.0, 0.0])),
        (90, np.array([0.0, 1.0, 0.0])),
        (180, np.array([-1.0, 0.0, 0.0])),
    ],
)
def test_steering_unit_vector_uses_current_azimuth_convention(angle_deg, expected):
    np.testing.assert_allclose(steering_unit_vector(angle_deg), expected, atol=1e-12)


@pytest.mark.parametrize("angle_deg", [-60, -15, 0, 35, 90])
def test_linear_steering_phases_match_existing_phase_engine(angle_deg):
    wavelength = 3e8 / 5.8e9
    center = np.array([3.0, 2.0, 0.5])
    positions = square_planar_grid(8, wavelength / 2.0, center=center)

    phases = linear_steering_phases(angle_deg, wavelength, positions, array_center=center)
    legacy = PhaseSteeringEngine.linear_steering_phases(
        angle_deg,
        ris_position=center,
        wavelength=wavelength,
        ris_array_size=8,
        element_positions=positions,
    )

    np.testing.assert_allclose(phases, legacy)


def test_phase_engine_synthetic_positions_are_relative_to_array_center():
    wavelength = 3e8 / 5.8e9

    at_origin = PhaseSteeringEngine.linear_steering_phases(
        25.0,
        ris_position=np.array([0.0, 0.0, 0.0]),
        wavelength=wavelength,
        ris_array_size=4,
    )
    translated = PhaseSteeringEngine.linear_steering_phases(
        25.0,
        ris_position=np.array([15.0, -7.0, 2.0]),
        wavelength=wavelength,
        ris_array_size=4,
    )

    np.testing.assert_allclose(translated, at_origin)


@pytest.mark.parametrize("target_angle_deg", [-45, 0, 30, 75])
def test_normalized_array_factor_matches_existing_physics_helper(target_angle_deg):
    frequency = 10e9
    wavelength = 3e8 / frequency
    center = np.array([5.0, 1.0, 0.0])
    positions = square_planar_grid(6, wavelength / 2.0, center=center)
    phases = linear_steering_phases(30.0, wavelength, positions, array_center=center)

    array_factor = normalized_array_factor_dB(
        phases,
        positions,
        target_angle_deg,
        frequency,
        array_center=center,
    )
    legacy = Physics.compute_array_factor(
        phases,
        positions,
        target_angle_deg,
        frequency,
        ris_position=center,
    )

    assert array_factor == pytest.approx(legacy)
