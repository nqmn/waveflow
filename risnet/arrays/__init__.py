"""Reusable phased-array primitives."""

from .geometry import centered_planar_grid, square_planar_grid
from .quantization import (
    phase_to_state,
    quantization_loss_dB,
    quantize_uniform_phases,
    rms_phase_error,
    state_to_phase,
    uniform_phase_levels,
    wrapped_phase_error,
)
from .steering import (
    linear_steering_phases,
    normalized_array_factor_dB,
    steering_unit_vector,
)

__all__ = [
    "centered_planar_grid",
    "square_planar_grid",
    "phase_to_state",
    "quantization_loss_dB",
    "quantize_uniform_phases",
    "rms_phase_error",
    "state_to_phase",
    "uniform_phase_levels",
    "wrapped_phase_error",
    "linear_steering_phases",
    "normalized_array_factor_dB",
    "steering_unit_vector",
]
