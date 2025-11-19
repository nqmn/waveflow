"""
Example 17: Column/Row Beam Sweeping with RIS Prototype Emulation

This script recreates the main experimental flow of:
    D. Vordonis et al., "Evaluating Beam Sweeping for AoA Estimation with an
    RIS Prototype: Indoor/Outdoor Field Trials," arXiv:2502.10671 (Feb. 2025).

Two high-level goals are mirrored from the paper:
  1) Implement Algorithm 1 (column-row scanning) that iteratively flips RIS
     column pairs and rows to maximize the received power for each Rx angle.
  2) Build a beam-sweeping codebook for both outdoor and indoor deployments,
     then test AoA estimation by executing two live iterations (maximization
     and minimization) of the same algorithm.

Just like example_8_sdr_validation.py, the script is self-contained: it creates
the analytical environment, executes the optimization steps, and prints
detail-rich summaries rather than relying on manual CLI commands.

Usage:
    python examples/script/example_17_beam_sweeping_trials.py
    python examples/script/example_17_beam_sweeping_trials.py --seed 7
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from examples.script.example_16_quantization_codebook import C, WAVELENGTH  # reuse constants


def _expected_mapping(start: int, stop: int, step: int) -> Dict[float, float]:
    return {float(angle): float(angle) for angle in range(start, stop + 1, step)}


PAPER_BEAM_EXPECTATIONS = {
    "Outdoor field trial (Tx=-15°, Rx 0→60°)": {
        "beam_mapping": _expected_mapping(0, 60, 5),
        "iteration_behavior": {"max": 1, "min": -1, "passes": 2},
    },
    "Indoor lab trial (Tx=-15°, Rx 0→45°)": {
        "beam_mapping": {0.0: 0.0, 15.0: 15.0, 30.0: 30.0, 45.0: 45.0},
        "iteration_behavior": {"max": 1, "min": -1, "passes": 2},
    },
}


@dataclass
class Scenario:
    name: str
    tx_angle_deg: float
    rx_angles_deg: List[float]
    nx: int = 32
    ny: int = 64
    multipath_strength: float = 0.0
    coupling_strength: float = 0.0
    noise_power_dBm: float = -70.0
    row_weight: float = 0.3


class BeamEnvironment:
    """Analytical mirror of the measurement setups from the field trials."""

    def __init__(self, scenario: Scenario, seed: int):
        self.scenario = scenario
        self.rng = np.random.default_rng(seed)
        self.spacing = WAVELENGTH / 2.0
        self.k = 2 * np.pi / WAVELENGTH
        self.row_coords = (np.arange(scenario.nx) - (scenario.nx - 1) / 2.0)
        self.col_coords = (np.arange(scenario.ny) - (scenario.ny - 1) / 2.0)
        self.element_scale = 1.0 + 0.03 * self.rng.standard_normal((scenario.nx, scenario.ny))
        self.coupling_mask = (self.rng.standard_normal((scenario.nx, scenario.ny))
                              + 1j * self.rng.standard_normal((scenario.nx, scenario.ny)))
        self.noise_sigma = 10 ** (scenario.noise_power_dBm / 20.0)
        self.cached_steering: Dict[float, np.ndarray] = {}

    def steering_matrix(self, rx_angle_deg: float) -> np.ndarray:
        """Return the Nx×Ny steering matrix for the AoA/AoD pair."""
        if rx_angle_deg in self.cached_steering:
            return self.cached_steering[rx_angle_deg]
        phi_in = np.deg2rad(self.scenario.tx_angle_deg)
        phi_out = np.deg2rad(rx_angle_deg)
        col_phase = -1j * self.k * self.spacing * (np.cos(phi_in) + np.cos(phi_out)) * self.col_coords
        row_phase = -1j * self.k * self.spacing * self.scenario.row_weight * (
            np.sin(phi_in) + np.sin(phi_out)) * self.row_coords
        steering = np.exp(row_phase)[:, None] * np.exp(col_phase)[None, :]
        self.cached_steering[rx_angle_deg] = steering
        return steering

    def _multipath_component(self, rx_angle_deg: float, phasemask: np.ndarray) -> complex:
        """Indoor/outdoor dependent scattered terms."""
        rng = self.rng
        strength = self.scenario.multipath_strength
        if strength <= 0:
            return 0.0
        offsets = [-20.0, -7.5, 12.5, 25.0]
        component = 0.0j
        for idx, off in enumerate(offsets):
            angle = rx_angle_deg + off
            weight = strength / (1 + abs(off) / 10.0)
            steering = self.steering_matrix(angle if angle >= 0 else 0.0)
            phase = np.exp(1j * rng.uniform(0, 2 * np.pi))
            component += weight * np.sum(steering * phasemask) * phase
        return component

    def measure(self, config: np.ndarray, rx_angle_deg: float) -> float:
        """Return received power (dB) for the current RIS configuration."""
        steering = self.steering_matrix(rx_angle_deg)
        phasemask = np.where(config == 0, 1.0 + 0j, -1.0 + 0j)
        coherent = np.sum(self.element_scale * steering * phasemask)
        coupling = self.scenario.coupling_strength * np.sum(self.coupling_mask * phasemask)
        multipath = self._multipath_component(rx_angle_deg, phasemask)
        noise = self.noise_sigma * (self.rng.standard_normal() + 1j * self.rng.standard_normal())
        field = coherent + coupling + multipath + noise
        return 20 * np.log10(abs(field) + 1e-9)


class ColumnRowScanner:
    """Implements Algorithm 1 with column-pair and row-wise toggling."""

    def __init__(self, env: BeamEnvironment):
        self.env = env
        self.nx = env.scenario.nx
        self.ny = env.scenario.ny

    def optimize(self, rx_angle_deg: float, num_starts: int = 5) -> Tuple[np.ndarray, float]:
        """Optimize RIS configuration using multi-start greedy search.

        Args:
            rx_angle_deg: Target reception angle in degrees
            num_starts: Number of random starting configurations to try (default 5)

        Returns:
            (best_config, best_power) tuple across all starts
        """
        best_config = None
        best_power_global = -np.inf

        for trial in range(num_starts):
            if trial == 0:
                config = np.zeros((self.nx, self.ny), dtype=int)
            else:
                config = self.env.rng.integers(0, 2, size=(self.nx, self.ny), dtype=int)

            config, power = self._optimize_greedy(config, rx_angle_deg)

            if power > best_power_global:
                best_power_global = power
                best_config = config.copy()

        return best_config, best_power_global

    def _optimize_greedy(self, config: np.ndarray, rx_angle_deg: float) -> Tuple[np.ndarray, float]:
        """Standard greedy optimization starting from given configuration.

        Args:
            config: Starting RIS configuration
            rx_angle_deg: Target reception angle in degrees

        Returns:
            (optimized_config, final_power) tuple
        """
        best_power = self.env.measure(config, rx_angle_deg)

        for col in range(0, self.ny, 2):
            cols = slice(col, min(col + 2, self.ny))
            config[:, cols] ^= 1
            new_power = self.env.measure(config, rx_angle_deg)
            if new_power > best_power:
                best_power = new_power
            else:
                config[:, cols] ^= 1

        for row in range(self.nx):
            config[row, :] ^= 1
            new_power = self.env.measure(config, rx_angle_deg)
            if new_power > best_power:
                best_power = new_power
            else:
                config[row, :] ^= 1

        return config.copy(), best_power

    def run_iterations(self, rx_angle_deg: float, iterations: int, objective: str) -> List[float]:
        """Execute multiple passes (maximization or minimization)."""
        config = np.zeros((self.nx, self.ny), dtype=int)
        history = []
        best_value = self.env.measure(config, rx_angle_deg)
        history.append(best_value)
        for _ in range(iterations):
            for col in range(0, self.ny, 2):
                cols = slice(col, min(col + 2, self.ny))
                config[:, cols] ^= 1
                new_value = self.env.measure(config, rx_angle_deg)
                condition = new_value > best_value if objective == "max" else new_value < best_value
                if condition:
                    best_value = new_value
                else:
                    config[:, cols] ^= 1
            for row in range(self.nx):
                config[row, :] ^= 1
                new_value = self.env.measure(config, rx_angle_deg)
                condition = new_value > best_value if objective == "max" else new_value < best_value
                if condition:
                    best_value = new_value
                else:
                    config[row, :] ^= 1
            history.append(best_value)
        return history


class BeamSweepingExperiment:
    """End-to-end reproduction of the trial pipeline."""

    def __init__(self, scenario: Scenario, seed: int):
        self.scenario = scenario
        self.env = BeamEnvironment(scenario, seed)
        self.scanner = ColumnRowScanner(self.env)
        self.codebook: Dict[float, Dict[str, object]] = {}

    def build_codebook(self) -> None:
        for angle in self.scenario.rx_angles_deg:
            config, power = self.scanner.optimize(angle)
            self.codebook[angle] = {"config": config, "power": power}

    def summarize_codebook(self) -> None:
        print(f"\n--- {self.scenario.name}: Optimized configurations ---")
        print("Angle (deg)  Max Power (dB)")
        print("----------------------------")
        for angle in self.scenario.rx_angles_deg:
            entry = self.codebook[angle]
            print(f"{angle:10.1f}  {entry['power']:12.3f}")

    def run_beam_sweeping(self, actual_angles: Iterable[float]) -> List[Dict[str, float]]:
        print("\nBeam sweeping / AoA estimation:")
        observations: List[Dict[str, float]] = []
        for actual in actual_angles:
            responses = []
            for beam_angle, entry in self.codebook.items():
                power = self.env.measure(entry["config"], actual)
                responses.append((beam_angle, power))
            best_angle, best_power = max(responses, key=lambda x: x[1])
            normalized = [(ang, p - best_power) for ang, p in responses]
            print(f"  Actual Rx={actual:4.1f}° -> best beam @ {best_angle:4.1f}° "
                  f"(Δ power = {max(abs(p) for _, p in normalized):.2f} dB span)")
            observations.append({"actual": actual, "best": best_angle})
        return observations

    def run_real_time_demo(self, angle: float) -> List[Dict[str, object]]:
        results: List[Dict[str, object]] = []
        for objective in ("max", "min"):
            history = self.scanner.run_iterations(angle, iterations=2, objective=objective)
            label = "Maximization" if objective == "max" else "Minimization"
            deltas = [history[i + 1] - history[i] for i in range(len(history) - 1)]
            print(f"  {label} @ Rx={angle:.1f}° -> "
                  f"history {['{:.2f}'.format(v) for v in history]} (Δ={['{:.2f}'.format(d) for d in deltas]})")
            results.append({"objective": objective, "history": history, "deltas": deltas})
        return results

    def report_paper_alignment(self,
                               sweep_observations: List[Dict[str, float]],
                               iteration_results: List[Dict[str, object]]) -> None:
        print("\nPaper comparison:")
        reference = PAPER_BEAM_EXPECTATIONS.get(self.scenario.name)
        if not reference:
            print("  No captured reference metrics for this scenario.")
            return
        mapping = reference["beam_mapping"]
        for entry in sweep_observations:
            expected = mapping.get(entry["actual"])
            if expected is None:
                continue
            delta = entry["best"] - expected
            print(f"  Beam direction: actual {entry['actual']:.1f}°, "
                  f"paper best={expected:.1f}° vs sim best={entry['best']:.1f}° "
                  f"(Δ={delta:+.1f}°)")
        iter_expect = reference.get("iteration_behavior", {})
        for result in iteration_results:
            expected_passes = iter_expect.get("passes")
            actual_passes = len(result["history"]) - 1
            sign_expect = iter_expect.get(result["objective"])
            consistent = True
            if sign_expect is not None:
                consistent = all((d > 0 if sign_expect > 0 else d < 0) for d in result["deltas"])
            print(f"  {result['objective'].capitalize()} iterations: "
                  f"paper passes={expected_passes}, sim passes={actual_passes}, "
                  f"monotonic={'yes' if consistent else 'no'}")


def run_experiments(seed: int) -> None:
    scenarios = [
        Scenario(
            name="Outdoor field trial (Tx=-15°, Rx 0→60°)",
            tx_angle_deg=-15.0,
            rx_angles_deg=list(np.arange(0, 62.5, 2.5)),
            multipath_strength=0.2,
            coupling_strength=0.05,
            noise_power_dBm=-75.0,
            row_weight=0.15,
        ),
        Scenario(
            name="Indoor lab trial (Tx=-15°, Rx 0→45°)",
            tx_angle_deg=-15.0,
            rx_angles_deg=[0.0, 15.0, 30.0, 45.0],
            multipath_strength=0.6,
            coupling_strength=0.12,
            noise_power_dBm=-65.0,
            row_weight=0.4,
        ),
    ]

    for index, scenario in enumerate(scenarios):
        print("\n" + "=" * 80)
        print(f"{scenario.name}")
        print("=" * 80)
        experiment = BeamSweepingExperiment(scenario, seed + index)
        experiment.build_codebook()
        experiment.summarize_codebook()

        test_angles = scenario.rx_angles_deg[::2] if len(scenario.rx_angles_deg) > 2 else scenario.rx_angles_deg
        sweep_obs = experiment.run_beam_sweeping(test_angles)
        focus_angle = scenario.rx_angles_deg[len(scenario.rx_angles_deg) // 2]
        print("\nReal-time Algorithm 1 iterations (two passes):")
        iteration_results = experiment.run_real_time_demo(focus_angle)
        experiment.report_paper_alignment(sweep_obs, iteration_results)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay column-row beam sweeping from Vordonis et al. (2025).")
    parser.add_argument("--seed", type=int, default=0, help="Seed for deterministic RNG.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_experiments(args.seed)


if __name__ == "__main__":
    main()
