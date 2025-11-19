"""
Example 16: Reproducing 1-bit RIS Quantization Beam and Map Fusion Codebook

This script replays the main numerical checks from:
    Y. Liu, F. Gao, and L. Zhang, "Quantization Beam Analysis and Codebook
    Design for One-Bit Reconfigurable Intelligent Surface." (IEEE WCL, Jul. 2024)

Key features reproduced from the letter:
  1) Closed-form corollaries for the quantization-beam directions of a 1-bit ULA.
  2) Map Fusion (MF) codebook construction versus random prephasing and legacy
     1-bit/2-bit codebooks for multi-direction beam switching.
  3) Quantitative comparison of sum capacity across phase quantizers and
     validation of the analytical vs. simulated quantization-beam locations.

The implementation mirrors the structure of example_8_sdr_validation.py:
  * Structured CLI entry point, verbose step-by-step reporting, and deterministic
    numpy-based replay of the original study.
  * Instead of reading a JSON topology, we synthesize the analytical model that
    the paper describes (ULA response with incident and outgoing azimuth angles).

Usage:
    python examples/script/example_16_quantization_codebook.py
    python examples/script/example_16_quantization_codebook.py --seed 42
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# -----------------------------------------------------------------------------
# Array/phase utilities
# -----------------------------------------------------------------------------

C = 3e8  # m/s
DEFAULT_FREQ = 30e9  # 30 GHz carrier used in the paper
WAVELENGTH = C / DEFAULT_FREQ

PAPER_REFERENCES = {
    "quantization_cases": {
        "Random prephasing validation (Fig. 2)": {"phi_out": 120.0, "reported_deg": 39.833},
        "Specular case (Fig. 3)": {"phi_out": 150.0, "reported_deg": 150.000},
    },
    "max_error_deg": 0.15,  # Reported in Fig. 4 caption
    "mf_gain_db": 2.0,  # Map Fusion gain vs random prephasing (Fig. 5 discussion)
}

def array_response(num_elements: int,
                   phi_in_deg: float,
                   phi_out_deg: float,
                   spacing_ratio: float = 0.5) -> np.ndarray:
    """Combined steering vector a_C(φ_out, φ_in) from Eq. (8) (unit norm)."""
    m = np.arange(num_elements)
    d = spacing_ratio * WAVELENGTH
    k = 2 * np.pi / WAVELENGTH
    phase = -1j * k * d * (np.cos(np.deg2rad(phi_in_deg))
                           + np.cos(np.deg2rad(phi_out_deg))) * m
    vec = np.exp(phase)
    return vec / np.sqrt(num_elements)


TYPE0 = np.array([1.0 + 0j, -1.0 + 0j])        # {0, π}
TYPE1 = np.array([0.0 + 1j, 0.0 - 1j])         # {π/2, 3π/2}
TWO_BIT = np.array([
    1.0 + 0j,
    0.0 + 1j,
    -1.0 + 0j,
    0.0 - 1j,
])


def quantize_phases(ideal: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Quantize complex weights to the nearest allowed states."""
    if ideal.size == 0:
        return np.array([], dtype=complex)
    # Broadcast: rows = samples, cols = candidates
    ideal = ideal.reshape(-1, 1)
    diff = np.abs(np.angle(ideal / allowed.reshape(1, -1)))
    indices = np.argmin(diff, axis=1)
    return allowed[indices]


def map_from_quantized(values: np.ndarray) -> np.ndarray:
    """Return z vector (0: type-1 from the paper, 1: type-2)."""
    z = np.zeros(values.size, dtype=int)
    delta_type0 = np.minimum(np.abs(values - TYPE0[0]), np.abs(values - TYPE0[1]))
    delta_type1 = np.minimum(np.abs(values - TYPE1[0]), np.abs(values - TYPE1[1]))
    z[delta_type1 < delta_type0] = 1
    return z


def quantize_with_map(ideal: np.ndarray, z: np.ndarray) -> np.ndarray:
    """Quantize ideal phases when each element is locked to a prephasing type."""
    result = np.empty_like(ideal)
    mask0 = z == 0
    mask1 = ~mask0
    if np.any(mask0):
        result[mask0] = quantize_phases(ideal[mask0], TYPE0)
    if np.any(mask1):
        result[mask1] = quantize_phases(ideal[mask1], TYPE1)
    return result


