"""Equivalence tests for additive phase quantization primitives."""

import numpy as np
import pytest

from controller.ris_phase.phase_quantization import QuantizationAnalyzer, UniformQuantizer
from core.physics import Physics
from risnet.arrays import (
    phase_to_state,
    quantization_loss_dB,
    quantize_uniform_phases,
    rms_phase_error,
    state_to_phase,
    uniform_phase_levels,
    wrapped_phase_error,
)


@pytest.mark.parametrize("bits", [1, 2, 3, 4])
def test_uniform_phase_levels_match_existing_quantizer(bits):
    quantizer = UniformQuantizer(bits)

    levels = uniform_phase_levels(bits)

    np.testing.assert_allclose(levels, quantizer.get_discrete_levels())


@pytest.mark.parametrize("bits", [1, 2, 3, 5])
def test_quantize_uniform_phases_matches_existing_quantizer(bits):
    ideal_phases = np.array(
        [
            -np.pi,
            -0.25,
            0.0,
            0.49 * np.pi,
            np.pi,
            2.1 * np.pi,
            5.75 * np.pi,
        ]
    )
    quantizer = UniformQuantizer(bits)

    quantized, states = quantize_uniform_phases(ideal_phases, bits)
    legacy_quantized, legacy_states = quantizer.quantize(ideal_phases)

    np.testing.assert_allclose(quantized, legacy_quantized)
    np.testing.assert_array_equal(states, legacy_states)


@pytest.mark.parametrize("bits", [1, 2, 4])
@pytest.mark.parametrize("phase_rad", [-0.2, 0.0, np.pi / 2, 2 * np.pi, 8.1])
def test_phase_state_mapping_matches_existing_quantizer(bits, phase_rad):
    quantizer = UniformQuantizer(bits)

    state = phase_to_state(phase_rad, bits)
    phase = state_to_phase(state, bits)

    assert state == quantizer.phase_to_state(phase_rad)
    assert phase == pytest.approx(quantizer.state_to_phase(state))


@pytest.mark.parametrize("bits", [1, 2, 3])
def test_uniform_quantization_matches_physics_quantization(bits):
    ideal_phases = np.linspace(-2 * np.pi, 4 * np.pi, 19)

    quantized, _states = quantize_uniform_phases(ideal_phases, bits)
    legacy = Physics.quantize_phase_to_bits(ideal_phases, bits)

    np.testing.assert_allclose(quantized, legacy)


def test_wrapped_phase_error_matches_current_analyzer_convention():
    ideal_phases = np.array([-0.1, 0.1, 2 * np.pi - 0.1, 4 * np.pi + 0.1])
    quantized_phases = np.array([2 * np.pi - 0.2, 0.0, 0.1, 2 * np.pi])

    error = wrapped_phase_error(ideal_phases, quantized_phases)
    expected = np.angle(np.exp(1j * (ideal_phases - quantized_phases)))

    np.testing.assert_allclose(error, expected)


@pytest.mark.parametrize("bits", [1, 2, 3, 4])
def test_rms_phase_error_matches_existing_analyzer(bits):
    ideal_phases = np.linspace(-np.pi, 3 * np.pi, 33)
    quantized_phases, _states = quantize_uniform_phases(ideal_phases, bits)

    rms_error = rms_phase_error(ideal_phases, quantized_phases)
    legacy = QuantizationAnalyzer.compute_rms_error(ideal_phases, quantized_phases)

    assert rms_error == pytest.approx(legacy)


@pytest.mark.parametrize("model", ["standard", "legacy", "unknown"])
@pytest.mark.parametrize("rms_error_rad", [0.0, 0.05, 0.25, 0.7])
def test_quantization_loss_matches_existing_analyzer(model, rms_error_rad):
    loss = quantization_loss_dB(rms_error_rad, model=model)
    legacy = QuantizationAnalyzer.compute_quantization_loss_db(rms_error_rad, model=model)

    assert loss == pytest.approx(legacy)