def fuse_maps(maps: Iterable[np.ndarray]) -> np.ndarray:
    """Mode operation per Eq. (32)."""
    stacked = np.vstack([m for m in maps])
    threshold = stacked.shape[0] / 2.0
    return (np.sum(stacked, axis=0) >= threshold).astype(int)


# -----------------------------------------------------------------------------
# Quantization-beam analytics
# -----------------------------------------------------------------------------

def _safe_arccos(value: float) -> float | None:
    if value < -1.0 or value > 1.0:
        return None
    return float(np.rad2deg(np.arccos(np.clip(value, -1.0, 1.0))))


def quantization_beam_directions(phi_in_deg: float,
                                 phi_main_deg: float,
                                 spacing_ratio: float = 0.5) -> List[float]:
    """Implement Corollaries 1-3 for the quantization-beam direction."""
    gamma_q = -2 * np.cos(np.deg2rad(phi_in_deg)) - np.cos(np.deg2rad(phi_main_deg))
    ratio = spacing_ratio
    solutions: List[float] = []

    def try_add(value: float | None) -> None:
        if value is None:
            return
        if 0.0 <= value <= 180.0:
            solutions.append(value)

    if math.isclose(ratio, 0.5, rel_tol=1e-6, abs_tol=1e-6):
        lambda_over_d = 2.0
        if -3.0 < gamma_q < -1.0:
            try_add(_safe_arccos(gamma_q + lambda_over_d))
        if 1.0 < gamma_q < 3.0:
            try_add(_safe_arccos(gamma_q - lambda_over_d))
        if -1.0 < gamma_q < 1.0:
            try_add(_safe_arccos(gamma_q))
        if math.isclose(abs(gamma_q), 1.0, abs_tol=1e-6) or math.isclose(abs(gamma_q), 3.0, abs_tol=1e-6):
            try_add(0.0)
            try_add(180.0)
        return sorted(set(solutions))

    if ratio < 0.25:
        try_add(_safe_arccos(gamma_q))
        return sorted(set(solutions))

    if 0.25 <= ratio < 0.5:
        try_add(_safe_arccos(gamma_q))
        lambda_over_d = 1.0 / ratio
        if -3.0 < gamma_q < -1.0 and lambda_over_d <= 1 - gamma_q:
            try_add(_safe_arccos(gamma_q + lambda_over_d))
        if 1.0 < gamma_q < 3.0 and lambda_over_d <= 1 + gamma_q:
            try_add(_safe_arccos(gamma_q - lambda_over_d))
        return sorted(set(solutions))

    # Fallback using Eq. (17) search (should not trigger for paper scenarios).
    solutions = []
    k = 2 * np.pi / WAVELENGTH
    d = ratio * WAVELENGTH
    for n in range(-5, 6):
        if n == 0:
            continue
        value = -np.cos(np.deg2rad(phi_main_deg)) - 2 * np.cos(np.deg2rad(phi_in_deg)) - 2 * np.pi * n / (k * d)
        try_add(_safe_arccos(value))
    return sorted(set(solutions))


def evaluate_beampattern(weights: np.ndarray,
                         phi_in_deg: float,
                         phi_grid_deg: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return |c^H a|^2 over the grid."""
    power = []
    for phi_out in phi_grid_deg:
        resp = array_response(weights.size, phi_in_deg, phi_out)
        power.append(np.abs(np.dot(weights, resp)) ** 2)
    return phi_grid_deg, np.array(power)


def extract_main_and_quant_beams(power: np.ndarray,
                                 grid: np.ndarray,
                                 exclude_deg: float = 3.0,
                                 min_prominence: float = 0.05) -> Tuple[float, float]:
    """Extract main and quantization beams with noise-aware peak detection.

    Args:
        power: Beampattern power values
        grid: Angle grid (degrees)
        exclude_deg: Exclusion zone around main beam (degrees)
        min_prominence: Minimum peak prominence relative to main beam (0.0-1.0)

    Returns:
        (main_angle, quant_angle) tuple
    """
    idx_main = int(np.argmax(power))
    main_angle = grid[idx_main]
    main_power = power[idx_main]

    mask = np.ones_like(power, dtype=bool)
    mask[np.abs(grid - main_angle) <= exclude_deg] = False

    if not np.any(mask):
        return main_angle, main_angle

    # Filter peaks by prominence: only report if >= min_prominence of main peak
    min_power_threshold = main_power * min_prominence
    masked_power = power[mask]
    valid_idx = np.where(masked_power >= min_power_threshold)[0]

    if len(valid_idx) == 0:
        # No prominent secondary peak found
        return main_angle, main_angle

    # Find the peak with highest power among valid peaks
    best_local_idx = valid_idx[np.argmax(masked_power[valid_idx])]
    quant_angle = grid[np.where(mask)[0][best_local_idx]]

    return main_angle, quant_angle


# -----------------------------------------------------------------------------
# Map Fusion capacity evaluation
# -----------------------------------------------------------------------------

def build_codebooks(num_elements: int,
                    rx_angles: Iterable[float],
                    phi_in_deg: float,
                    rng: np.random.Generator) -> Dict[str, List[np.ndarray]]:
    """Generate codebooks for 2-bit, traditional 1-bit, random prephasing, MF."""
    rx_angles = list(rx_angles)
    codebooks: Dict[str, List[np.ndarray]] = {key: [] for key in
                                              ("two_bit", "traditional", "random_prephasing", "map_fusion")}

    random_map = rng.integers(0, 2, size=num_elements)
    mrc_vectors = []
    per_angle_maps = []

    for phi_out in rx_angles:
        steering = array_response(num_elements, phi_in_deg, phi_out)
        mrc = np.conj(steering)
        mrc_vectors.append(mrc)
        codebooks["two_bit"].append(quantize_phases(mrc, TWO_BIT))
        codebooks["traditional"].append(quantize_phases(mrc, TYPE0))
        codebooks["random_prephasing"].append(quantize_with_map(mrc, random_map))

        quantized_2bit = quantize_phases(mrc, TWO_BIT)
        per_angle_maps.append(map_from_quantized(quantized_2bit))

    fused_map = fuse_maps(per_angle_maps)

    for mrc in mrc_vectors:
        codebooks["map_fusion"].append(quantize_with_map(mrc, fused_map))

    return codebooks


def sum_capacity(codewords: List[np.ndarray],
                 rx_angles: Iterable[float],
                 phi_in_deg: float,
                 path_loss_dB: float) -> float:
    """Compute Σ log2(1 + SNR_i) with channel covariance Ri = a a^H."""
    total = 0.0
    loss_linear = 10 ** (path_loss_dB / 10.0)
    for cw, phi_out in zip(codewords, rx_angles):
        response = array_response(cw.size, phi_in_deg, phi_out)
        gain = np.abs(np.dot(cw, response)) ** 2
        snr = loss_linear * gain
        total += math.log2(1.0 + snr)
    return total


# -----------------------------------------------------------------------------
# Replay routines
# -----------------------------------------------------------------------------

def run_quantization_validation(seed: int) -> None:
    rng = np.random.default_rng(seed)
    phi_in = 30.0
    num_elements = 256
    spacing_ratio = 0.5
    phi_grid = np.linspace(0.0, 180.0, 7201)  # 0.025° resolution

    print("\n" + "=" * 80)
    print("Example 16: Quantization-Beam Analytics")
    print("=" * 80)
    print(f"Incident angle      : {phi_in:.1f}°")
    print(f"Elements (ULA)      : {num_elements}")
    print(f"Spacing             : {spacing_ratio}·λ (half-wavelength case)")

    cases = [
        ("Random prephasing validation (Fig. 2)", 120.0),
        ("Specular case (Fig. 3)", 150.0),
    ]

    for label, phi_out in cases:
        predicted = quantization_beam_directions(phi_in, phi_out, spacing_ratio)
        steering = array_response(num_elements, phi_in, phi_out, spacing_ratio)
        mrc = np.conj(steering)
        standard = quantize_phases(mrc, TYPE0)
        random_map = rng.integers(0, 2, size=num_elements)
        random_weights = quantize_with_map(mrc, random_map)
        _, power_std = evaluate_beampattern(standard, phi_in, phi_grid)
        _, power_random = evaluate_beampattern(random_weights, phi_in, phi_grid)
        _, quant_std = extract_main_and_quant_beams(power_std, phi_grid)
        _, quant_rand = extract_main_and_quant_beams(power_random, phi_grid)
        print(f"\n[{label}] φ_out={phi_out:.1f}°")
        if predicted:
            print(f"  Predicted quantization beam(s): {', '.join(f'{p:.3f}°' for p in predicted)}")
        else:
            print("  Predicted quantization beam(s): none (only main beam)")
        print(f"  Measured quant beam (standard 1-bit) : {quant_std:.3f}°")
        print(f"  Measured quant beam (random prephase): {quant_rand:.3f}°")
        paper_entry = PAPER_REFERENCES["quantization_cases"].get(label)
        if paper_entry:
            delta = quant_std - paper_entry["reported_deg"]
            print(f"  Reported (paper) quant beam       : {paper_entry['reported_deg']:.3f}° "
                  f"(Δ vs. sim = {delta:+.4f}°)")

    print("\n--- Angular error study (Fig. 4) ---")
    rx_angles = [90, 105, 120, 135, 150, 165]
    errors = []
    for phi_out in rx_angles:
        predicted = quantization_beam_directions(phi_in, phi_out, spacing_ratio)
        steering = array_response(num_elements, phi_in, phi_out)
        weights = quantize_phases(np.conj(steering), TYPE0)
        _, power = evaluate_beampattern(weights, phi_in, phi_grid)
        _, measured = extract_main_and_quant_beams(power, phi_grid)
        note = ""
        if abs(measured - phi_out) < 0.5:
            err = 0.0
            note = " (overlaps with main beam)"
        elif predicted:
            err = min(abs(measured - cand) for cand in predicted)
        else:
            err = abs(measured - phi_out)
        errors.append(err)
        print(f"  φ_out={phi_out:6.1f}° -> quant beam @ {measured:7.3f}° "
              f"(|Δ|={err:.4f}°){note}")
    max_err = max(errors)
    print(f"  Max error over the sweep: {max_err:.4f}° "
          f"(paper upper bound {PAPER_REFERENCES['max_error_deg']:.2f}° "
          f"=> Δ={max_err - PAPER_REFERENCES['max_error_deg']:+.4f}°)")


def run_codebook_capacity(seed: int) -> None:
    rng = np.random.default_rng(seed)
    phi_in = 30.0
    rx_angles = np.linspace(100.0, 140.0, 5)
    element_counts = [64, 128, 256, 512]
    path_losses = [-10.0, -20.0]

    print("\n" + "=" * 80)
    print("Map Fusion vs. Random Prephasing vs. Legacy Codebooks (Fig. 5)")
    print("=" * 80)
    header = "Elements  PathLoss  Two-bit  1-bit  Random  MapFusion"
    print(header)
    print("-" * len(header))
    for m in element_counts:
        codebooks = build_codebooks(m, rx_angles, phi_in, rng)
        for loss in path_losses:
            capacities = {
                "two_bit": sum_capacity(codebooks["two_bit"], rx_angles, phi_in, loss),
                "traditional": sum_capacity(codebooks["traditional"], rx_angles, phi_in, loss),
                "random_prephasing": sum_capacity(codebooks["random_prephasing"], rx_angles, phi_in, loss),
                "map_fusion": sum_capacity(codebooks["map_fusion"], rx_angles, phi_in, loss),
            }
            print(f"{m:8d}  {loss:8.1f}  "
                  f"{capacities['two_bit']:6.3f}  "
                  f"{capacities['traditional']:5.3f}  "
                  f"{capacities['random_prephasing']:6.3f}  "
                  f"{capacities['map_fusion']:9.3f}")
            if m == 256 and abs(loss - (-10.0)) < 1e-6:
                gain_sim = capacities["map_fusion"] - capacities["random_prephasing"]
                gain_paper = PAPER_REFERENCES["mf_gain_db"]
                print(" " * 6 + f"Paper MF gain ≈ {gain_paper:.2f} dB over random (Fig. 5); "
                      f"simulated gain = {gain_sim:.2f} dB "
                      f"(Δ={gain_sim - gain_paper:+.2f} dB)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay Liu et al. (2024) quantization-beam and MF results.")
    parser.add_argument("--seed", type=int, default=0, help="Seed for deterministic numpy RNG.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_quantization_validation(args.seed)
    run_codebook_capacity(args.seed)


if __name__ == "__main__":
    main()
