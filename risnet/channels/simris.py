"""SimRIS-style channel helpers and additive engine adapters.

This module now contains two layers:

1. A deterministic LOS reference slice that matches the published formulas and
   is convenient for closed-form comparison tests.
2. A seeded stochastic channel generator that ports the core SimRIS-style
   H/G/D generation workflow into Python without touching the existing
   `RISNetwork.connect()` path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from .base import ChannelEvaluation


SimRISEnvironment = Literal["indoor", "outdoor"]
SimRISArrayType = Literal["ula", "upa"]

_ELEMENT_GAIN_LINEAR = float(np.pi)
_ELEMENT_PATTERN_Q = 0.285


@dataclass(frozen=True)
class SimRISLoSConfig:
    """Deterministic published-formula subset for SimRIS LOS evaluation."""

    environment: SimRISEnvironment = "indoor"
    scenario: int = 1
    array_type: SimRISArrayType = "ula"
    tx_antennas: int = 1
    rx_antennas: int = 1
    include_direct_path: bool = True
    frequency_GHz: float | None = None
    validate_preflight: bool = False
    error_on_invalid: bool = True


@dataclass(frozen=True)
class SimRISConfig:
    """Seeded stochastic SimRIS-style channel configuration."""

    environment: SimRISEnvironment = "indoor"
    scenario: int = 1
    array_type: SimRISArrayType = "ula"
    tx_antennas: int = 1
    rx_antennas: int = 1
    include_direct_path: bool = True
    frequency_GHz: float | None = None
    num_realizations: int = 1
    seed: int | None = None
    include_nlos: bool = True
    include_shadow_fading: bool = True
    force_tx_ris_los: bool | None = None
    force_ris_rx_los: bool | None = None
    force_direct_los: bool | None = None
    validate_preflight: bool = False
    error_on_invalid: bool = True


@dataclass(frozen=True)
class SimRISValidationResult:
    """Validation result mirroring the published SimRIS GUI checks."""

    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def get_simris_published_geometry(
    *,
    environment: str | int,
    scenario: int,
) -> dict[str, np.ndarray]:
    """Return the published SimRIS GUI recommended geometry for a scenario."""
    environment_key = _normalize_environment(environment)
    if scenario not in (1, 2):
        raise ValueError(f"Unsupported SimRIS scenario: {scenario}")

    presets: dict[tuple[SimRISEnvironment, int], tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]] = {
        ("indoor", 1): ((0.0, 25.0, 2.0), (40.0, 50.0, 2.0), (38.0, 48.0, 1.0)),
        ("indoor", 2): ((0.0, 25.0, 2.0), (70.0, 30.0, 2.0), (70.0, 35.0, 1.0)),
        ("outdoor", 1): ((0.0, 25.0, 20.0), (70.0, 85.0, 10.0), (80.0, 75.0, 1.0)),
        ("outdoor", 2): ((0.0, 25.0, 20.0), (85.0, 40.0, 10.0), (70.0, 65.0, 1.0)),
    }
    tx_xyz, ris_xyz, rx_xyz = presets[(environment_key, scenario)]
    return {
        "tx_xyz": np.asarray(tx_xyz, dtype=float),
        "ris_xyz": np.asarray(ris_xyz, dtype=float),
        "rx_xyz": np.asarray(rx_xyz, dtype=float),
        "environment": environment_key,
        "scenario": int(scenario),
    }


def build_simris_published_network(
    *,
    environment: str | int,
    scenario: int,
    ris_side: int,
    frequency_GHz: float,
    ap_name: str = "ap1",
    ris_name: str = "ris1",
    ue_name: str = "ue1",
    enable_messaging: bool = False,
    power_dBm: float = 0.0,
    bandwidth_MHz: float = 20.0,
    antenna_gain_dBi: float = 0.0,
    noise_figure_dB: float = 6.0,
    bits: int = 0,
    max_angle_deg: float = 180.0,
    normal_angle_deg: float = 0.0,
) -> Any:
    """Build a RISNetwork from a published SimRIS GUI preset geometry."""
    from core import RISNetwork

    geometry = get_simris_published_geometry(environment=environment, scenario=scenario)
    tx_xyz = geometry["tx_xyz"]
    ris_xyz = geometry["ris_xyz"]
    rx_xyz = geometry["rx_xyz"]

    net = RISNetwork(enable_messaging=enable_messaging)
    net.add_ap(
        ap_name,
        float(tx_xyz[0]),
        float(tx_xyz[1]),
        float(tx_xyz[2]),
        power_dBm=power_dBm,
        freq=float(frequency_GHz) * 1.0e9,
        antenna_gain_dBi=antenna_gain_dBi,
        bandwidth_MHz=bandwidth_MHz,
    )
    net.add_ris(
        ris_name,
        float(ris_xyz[0]),
        float(ris_xyz[1]),
        float(ris_xyz[2]),
        N=ris_side,
        bits=bits,
        freq=float(frequency_GHz) * 1.0e9,
        max_angle_deg=max_angle_deg,
        normal_angle_deg=normal_angle_deg,
    )
    net.add_ue(
        ue_name,
        float(rx_xyz[0]),
        float(rx_xyz[1]),
        float(rx_xyz[2]),
        antenna_gain_dBi=antenna_gain_dBi,
        noise_figure_dB=noise_figure_dB,
    )
    return net


def _normalize_environment(environment: str | int) -> SimRISEnvironment:
    if environment in (1, "indoor", "InH", "inh"):
        return "indoor"
    if environment in (2, "outdoor", "UMi", "umi"):
        return "outdoor"
    raise ValueError(f"Unsupported SimRIS environment: {environment!r}")


def _normalize_array_type(array_type: str | int) -> SimRISArrayType:
    if array_type in (1, "ula", "ULA"):
        return "ula"
    if array_type in (2, "upa", "UPA"):
        return "upa"
    raise ValueError(f"Unsupported SimRIS array type: {array_type!r}")


def _validate_square_count(count: int, label: str) -> str | None:
    side = int(round(np.sqrt(count)))
    if side * side != count:
        return f"{label} should be an even square count in SimRIS-style array mode"
    return None


def validate_simris_configuration(
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    *,
    environment: str | int,
    frequency_GHz: float,
    ris_side: int,
    tx_antennas: int = 1,
    rx_antennas: int = 1,
) -> SimRISValidationResult:
    """Mirror the core pre-run checks performed by the published MATLAB GUI."""
    environment_key = _normalize_environment(environment)
    tx_xyz = np.asarray(tx_xyz, dtype=float)
    ris_xyz = np.asarray(ris_xyz, dtype=float)
    rx_xyz = np.asarray(rx_xyz, dtype=float)
    errors: list[str] = []
    warnings: list[str] = []

    ris_elements = int(ris_side) * int(ris_side)
    for label, count in (("N", ris_elements), ("Nt", int(tx_antennas)), ("Nr", int(rx_antennas))):
        message = _validate_square_count(int(count), label)
        if message is not None:
            errors.append(message)

    if not np.isclose(tx_xyz[0], 0.0):
        errors.append("Tx should be on xz plane with x=0")

    if rx_xyz[2] > 2.0:
        errors.append("Rx is a ground user equipment; z should be less than or equal to 2")

    d_tx_ris = float(np.linalg.norm(tx_xyz - ris_xyz))
    d_ris_rx = float(np.linalg.norm(ris_xyz - rx_xyz))
    d_tx_rx = float(np.linalg.norm(tx_xyz - rx_xyz))
    wavelength = _wavelength_m(float(frequency_GHz))
    far_field_condition = ris_elements * wavelength / 2.0

    if environment_key == "indoor" and tx_xyz[2] > 3.0:
        errors.append("Typical Tx height is 2-3 meters for indoor InH Office")
    if environment_key == "outdoor" and tx_xyz[2] > 20.0:
        errors.append("Typical Tx height is 20 meters for outdoor UMi Street Canyon")

    if environment_key == "indoor" and d_ris_rx > 10.0:
        errors.append("Rx is far away from RIS; typical indoor SimRIS range is 8-10 meters")

    if environment_key == "indoor" and d_tx_rx > 75.0:
        errors.append("Typical cell radius max is 75 meters for indoor InH Office")
    if environment_key == "outdoor" and d_tx_rx > 100.0:
        errors.append("Typical cell radius max is 100 meters for outdoor UMi Street Canyon")

    if d_tx_ris < far_field_condition or d_ris_rx < far_field_condition or d_tx_rx < far_field_condition:
        errors.append("Far field condition is not satisfied")

    if environment_key == "outdoor" and (tx_xyz[2] < ris_xyz[2] or tx_xyz[2] < rx_xyz[2]):
        errors.append("Tx should be higher than Rx and RIS for outdoor")

    if float(frequency_GHz) not in (28.0, 73.0):
        warnings.append("Published SimRIS examples and tuned parameters target 28 GHz or 73 GHz")

    return SimRISValidationResult(errors=tuple(errors), warnings=tuple(warnings))


def _maybe_run_preflight_validation(
    *,
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    environment: str | int,
    frequency_GHz: float,
    ris_side: int,
    tx_antennas: int,
    rx_antennas: int,
    validate_preflight: bool,
    error_on_invalid: bool,
) -> SimRISValidationResult | None:
    if not validate_preflight:
        return None
    result = validate_simris_configuration(
        tx_xyz,
        ris_xyz,
        rx_xyz,
        environment=environment,
        frequency_GHz=frequency_GHz,
        ris_side=ris_side,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
    )
    if error_on_invalid and not result.ok:
        raise ValueError("; ".join(result.errors))
    return result


def _wavelength_m(frequency_GHz: float) -> float:
    return 3.0e8 / (frequency_GHz * 1.0e9)


def _path_loss_params(environment: SimRISEnvironment) -> tuple[float, float, float, float, float, float, float]:
    if environment == "indoor":
        return 3.19, 8.29, 0.06, 1.73, 3.02, 0.0, 24.2
    return 3.19, 8.2, 0.0, 1.98, 3.1, 0.0, 24.2


def _cluster_poisson_mean(frequency_GHz: float) -> float:
    return 1.8 if frequency_GHz <= 50.0 else 1.9


def _apply_shadow(value_dB: float, sigma_dB: float, rng: np.random.Generator, include_shadow_fading: bool) -> tuple[float, float]:
    shadow = float(rng.normal(0.0, sigma_dB)) if include_shadow_fading and sigma_dB > 0 else 0.0
    return float(value_dB - shadow), shadow


def _path_gain_linear(
    distance_m: float,
    *,
    frequency_GHz: float,
    environment: SimRISEnvironment,
    is_los: bool,
    rng: np.random.Generator | None = None,
    include_shadow_fading: bool = True,
    shadow_override: float | None = None,
) -> tuple[float, float, float]:
    if distance_m <= 0:
        raise ValueError("distance_m must be positive")

    wavelength = _wavelength_m(frequency_GHz)
    n_nlos, sigma_nlos, b_nlos, n_los, sigma_los, b_los, f0 = _path_loss_params(environment)
    if is_los:
        n_term, sigma_term, b_term = n_los, sigma_los, b_los
    else:
        n_term, sigma_term, b_term = n_nlos, sigma_nlos, b_nlos

    path_gain_dB = (
        -20.0 * np.log10(4.0 * np.pi / wavelength)
        - 10.0 * n_term * (1.0 + b_term * ((frequency_GHz - f0) / f0)) * np.log10(distance_m)
    )
    if shadow_override is not None:
        shadow = float(shadow_override)
        path_gain_dB = float(path_gain_dB - shadow)
    elif rng is not None:
        path_gain_dB, shadow = _apply_shadow(path_gain_dB, sigma_term, rng, include_shadow_fading)
    else:
        shadow = 0.0
    return float(path_gain_dB), float(10.0 ** (path_gain_dB / 10.0)), float(shadow)


def _signed_ratio_angle_deg(numerator: float, denominator: float, sign_source: float) -> float:
    sign = 1.0 if sign_source >= 0 else -1.0
    return float(sign * np.degrees(np.arctan2(abs(numerator), abs(denominator))))


def _signed_asin_angle_deg(opposite: float, hypotenuse: float, sign_source: float) -> float:
    sign = 1.0 if sign_source >= 0 else -1.0
    ratio = 0.0 if hypotenuse <= 0 else np.clip(abs(opposite) / hypotenuse, 0.0, 1.0)
    return float(sign * np.degrees(np.arcsin(ratio)))


def _angles_tx_ris_los(tx_xyz: np.ndarray, ris_xyz: np.ndarray, scenario: int) -> tuple[float, float, float, float]:
    distance = float(np.linalg.norm(tx_xyz - ris_xyz))
    if scenario == 1:
        phi_ris = _signed_ratio_angle_deg(ris_xyz[0] - tx_xyz[0], ris_xyz[1] - tx_xyz[1], ris_xyz[0] - tx_xyz[0])
        theta_ris = _signed_asin_angle_deg(ris_xyz[2] - tx_xyz[2], distance, tx_xyz[2] - ris_xyz[2])
        phi_tx = _signed_ratio_angle_deg(tx_xyz[1] - ris_xyz[1], tx_xyz[0] - ris_xyz[0], tx_xyz[1] - ris_xyz[1])
        theta_tx = _signed_asin_angle_deg(ris_xyz[2] - tx_xyz[2], distance, tx_xyz[2] - ris_xyz[2])
    elif scenario == 2:
        phi_ris = _signed_ratio_angle_deg(ris_xyz[1] - tx_xyz[1], ris_xyz[0] - tx_xyz[0], tx_xyz[1] - ris_xyz[1])
        theta_ris = _signed_asin_angle_deg(ris_xyz[2] - tx_xyz[2], distance, tx_xyz[2] - ris_xyz[2])
        phi_tx = _signed_ratio_angle_deg(ris_xyz[1] - tx_xyz[1], ris_xyz[0] - tx_xyz[0], tx_xyz[1] - ris_xyz[1])
        theta_tx = _signed_asin_angle_deg(ris_xyz[2] - tx_xyz[2], distance, ris_xyz[2] - tx_xyz[2])
    else:
        raise ValueError(f"Unsupported SimRIS scenario: {scenario}")
    return phi_ris, theta_ris, phi_tx, theta_tx


def _angles_ris_rx_los(ris_xyz: np.ndarray, rx_xyz: np.ndarray, scenario: int) -> tuple[float, float, float, float]:
    distance = float(np.linalg.norm(ris_xyz - rx_xyz))
    if scenario == 1:
        phi_ris = _signed_ratio_angle_deg(ris_xyz[0] - rx_xyz[0], ris_xyz[1] - rx_xyz[1], ris_xyz[0] - rx_xyz[0])
        theta_ris = _signed_asin_angle_deg(ris_xyz[2] - rx_xyz[2], distance, rx_xyz[2] - ris_xyz[2])
        phi_rx = _signed_ratio_angle_deg(rx_xyz[1] - ris_xyz[1], rx_xyz[0] - ris_xyz[0], ris_xyz[1] - rx_xyz[1])
        theta_rx = _signed_asin_angle_deg(ris_xyz[2] - rx_xyz[2], distance, ris_xyz[2] - rx_xyz[2])
    elif scenario == 2:
        phi_ris = _signed_ratio_angle_deg(ris_xyz[1] - rx_xyz[1], ris_xyz[0] - rx_xyz[0], rx_xyz[1] - ris_xyz[1])
        theta_ris = _signed_asin_angle_deg(ris_xyz[2] - rx_xyz[2], distance, rx_xyz[2] - ris_xyz[2])
        phi_rx = _signed_ratio_angle_deg(rx_xyz[1] - ris_xyz[1], rx_xyz[0] - ris_xyz[0], rx_xyz[1] - ris_xyz[1])
        theta_rx = _signed_asin_angle_deg(ris_xyz[2] - rx_xyz[2], distance, ris_xyz[2] - rx_xyz[2])
    else:
        raise ValueError(f"Unsupported SimRIS scenario: {scenario}")
    return phi_ris, theta_ris, phi_rx, theta_rx


def _angles_direct_los(tx_xyz: np.ndarray, rx_xyz: np.ndarray) -> tuple[float, float, float, float]:
    distance = float(np.linalg.norm(tx_xyz - rx_xyz))
    phi_tx = _signed_ratio_angle_deg(tx_xyz[1] - rx_xyz[1], tx_xyz[0] - rx_xyz[0], tx_xyz[1] - rx_xyz[1])
    theta_tx = _signed_ratio_angle_deg(tx_xyz[2] - rx_xyz[2], distance, rx_xyz[2] - tx_xyz[2])
    phi_rx = _signed_ratio_angle_deg(tx_xyz[1] - rx_xyz[1], tx_xyz[0] - rx_xyz[0], tx_xyz[1] - rx_xyz[1])
    theta_rx = _signed_ratio_angle_deg(tx_xyz[2] - rx_xyz[2], distance, tx_xyz[2] - rx_xyz[2])
    return phi_tx, theta_tx, phi_rx, theta_rx


def _ris_array_response(side: int, k: float, spacing: float, theta_deg: float, phi_deg: float) -> np.ndarray:
    response = np.zeros(side * side, dtype=np.complex128)
    idx = 0
    sin_theta = np.sin(np.radians(theta_deg))
    sin_phi = np.sin(np.radians(phi_deg))
    cos_theta = np.cos(np.radians(theta_deg))
    for x_idx in range(side):
        for y_idx in range(side):
            response[idx] = np.exp(1j * k * spacing * (x_idx * sin_theta + y_idx * sin_phi * cos_theta))
            idx += 1
    return response


def _linear_array_response(count: int, k: float, spacing: float, phi_deg: float, theta_deg: float) -> np.ndarray:
    response = np.zeros(count, dtype=np.complex128)
    phase_scale = np.sin(np.radians(phi_deg)) * np.cos(np.radians(theta_deg))
    for idx in range(count):
        response[idx] = np.exp(1j * k * spacing * idx * phase_scale)
    return response


def _planar_array_response(side: int, k: float, spacing: float, phi_deg: float, theta_deg: float) -> np.ndarray:
    response = np.zeros(side * side, dtype=np.complex128)
    idx = 0
    sin_phi = np.sin(np.radians(phi_deg))
    cos_theta = np.cos(np.radians(theta_deg))
    sin_theta = np.sin(np.radians(theta_deg))
    for x_idx in range(side):
        for y_idx in range(side):
            response[idx] = np.exp(1j * k * spacing * (x_idx * sin_phi * cos_theta + y_idx * sin_theta))
            idx += 1
    return response


def _terminal_array_response(count: int, array_type: SimRISArrayType, k: float, spacing: float, phi_deg: float, theta_deg: float) -> np.ndarray:
    if count <= 0:
        raise ValueError("Antenna count must be positive")
    if count == 1:
        return np.ones(1, dtype=np.complex128)
    if array_type == "ula":
        return _linear_array_response(count, k, spacing, phi_deg, theta_deg)
    side = int(round(np.sqrt(count)))
    if side * side != count:
        raise ValueError("UPA terminal arrays require a square antenna count")
    return _planar_array_response(side, k, spacing, phi_deg, theta_deg)


def _ris_pattern_linear(theta_deg: float) -> float:
    return float(_ELEMENT_GAIN_LINEAR * (np.cos(np.radians(theta_deg)) ** (2.0 * _ELEMENT_PATTERN_Q)))


def _sample_binary(rng: np.random.Generator, probability: float) -> int:
    return int(rng.choice([1, 0], p=[probability, 1.0 - probability]))


def _sample_los_indicator(
    environment: SimRISEnvironment,
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    distance: float,
    rng: np.random.Generator,
    *,
    force: bool | None = None,
) -> int:
    if force is not None:
        return int(bool(force))

    z_tx = float(tx_xyz[2])
    z_ris = float(ris_xyz[2])
    if environment == "indoor":
        if z_ris >= z_tx:
            return 1
        if distance <= 1.2:
            p_los = 1.0
        elif distance < 6.5:
            p_los = float(np.exp(-(distance - 1.2) / 4.7))
        else:
            p_los = float(0.32 * np.exp(-(distance - 6.5) / 32.6))
        return _sample_binary(rng, p_los)

    p_los = float(min(20.0 / distance, 1.0) * (1.0 - np.exp(-distance / 39.0)) + np.exp(-distance / 39.0))
    return _sample_binary(rng, p_los)


def _sample_direct_los_indicator(
    environment: SimRISEnvironment,
    tx_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    d_tx_rx: float,
    rng: np.random.Generator,
    *,
    force: bool | None = None,
    inherited_tx_ris_los: int | None = None,
) -> int:
    if force is not None:
        return int(bool(force))

    if environment == "indoor":
        if ris_xyz[2] >= tx_xyz[2]:
            if d_tx_rx <= 1.2:
                p_los = 1.0
            elif d_tx_rx < 6.5:
                p_los = float(np.exp(-(d_tx_rx - 1.2) / 4.7))
            else:
                p_los = float(0.32 * np.exp(-(d_tx_rx - 6.5) / 32.6))
            return _sample_binary(rng, p_los)
        return int(inherited_tx_ris_los or 0)

    p_los = float(min(20.0 / d_tx_rx, 1.0) * (1.0 - np.exp(-d_tx_rx / 39.0)) + np.exp(-d_tx_rx / 39.0))
    return _sample_binary(rng, p_los)


def _sample_logistic_angles(rng: np.random.Generator, count: int, phi_mean_deg: float, theta_mean_deg: float) -> tuple[np.ndarray, np.ndarray]:
    if count <= 0:
        return np.empty(0), np.empty(0)
    phi = rng.logistic(loc=phi_mean_deg, scale=np.sqrt(25.0 / 2.0), size=count)
    theta = rng.logistic(loc=theta_mean_deg, scale=np.sqrt(25.0 / 2.0), size=count)
    return phi, theta


def _sample_random_rx_angles(rng: np.random.Generator) -> tuple[float, float]:
    """Sample Rx AoA angles using the MATLAB SimRIS-style random logistic model."""
    phi_mean = float(rng.uniform(-90.0, 90.0))
    theta_mean = float(rng.uniform(-90.0, 90.0))
    phi, theta = _sample_logistic_angles(rng, 1, phi_mean, theta_mean)
    return float(phi[0]), float(theta[0])


def _generate_tx_side_scatterers(
    source_xyz: np.ndarray,
    target_xyz: np.ndarray,
    *,
    environment: SimRISEnvironment,
    frequency_GHz: float,
    rng: np.random.Generator,
) -> dict[str, Any]:
    d_source_target = float(np.linalg.norm(source_xyz - target_xyz))
    lambda_p = _cluster_poisson_mean(frequency_GHz)

    for _ in range(100):
        cluster_count = max(1, int(rng.poisson(lambda_p)))
        subrays_per_cluster = rng.integers(1, 31, size=cluster_count)

        phi_all: list[float] = []
        theta_all: list[float] = []
        cluster_distances = 1.0 + rng.random(cluster_count) * max(d_source_target - 1.0, 1e-6)
        cluster_means: list[tuple[float, float]] = []

        for idx in range(cluster_count):
            phi_mean = float(rng.uniform(-90.0, 90.0))
            theta_mean = float(rng.uniform(-45.0, 45.0))
            cluster_means.append((phi_mean, theta_mean))
            phi_cluster, theta_cluster = _sample_logistic_angles(
                rng, int(subrays_per_cluster[idx]), phi_mean, theta_mean
            )
            phi_all.extend(phi_cluster.tolist())
            theta_all.extend(theta_cluster.tolist())

        phi_all_arr = np.asarray(phi_all, dtype=float)
        theta_all_arr = np.asarray(theta_all, dtype=float)

        if environment == "indoor":
            room = np.array([75.0, 50.0, 3.5], dtype=float)
        else:
            room = None

        cluster_positions = np.zeros((cluster_count, 3), dtype=float)
        for idx, (phi_mean, theta_mean) in enumerate(cluster_means):
            distance = cluster_distances[idx]
            for _ in range(256):
                pos = np.array(
                    [
                        source_xyz[0] + distance * np.cos(np.radians(theta_mean)) * np.cos(np.radians(phi_mean)),
                        source_xyz[1] - distance * np.cos(np.radians(theta_mean)) * np.sin(np.radians(phi_mean)),
                        source_xyz[2] + distance * np.sin(np.radians(theta_mean)),
                    ],
                    dtype=float,
                )
                if environment == "indoor":
                    inside = bool(np.all(pos >= 0.0) and pos[0] <= room[0] and pos[1] <= room[1] and pos[2] <= room[2])
                    if not inside and distance <= 1e-6:
                        pos = np.clip(source_xyz, np.zeros(3, dtype=float), room)
                        distance = 0.0
                        inside = True
                else:
                    inside = bool(pos[2] >= 0.0)
                    if not inside and distance <= 1e-6:
                        pos = np.array(source_xyz, dtype=float)
                        pos[2] = max(pos[2], 0.0)
                        distance = 0.0
                        inside = True
                if inside:
                    break
                distance *= 0.8
            else:
                raise RuntimeError("Failed to project SimRIS Tx-side cluster inside the supported bounds")
            cluster_distances[idx] = distance
            cluster_positions[idx] = pos

        repeated_distances = np.repeat(cluster_distances, subrays_per_cluster)
        scatterers = np.zeros((len(repeated_distances), 3), dtype=float)
        for idx in range(len(repeated_distances)):
            scatterers[idx] = np.array(
                [
                    source_xyz[0] + repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.cos(np.radians(phi_all_arr[idx])),
                    source_xyz[1] - repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.sin(np.radians(phi_all_arr[idx])),
                    source_xyz[2] + repeated_distances[idx] * np.sin(np.radians(theta_all_arr[idx])),
                ],
                dtype=float,
            )

        if environment == "indoor":
            mask = (
                (scatterers[:, 0] >= 0.0)
                & (scatterers[:, 0] <= room[0])
                & (scatterers[:, 1] >= 0.0)
                & (scatterers[:, 1] <= room[1])
                & (scatterers[:, 2] >= 0.0)
                & (scatterers[:, 2] <= room[2])
            )
        else:
            mask = scatterers[:, 2] >= 0.0

        active_indices = np.flatnonzero(mask)
        if active_indices.size > 0:
            return {
                "scatterers": scatterers,
                "phi_source": phi_all_arr,
                "theta_source": theta_all_arr,
                "a_rep": repeated_distances,
                "active_indices": active_indices,
                "m_new": int(active_indices.size),
                "cluster_count": int(cluster_count),
                "subrays_per_cluster": np.asarray(subrays_per_cluster, dtype=int),
            }

    raise RuntimeError("Failed to generate active scatterers for SimRIS link")


def _generate_ris_side_scatterers(
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    *,
    environment: SimRISEnvironment,
    frequency_GHz: float,
    scenario: int,
    rng: np.random.Generator,
) -> dict[str, Any]:
    d_ris_rx = float(np.linalg.norm(ris_xyz - rx_xyz))
    lambda_p = _cluster_poisson_mean(frequency_GHz)

    for _ in range(100):
        cluster_count = max(1, int(rng.poisson(lambda_p)))
        subrays_per_cluster = rng.integers(1, 31, size=cluster_count)

        phi_all: list[float] = []
        theta_all: list[float] = []
        cluster_distances = 1.0 + rng.random(cluster_count) * max(d_ris_rx - 1.0, 1e-6)
        cluster_means: list[tuple[float, float]] = []

        for idx in range(cluster_count):
            phi_mean = float(rng.uniform(-45.0, 45.0))
            theta_mean = float(rng.uniform(-45.0, 45.0))
            cluster_means.append((phi_mean, theta_mean))
            phi_cluster, theta_cluster = _sample_logistic_angles(
                rng, int(subrays_per_cluster[idx]), phi_mean, theta_mean
            )
            phi_all.extend(phi_cluster.tolist())
            theta_all.extend(theta_cluster.tolist())

        phi_all_arr = np.asarray(phi_all, dtype=float)
        theta_all_arr = np.asarray(theta_all, dtype=float)

        cluster_positions = np.zeros((cluster_count, 3), dtype=float)
        for idx, (phi_mean, theta_mean) in enumerate(cluster_means):
            distance = cluster_distances[idx]
            for _ in range(256):
                if scenario == 1:
                    pos = np.array(
                        [
                            ris_xyz[0] - distance * np.cos(np.radians(theta_mean)) * np.sin(np.radians(phi_mean)),
                            ris_xyz[1] - distance * np.cos(np.radians(theta_mean)) * np.cos(np.radians(phi_mean)),
                            ris_xyz[2] + distance * np.sin(np.radians(theta_mean)),
                        ],
                        dtype=float,
                    )
                else:
                    pos = np.array(
                        [
                            ris_xyz[0] - distance * np.cos(np.radians(theta_mean)) * np.cos(np.radians(phi_mean)),
                            ris_xyz[1] + distance * np.cos(np.radians(theta_mean)) * np.sin(np.radians(phi_mean)),
                            ris_xyz[2] + distance * np.sin(np.radians(theta_mean)),
                        ],
                        dtype=float,
                    )
                if pos[2] >= 0.0:
                    break
                if distance <= 1e-6:
                    pos = np.array(ris_xyz, dtype=float)
                    pos[2] = max(pos[2], 0.0)
                    distance = 0.0
                    break
                distance *= 0.8
            else:
                raise RuntimeError("Failed to project SimRIS RIS-side cluster above ground")
            cluster_distances[idx] = distance
            cluster_positions[idx] = pos

        repeated_distances = np.repeat(cluster_distances, subrays_per_cluster)
        scatterers = np.zeros((len(repeated_distances), 3), dtype=float)
        for idx in range(len(repeated_distances)):
            if scenario == 1:
                scatterers[idx] = np.array(
                    [
                        ris_xyz[0] - repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.sin(np.radians(phi_all_arr[idx])),
                        ris_xyz[1] - repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.cos(np.radians(phi_all_arr[idx])),
                        ris_xyz[2] + repeated_distances[idx] * np.sin(np.radians(theta_all_arr[idx])),
                    ],
                    dtype=float,
                )
            else:
                scatterers[idx] = np.array(
                    [
                        ris_xyz[0] - repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.cos(np.radians(phi_all_arr[idx])),
                        ris_xyz[1] + repeated_distances[idx] * np.cos(np.radians(theta_all_arr[idx])) * np.sin(np.radians(phi_all_arr[idx])),
                        ris_xyz[2] + repeated_distances[idx] * np.sin(np.radians(theta_all_arr[idx])),
                    ],
                    dtype=float,
                )

        active_indices = np.flatnonzero(scatterers[:, 2] >= 0.0)
        if active_indices.size > 0:
            return {
                "scatterers": scatterers,
                "phi_ris_side": phi_all_arr,
                "theta_ris_side": theta_all_arr,
                "a_rep": repeated_distances,
                "active_indices": active_indices,
                "m_new": int(active_indices.size),
                "cluster_count": int(cluster_count),
                "subrays_per_cluster": np.asarray(subrays_per_cluster, dtype=int),
            }

    raise RuntimeError("Failed to generate active RIS-side scatterers for SimRIS link")


def _complex_gaussian(rng: np.random.Generator) -> complex:
    return complex((rng.normal() + 1j * rng.normal()) / np.sqrt(2.0))


def _generate_tx_ris_channel(
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    *,
    environment: SimRISEnvironment,
    scenario: int,
    frequency_GHz: float,
    array_type: SimRISArrayType,
    ris_side: int,
    tx_antennas: int,
    include_nlos: bool,
    include_shadow_fading: bool,
    force_los: bool | None,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, Any]]:
    wavelength = _wavelength_m(frequency_GHz)
    k = 2.0 * np.pi / wavelength
    spacing = wavelength / 2.0

    d_tx_ris = float(np.linalg.norm(tx_xyz - ris_xyz))
    los_indicator = _sample_los_indicator(environment, tx_xyz, ris_xyz, d_tx_ris, rng, force=force_los)
    h_los = np.zeros((ris_side * ris_side, tx_antennas), dtype=np.complex128)
    metadata: dict[str, Any] = {"los_indicator": los_indicator, "distance_m": d_tx_ris}

    if los_indicator == 1:
        phi_ris, theta_ris, phi_tx, theta_tx = _angles_tx_ris_los(tx_xyz, ris_xyz, scenario)
        a_ris = _ris_array_response(ris_side, k, spacing, theta_ris, phi_ris)
        a_tx = _terminal_array_response(tx_antennas, array_type, k, spacing, phi_tx, theta_tx)
        path_gain_dB, path_gain_linear, _ = _path_gain_linear(
            d_tx_ris,
            frequency_GHz=frequency_GHz,
            environment=environment,
            is_los=True,
            rng=rng,
            include_shadow_fading=include_shadow_fading,
        )
        h_los = (
            np.sqrt(path_gain_linear * _ris_pattern_linear(theta_ris))
            * np.outer(a_ris, a_tx)
            * np.exp(1j * rng.random() * 2.0 * np.pi)
        )
        metadata["los_angles"] = (phi_ris, theta_ris, phi_tx, theta_tx)
        metadata["los_path_gain_dB"] = float(path_gain_dB)
        metadata["los_path_gain_linear"] = float(path_gain_linear)

    h_nlos = np.zeros_like(h_los)
    if include_nlos:
        scatter_data = _generate_tx_side_scatterers(
            tx_xyz, ris_xyz, environment=environment, frequency_GHz=frequency_GHz, rng=rng
        )
        phi_cs_ris = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        theta_cs_ris = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        phi_tx_cs = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        theta_tx_cs = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        shadow = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        beta = np.zeros(scatter_data["scatterers"].shape[0], dtype=np.complex128)

        for idx in scatter_data["active_indices"]:
            scatter = scatter_data["scatterers"][idx]
            b_cs = float(np.linalg.norm(ris_xyz - scatter))
            d_cs = float(scatter_data["a_rep"][idx] + b_cs)
            if scenario == 1:
                phi_cs_ris[idx] = _signed_ratio_angle_deg(ris_xyz[0] - scatter[0], ris_xyz[1] - scatter[1], ris_xyz[0] - scatter[0])
                theta_cs_ris[idx] = _signed_asin_angle_deg(ris_xyz[2] - scatter[2], b_cs, scatter[2] - ris_xyz[2])
                phi_tx_cs[idx] = _signed_ratio_angle_deg(scatter[1] - tx_xyz[1], scatter[0] - tx_xyz[0], tx_xyz[1] - scatter[1])
                theta_tx_cs[idx] = _signed_asin_angle_deg(scatter[2] - tx_xyz[2], scatter_data["a_rep"][idx], scatter[2] - tx_xyz[2])
            else:
                phi_cs_ris[idx] = _signed_ratio_angle_deg(ris_xyz[1] - scatter[1], ris_xyz[0] - scatter[0], scatter[1] - ris_xyz[1])
                theta_cs_ris[idx] = _signed_asin_angle_deg(ris_xyz[2] - scatter[2], b_cs, scatter[2] - ris_xyz[2])
                phi_tx_cs[idx] = _signed_ratio_angle_deg(scatter[1] - tx_xyz[1], scatter[0] - tx_xyz[0], tx_xyz[1] - scatter[1])
                theta_tx_cs[idx] = _signed_asin_angle_deg(scatter[2] - tx_xyz[2], scatter_data["a_rep"][idx], scatter[2] - tx_xyz[2])

            a_ris_cs = _ris_array_response(ris_side, k, spacing, theta_cs_ris[idx], phi_cs_ris[idx])
            a_tx_cs = _terminal_array_response(tx_antennas, array_type, k, spacing, phi_tx_cs[idx], theta_tx_cs[idx])
            _, path_gain_linear, shadow[idx] = _path_gain_linear(
                d_cs,
                frequency_GHz=frequency_GHz,
                environment=environment,
                is_los=False,
                rng=rng,
                include_shadow_fading=include_shadow_fading,
            )
            beta[idx] = _complex_gaussian(rng)
            h_nlos += (
                beta[idx]
                * np.sqrt(_ris_pattern_linear(theta_cs_ris[idx]) * path_gain_linear)
                * np.outer(a_ris_cs, a_tx_cs)
            )

        h_nlos *= np.sqrt(1.0 / max(scatter_data["m_new"], 1))
        metadata["shared_scatterers"] = scatter_data
        metadata["shared_beta"] = beta
        metadata["shared_shadow"] = shadow
        metadata["nlos_cluster_count"] = int(scatter_data["cluster_count"])
        metadata["nlos_subray_count"] = int(np.sum(scatter_data["subrays_per_cluster"]))
        metadata["nlos_active_scatterer_count"] = int(scatter_data["m_new"])

    return h_los + h_nlos, metadata


def _generate_ris_rx_channel(
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    *,
    environment: SimRISEnvironment,
    scenario: int,
    frequency_GHz: float,
    array_type: SimRISArrayType,
    ris_side: int,
    rx_antennas: int,
    include_nlos: bool,
    include_shadow_fading: bool,
    force_los: bool | None,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, Any]]:
    wavelength = _wavelength_m(frequency_GHz)
    k = 2.0 * np.pi / wavelength
    spacing = wavelength / 2.0

    d_ris_rx = float(np.linalg.norm(ris_xyz - rx_xyz))
    if environment == "indoor":
        los_indicator = 1 if force_los is None else int(bool(force_los))
    else:
        los_indicator = _sample_los_indicator(environment, rx_xyz, ris_xyz, d_ris_rx, rng, force=force_los)

    g_los = np.zeros((ris_side * ris_side, rx_antennas), dtype=np.complex128)
    metadata: dict[str, Any] = {"los_indicator": los_indicator, "distance_m": d_ris_rx}

    if los_indicator == 1:
        phi_ris, theta_ris, _, _ = _angles_ris_rx_los(ris_xyz, rx_xyz, scenario)
        phi_rx, theta_rx = _sample_random_rx_angles(rng)
        a_ris = _ris_array_response(ris_side, k, spacing, theta_ris, phi_ris)
        a_rx = _terminal_array_response(rx_antennas, array_type, k, spacing, phi_rx, theta_rx)
        path_gain_dB, path_gain_linear, _ = _path_gain_linear(
            d_ris_rx,
            frequency_GHz=frequency_GHz,
            environment=environment,
            is_los=True,
            rng=rng,
            include_shadow_fading=include_shadow_fading,
        )
        g_los = (
            np.sqrt(path_gain_linear * _ris_pattern_linear(theta_ris))
            * np.outer(a_ris, a_rx)
            * np.exp(1j * rng.random() * 2.0 * np.pi)
        )
        metadata["los_angles"] = (phi_ris, theta_ris, phi_rx, theta_rx)
        metadata["los_path_gain_dB"] = float(path_gain_dB)
        metadata["los_path_gain_linear"] = float(path_gain_linear)

    g_nlos = np.zeros_like(g_los)
    if environment == "outdoor" and include_nlos:
        scatter_data = _generate_ris_side_scatterers(
            ris_xyz, rx_xyz, environment=environment, frequency_GHz=frequency_GHz, scenario=scenario, rng=rng
        )
        phi_cs_rx = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        theta_cs_rx = np.zeros(scatter_data["scatterers"].shape[0], dtype=float)
        for idx in scatter_data["active_indices"]:
            scatter = scatter_data["scatterers"][idx]
            b_cs = float(np.linalg.norm(rx_xyz - scatter))
            d_cs = float(scatter_data["a_rep"][idx] + b_cs)
            phi_cs_rx[idx] = float(rng.logistic(loc=rng.uniform(-90.0, 90.0), scale=np.sqrt(25.0 / 2.0)))
            theta_cs_rx[idx] = float(rng.logistic(loc=rng.uniform(-90.0, 90.0), scale=np.sqrt(25.0 / 2.0)))
            a_ris_cs = _ris_array_response(ris_side, k, spacing, scatter_data["theta_ris_side"][idx], scatter_data["phi_ris_side"][idx])
            a_rx_cs = _terminal_array_response(rx_antennas, array_type, k, spacing, phi_cs_rx[idx], theta_cs_rx[idx])
            _, path_gain_linear, _ = _path_gain_linear(
                d_cs,
                frequency_GHz=frequency_GHz,
                environment=environment,
                is_los=False,
                rng=rng,
                include_shadow_fading=include_shadow_fading,
            )
            g_nlos += (
                _complex_gaussian(rng)
                * np.sqrt(_ris_pattern_linear(scatter_data["theta_ris_side"][idx]) * path_gain_linear)
                * np.outer(a_ris_cs, a_rx_cs)
            )
        g_nlos *= np.sqrt(1.0 / max(scatter_data["m_new"], 1))
        metadata["scatterers"] = scatter_data
        metadata["nlos_cluster_count"] = int(scatter_data["cluster_count"])
        metadata["nlos_subray_count"] = int(np.sum(scatter_data["subrays_per_cluster"]))
        metadata["nlos_active_scatterer_count"] = int(scatter_data["m_new"])

    return g_los + g_nlos, metadata


def _generate_direct_channel(
    tx_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    *,
    environment: SimRISEnvironment,
    frequency_GHz: float,
    array_type: SimRISArrayType,
    tx_antennas: int,
    rx_antennas: int,
    include_nlos: bool,
    include_shadow_fading: bool,
    force_los: bool | None,
    inherited_tx_ris_los: int | None,
    shared_tx_ris_metadata: dict[str, Any] | None,
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, Any]]:
    wavelength = _wavelength_m(frequency_GHz)
    k = 2.0 * np.pi / wavelength
    spacing = wavelength / 2.0
    d_tx_rx = float(np.linalg.norm(tx_xyz - rx_xyz))
    los_indicator = _sample_direct_los_indicator(
        environment,
        tx_xyz,
        rx_xyz,
        ris_xyz,
        d_tx_rx,
        rng,
        force=force_los,
        inherited_tx_ris_los=inherited_tx_ris_los,
    )
    metadata: dict[str, Any] = {"los_indicator": los_indicator, "distance_m": d_tx_rx}
    direct = np.zeros((rx_antennas, tx_antennas), dtype=np.complex128)
    direct_nlos = np.zeros((rx_antennas, tx_antennas), dtype=np.complex128)

    if los_indicator == 1:
        phi_tx, theta_tx, _, _ = _angles_direct_los(tx_xyz, rx_xyz)
        phi_rx, theta_rx = _sample_random_rx_angles(rng)
        a_tx = _terminal_array_response(tx_antennas, array_type, k, spacing, phi_tx, theta_tx)
        a_rx = _terminal_array_response(rx_antennas, array_type, k, spacing, phi_rx, theta_rx)
        path_gain_dB, path_gain_linear, _ = _path_gain_linear(
            d_tx_rx,
            frequency_GHz=frequency_GHz,
            environment=environment,
            is_los=True,
            rng=rng,
            include_shadow_fading=include_shadow_fading,
        )
        direct += np.sqrt(path_gain_linear) * np.outer(a_rx, a_tx) * np.exp(1j * rng.random() * 2.0 * np.pi)
        metadata["los_angles"] = (phi_tx, theta_tx, phi_rx, theta_rx)
        metadata["los_path_gain_dB"] = float(path_gain_dB)
        metadata["los_path_gain_linear"] = float(path_gain_linear)
    if include_nlos:
        if environment == "indoor":
            if shared_tx_ris_metadata is not None and "shared_scatterers" in shared_tx_ris_metadata:
                scatter_data = shared_tx_ris_metadata["shared_scatterers"]
                beta = np.asarray(shared_tx_ris_metadata.get("shared_beta"), dtype=np.complex128)
                shadow = np.asarray(shared_tx_ris_metadata.get("shared_shadow"), dtype=float)
                for idx in scatter_data["active_indices"]:
                    scatter = scatter_data["scatterers"][idx]
                    d_cs_tilde = float(scatter_data["a_rep"][idx] + np.linalg.norm(scatter - rx_xyz))
                    phi_tx_cs = _signed_ratio_angle_deg(scatter[1] - tx_xyz[1], scatter[0] - tx_xyz[0], tx_xyz[1] - scatter[1])
                    theta_tx_cs = _signed_asin_angle_deg(scatter[2] - tx_xyz[2], scatter_data["a_rep"][idx], scatter[2] - tx_xyz[2])
                    phi_rx_cs, theta_rx_cs = _sample_random_rx_angles(rng)
                    a_tx_cs = _terminal_array_response(tx_antennas, array_type, k, spacing, phi_tx_cs, theta_tx_cs)
                    a_rx_cs = _terminal_array_response(rx_antennas, array_type, k, spacing, phi_rx_cs, theta_rx_cs)
                    _, path_gain_linear, _ = _path_gain_linear(
                        d_cs_tilde,
                        frequency_GHz=frequency_GHz,
                        environment=environment,
                        is_los=False,
                        rng=rng,
                        include_shadow_fading=include_shadow_fading,
                        shadow_override=float(shadow[idx]) if shadow.size > idx else None,
                    )
                    eta = float(k * (np.linalg.norm(scatter - ris_xyz) - np.linalg.norm(scatter - rx_xyz)))
                    beta_idx = beta[idx] if beta.size > idx else _complex_gaussian(rng)
                    direct_nlos += beta_idx * np.exp(1j * eta) * np.sqrt(path_gain_linear) * np.outer(a_rx_cs, a_tx_cs)
                direct_nlos *= np.sqrt(1.0 / max(scatter_data["m_new"], 1))
                metadata["shared_direct_scatterers"] = scatter_data
                metadata["nlos_cluster_count"] = int(scatter_data["cluster_count"])
                metadata["nlos_subray_count"] = int(np.sum(scatter_data["subrays_per_cluster"]))
                metadata["nlos_active_scatterer_count"] = int(scatter_data["m_new"])
        else:
            scatter_data = _generate_tx_side_scatterers(
                tx_xyz, rx_xyz, environment=environment, frequency_GHz=frequency_GHz, rng=rng
            )
            for idx in scatter_data["active_indices"]:
                scatter = scatter_data["scatterers"][idx]
                d_cs = float(scatter_data["a_rep"][idx] + np.linalg.norm(scatter - rx_xyz))
                phi_tx_cs = _signed_ratio_angle_deg(scatter[1] - tx_xyz[1], scatter[0] - tx_xyz[0], tx_xyz[1] - scatter[1])
                theta_tx_cs = _signed_asin_angle_deg(scatter[2] - tx_xyz[2], scatter_data["a_rep"][idx], scatter[2] - tx_xyz[2])
                phi_rx_cs, theta_rx_cs = _sample_random_rx_angles(rng)
                a_tx_cs = _terminal_array_response(tx_antennas, array_type, k, spacing, phi_tx_cs, theta_tx_cs)
                a_rx_cs = _terminal_array_response(rx_antennas, array_type, k, spacing, phi_rx_cs, theta_rx_cs)
                _, path_gain_linear, _ = _path_gain_linear(
                    d_cs,
                    frequency_GHz=frequency_GHz,
                    environment=environment,
                    is_los=False,
                    rng=rng,
                    include_shadow_fading=include_shadow_fading,
                )
                direct_nlos += _complex_gaussian(rng) * np.sqrt(path_gain_linear) * np.outer(a_rx_cs, a_tx_cs)
            direct_nlos *= np.sqrt(1.0 / max(scatter_data["m_new"], 1))
            metadata["scatterers"] = scatter_data
            metadata["nlos_cluster_count"] = int(scatter_data["cluster_count"])
            metadata["nlos_subray_count"] = int(np.sum(scatter_data["subrays_per_cluster"]))
            metadata["nlos_active_scatterer_count"] = int(scatter_data["m_new"])
    return direct + direct_nlos, metadata


def evaluate_simris_los_reference(
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    *,
    ris_side: int,
    frequency_GHz: float,
    environment: str | int = "indoor",
    scenario: int = 1,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    include_direct_path: bool = True,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Evaluate a deterministic LOS subset of the published SimRIS model."""

    environment_key = _normalize_environment(environment)
    array_type_key = _normalize_array_type(array_type)
    tx_xyz = np.asarray(tx_xyz, dtype=float)
    ris_xyz = np.asarray(ris_xyz, dtype=float)
    rx_xyz = np.asarray(rx_xyz, dtype=float)
    validation = _maybe_run_preflight_validation(
        tx_xyz=tx_xyz,
        ris_xyz=ris_xyz,
        rx_xyz=rx_xyz,
        environment=environment_key,
        frequency_GHz=float(frequency_GHz),
        ris_side=ris_side,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )

    H, tx_meta = _generate_tx_ris_channel(
        tx_xyz,
        ris_xyz,
        environment=environment_key,
        scenario=scenario,
        frequency_GHz=frequency_GHz,
        array_type=array_type_key,
        ris_side=ris_side,
        tx_antennas=tx_antennas,
        include_nlos=False,
        include_shadow_fading=False,
        force_los=True,
        rng=np.random.default_rng(0),
    )
    G_tx, rx_meta = _generate_ris_rx_channel(
        ris_xyz,
        rx_xyz,
        environment=environment_key,
        scenario=scenario,
        frequency_GHz=frequency_GHz,
        array_type=array_type_key,
        ris_side=ris_side,
        rx_antennas=rx_antennas,
        include_nlos=False,
        include_shadow_fading=False,
        force_los=True,
        rng=np.random.default_rng(1),
    )
    d_tx_ris = float(np.linalg.norm(tx_xyz - ris_xyz))
    d_ris_rx = float(np.linalg.norm(ris_xyz - rx_xyz))
    d_tx_rx = float(np.linalg.norm(tx_xyz - rx_xyz))
    if include_direct_path:
        D, direct_meta = _generate_direct_channel(
            tx_xyz,
            rx_xyz,
            ris_xyz,
            environment=environment_key,
            frequency_GHz=frequency_GHz,
            array_type=array_type_key,
            tx_antennas=tx_antennas,
            rx_antennas=rx_antennas,
            include_nlos=False,
            include_shadow_fading=False,
            force_los=True,
            inherited_tx_ris_los=1,
            shared_tx_ris_metadata=tx_meta,
            rng=np.random.default_rng(2),
        )
    else:
        D = np.zeros((rx_antennas, tx_antennas), dtype=np.complex128)
        direct_meta = {"los_indicator": 0, "distance_m": d_tx_rx}

    G = G_tx.T
    phase_alignment = np.exp(-1j * np.angle(G[0, :] * H[:, 0]))
    channel_gain_linear = float(np.linalg.norm(G @ np.diag(phase_alignment) @ H + D, ord="fro") ** 2)
    channel_gain_dB = float(10.0 * np.log10(max(channel_gain_linear, 1e-30)))
    path_gain_ap_ris_dB, _, _ = _path_gain_linear(d_tx_ris, frequency_GHz=frequency_GHz, environment=environment_key, is_los=True)
    path_gain_ris_ue_dB, _, _ = _path_gain_linear(d_ris_rx, frequency_GHz=frequency_GHz, environment=environment_key, is_los=True)
    path_gain_direct_dB, _, _ = _path_gain_linear(d_tx_rx, frequency_GHz=frequency_GHz, environment=environment_key, is_los=True)

    theta_ris_in = float(tx_meta["los_angles"][1])
    theta_ris_out = float(rx_meta["los_angles"][1])
    ris_pattern_in_linear = _ris_pattern_linear(theta_ris_in)
    ris_pattern_out_linear = _ris_pattern_linear(theta_ris_out)

    result = {
        "h": H.copy(),
        "g": G_tx.copy(),
        "H": H,
        "G": G,
        "D": D,
        "h_SISO": D.copy(),
        "channel_gain_linear": channel_gain_linear,
        "channel_gain_dB": channel_gain_dB,
        "metadata": {
            "tx_ris": tx_meta,
            "ris_rx": rx_meta,
            "direct": direct_meta,
        },
        "path_gain_ap_ris_dB": path_gain_ap_ris_dB,
        "path_gain_ris_ue_dB": path_gain_ris_ue_dB,
        "path_gain_direct_dB": path_gain_direct_dB,
        "path_loss_ap_ris_dB": -path_gain_ap_ris_dB,
        "path_loss_ris_ue_dB": -path_gain_ris_ue_dB,
        "path_loss_direct_dB": -path_gain_direct_dB,
        "theta_tx_ris_deg": theta_ris_in,
        "theta_ris_ue_deg": theta_ris_out,
        "ris_pattern_in_dB": float(10.0 * np.log10(max(ris_pattern_in_linear, 1e-30))),
        "ris_pattern_out_dB": float(10.0 * np.log10(max(ris_pattern_out_linear, 1e-30))),
        "frequency_GHz": float(frequency_GHz),
        "environment": environment_key,
        "scenario": int(scenario),
        "array_type": array_type_key,
    }
    if validation is not None:
        result["validation"] = {
            "ok": validation.ok,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        }
    return result


def evaluate_simris_los_from_nodes(
    ap: Any,
    ris: Any,
    ue: Any,
    *,
    environment: str | int = "indoor",
    scenario: int = 1,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    frequency_GHz: float | None = None,
    include_direct_path: bool = True,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Evaluate deterministic SimRIS LOS metrics using existing node metadata."""
    if frequency_GHz is None:
        frequency_GHz = getattr(ap, "freq", 5.8e9) / 1.0e9
    return evaluate_simris_los_reference(
        ap.pos,
        ris.pos,
        ue.pos,
        ris_side=int(getattr(ris, "N", 1)),
        frequency_GHz=float(frequency_GHz),
        environment=environment,
        scenario=scenario,
        array_type=array_type,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        include_direct_path=include_direct_path,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )


def evaluate_simris_los_published_case(
    *,
    environment: str | int,
    scenario: int,
    ris_side: int,
    frequency_GHz: float,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    include_direct_path: bool = True,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Evaluate deterministic SimRIS LOS metrics for a published GUI preset."""
    geometry = get_simris_published_geometry(environment=environment, scenario=scenario)
    return evaluate_simris_los_reference(
        geometry["tx_xyz"],
        geometry["ris_xyz"],
        geometry["rx_xyz"],
        ris_side=ris_side,
        frequency_GHz=frequency_GHz,
        environment=geometry["environment"],
        scenario=geometry["scenario"],
        array_type=array_type,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        include_direct_path=include_direct_path,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )


def simulate_simris_channels(
    tx_xyz: np.ndarray,
    ris_xyz: np.ndarray,
    rx_xyz: np.ndarray,
    *,
    ris_side: int,
    frequency_GHz: float,
    environment: str | int = "indoor",
    scenario: int = 1,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    num_realizations: int = 1,
    seed: int | None = None,
    include_direct_path: bool = True,
    include_nlos: bool = True,
    include_shadow_fading: bool = True,
    force_tx_ris_los: bool | None = None,
    force_ris_rx_los: bool | None = None,
    force_direct_los: bool | None = None,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Generate seeded SimRIS-style H/G/D channel tensors."""
    environment_key = _normalize_environment(environment)
    array_type_key = _normalize_array_type(array_type)
    tx_xyz = np.asarray(tx_xyz, dtype=float)
    ris_xyz = np.asarray(ris_xyz, dtype=float)
    rx_xyz = np.asarray(rx_xyz, dtype=float)
    validation = _maybe_run_preflight_validation(
        tx_xyz=tx_xyz,
        ris_xyz=ris_xyz,
        rx_xyz=rx_xyz,
        environment=environment_key,
        frequency_GHz=float(frequency_GHz),
        ris_side=ris_side,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )
    if num_realizations <= 0:
        raise ValueError("num_realizations must be positive")

    H = np.zeros((ris_side * ris_side, tx_antennas, num_realizations), dtype=np.complex128)
    g_raw = np.zeros((ris_side * ris_side, rx_antennas, num_realizations), dtype=np.complex128)
    G = np.zeros((rx_antennas, ris_side * ris_side, num_realizations), dtype=np.complex128)
    D = np.zeros((rx_antennas, tx_antennas, num_realizations), dtype=np.complex128)
    channel_gain_linear = np.zeros(num_realizations, dtype=float)
    channel_gain_dB = np.zeros(num_realizations, dtype=float)
    los_path_gain_ap_ris_dB = np.full(num_realizations, np.nan, dtype=float)
    los_path_gain_ris_ue_dB = np.full(num_realizations, np.nan, dtype=float)
    los_path_gain_direct_dB = np.full(num_realizations, np.nan, dtype=float)
    los_path_loss_ap_ris_dB = np.full(num_realizations, np.nan, dtype=float)
    los_path_loss_ris_ue_dB = np.full(num_realizations, np.nan, dtype=float)
    los_path_loss_direct_dB = np.full(num_realizations, np.nan, dtype=float)
    theta_tx_ris_deg = np.full(num_realizations, np.nan, dtype=float)
    theta_ris_ue_deg = np.full(num_realizations, np.nan, dtype=float)
    ris_pattern_in_dB = np.full(num_realizations, np.nan, dtype=float)
    ris_pattern_out_dB = np.full(num_realizations, np.nan, dtype=float)
    metadata: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)

    for realization in range(num_realizations):
        h_matrix, tx_meta = _generate_tx_ris_channel(
            tx_xyz,
            ris_xyz,
            environment=environment_key,
            scenario=scenario,
            frequency_GHz=frequency_GHz,
            array_type=array_type_key,
            ris_side=ris_side,
            tx_antennas=tx_antennas,
            include_nlos=include_nlos,
            include_shadow_fading=include_shadow_fading,
            force_los=force_tx_ris_los,
            rng=rng,
        )
        g_matrix_tx, rx_meta = _generate_ris_rx_channel(
            ris_xyz,
            rx_xyz,
            environment=environment_key,
            scenario=scenario,
            frequency_GHz=frequency_GHz,
            array_type=array_type_key,
            ris_side=ris_side,
            rx_antennas=rx_antennas,
            include_nlos=include_nlos,
            include_shadow_fading=include_shadow_fading,
            force_los=force_ris_rx_los,
            rng=rng,
        )
        if include_direct_path:
            d_matrix, direct_meta = _generate_direct_channel(
                tx_xyz,
                rx_xyz,
                ris_xyz,
                environment=environment_key,
                frequency_GHz=frequency_GHz,
                array_type=array_type_key,
                tx_antennas=tx_antennas,
                rx_antennas=rx_antennas,
                include_nlos=include_nlos,
                include_shadow_fading=include_shadow_fading,
                force_los=force_direct_los,
                inherited_tx_ris_los=tx_meta.get("los_indicator"),
                shared_tx_ris_metadata=tx_meta,
                rng=rng,
            )
        else:
            d_matrix = np.zeros((rx_antennas, tx_antennas), dtype=np.complex128)
            direct_meta = {"los_indicator": 0}

        H[:, :, realization] = h_matrix
        g_raw[:, :, realization] = g_matrix_tx
        G[:, :, realization] = g_matrix_tx.T
        D[:, :, realization] = d_matrix
        if "los_path_gain_dB" in tx_meta:
            los_path_gain_ap_ris_dB[realization] = float(tx_meta["los_path_gain_dB"])
            los_path_loss_ap_ris_dB[realization] = float(-tx_meta["los_path_gain_dB"])
        if "los_path_gain_dB" in rx_meta:
            los_path_gain_ris_ue_dB[realization] = float(rx_meta["los_path_gain_dB"])
            los_path_loss_ris_ue_dB[realization] = float(-rx_meta["los_path_gain_dB"])
        if "los_path_gain_dB" in direct_meta:
            los_path_gain_direct_dB[realization] = float(direct_meta["los_path_gain_dB"])
            los_path_loss_direct_dB[realization] = float(-direct_meta["los_path_gain_dB"])
        if "los_angles" in tx_meta:
            theta_tx_ris_deg[realization] = float(tx_meta["los_angles"][1])
            ris_pattern_in_dB[realization] = float(10.0 * np.log10(max(_ris_pattern_linear(theta_tx_ris_deg[realization]), 1e-30)))
        if "los_angles" in rx_meta:
            theta_ris_ue_deg[realization] = float(rx_meta["los_angles"][1])
            ris_pattern_out_dB[realization] = float(10.0 * np.log10(max(_ris_pattern_linear(theta_ris_ue_deg[realization]), 1e-30)))
        phase_alignment = np.exp(-1j * np.angle(G[0, :, realization] * H[:, 0, realization]))
        channel_gain_linear[realization] = float(
            np.linalg.norm(
                G[:, :, realization] @ np.diag(phase_alignment) @ H[:, :, realization] + D[:, :, realization],
                ord="fro",
            )
            ** 2
        )
        channel_gain_dB[realization] = float(10.0 * np.log10(max(channel_gain_linear[realization], 1e-30)))
        metadata.append({"tx_ris": tx_meta, "ris_rx": rx_meta, "direct": direct_meta})

    result = {
        "h": H.copy(),
        "g": g_raw,
        "H": H,
        "G": G,
        "D": D,
        "h_SISO": D.copy(),
        "metadata": metadata,
        "frequency_GHz": float(frequency_GHz),
        "environment": environment_key,
        "scenario": int(scenario),
        "array_type": array_type_key,
        "num_realizations": int(num_realizations),
        "channel_gain_linear": channel_gain_linear,
        "channel_gain_dB": channel_gain_dB,
        "los_path_gain_ap_ris_dB": los_path_gain_ap_ris_dB,
        "los_path_gain_ris_ue_dB": los_path_gain_ris_ue_dB,
        "los_path_gain_direct_dB": los_path_gain_direct_dB,
        "los_path_loss_ap_ris_dB": los_path_loss_ap_ris_dB,
        "los_path_loss_ris_ue_dB": los_path_loss_ris_ue_dB,
        "los_path_loss_direct_dB": los_path_loss_direct_dB,
        "theta_tx_ris_deg": theta_tx_ris_deg,
        "theta_ris_ue_deg": theta_ris_ue_deg,
        "ris_pattern_in_dB": ris_pattern_in_dB,
        "ris_pattern_out_dB": ris_pattern_out_dB,
    }
    if validation is not None:
        result["validation"] = {
            "ok": validation.ok,
            "errors": list(validation.errors),
            "warnings": list(validation.warnings),
        }
    return result


def simulate_simris_published_case(
    *,
    environment: str | int,
    scenario: int,
    ris_side: int,
    frequency_GHz: float,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    num_realizations: int = 1,
    seed: int | None = None,
    include_direct_path: bool = True,
    include_nlos: bool = True,
    include_shadow_fading: bool = True,
    force_tx_ris_los: bool | None = None,
    force_ris_rx_los: bool | None = None,
    force_direct_los: bool | None = None,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Generate seeded SimRIS tensors for a published GUI preset geometry."""
    geometry = get_simris_published_geometry(environment=environment, scenario=scenario)
    return simulate_simris_channels(
        geometry["tx_xyz"],
        geometry["ris_xyz"],
        geometry["rx_xyz"],
        ris_side=ris_side,
        frequency_GHz=frequency_GHz,
        environment=geometry["environment"],
        scenario=geometry["scenario"],
        array_type=array_type,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        num_realizations=num_realizations,
        seed=seed,
        include_direct_path=include_direct_path,
        include_nlos=include_nlos,
        include_shadow_fading=include_shadow_fading,
        force_tx_ris_los=force_tx_ris_los,
        force_ris_rx_los=force_ris_rx_los,
        force_direct_los=force_direct_los,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )


def evaluate_simris_from_nodes(
    ap: Any,
    ris: Any,
    ue: Any,
    *,
    environment: str | int = "indoor",
    scenario: int = 1,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    frequency_GHz: float | None = None,
    num_realizations: int = 1,
    seed: int | None = None,
    include_direct_path: bool = True,
    include_nlos: bool = True,
    include_shadow_fading: bool = True,
    force_tx_ris_los: bool | None = None,
    force_ris_rx_los: bool | None = None,
    force_direct_los: bool | None = None,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> dict[str, Any]:
    """Generate seeded SimRIS-style channels using existing node metadata."""
    if frequency_GHz is None:
        frequency_GHz = getattr(ap, "freq", 5.8e9) / 1.0e9
    return simulate_simris_channels(
        ap.pos,
        ris.pos,
        ue.pos,
        ris_side=int(getattr(ris, "N", 1)),
        frequency_GHz=float(frequency_GHz),
        environment=environment,
        scenario=scenario,
        array_type=array_type,
        tx_antennas=tx_antennas,
        rx_antennas=rx_antennas,
        num_realizations=num_realizations,
        seed=seed,
        include_direct_path=include_direct_path,
        include_nlos=include_nlos,
        include_shadow_fading=include_shadow_fading,
        force_tx_ris_los=force_tx_ris_los,
        force_ris_rx_los=force_ris_rx_los,
        force_direct_los=force_direct_los,
        validate_preflight=validate_preflight,
        error_on_invalid=error_on_invalid,
    )


def summarize_simris_tensors(tensors: dict[str, Any]) -> dict[str, Any]:
    """Return a compact deterministic signature for seeded regression checks."""
    H = np.asarray(tensors["H"])
    G = np.asarray(tensors["G"])
    D = np.asarray(tensors["D"])
    h_siso = np.asarray(tensors.get("h_SISO", D))
    return {
        "H_norms": [float(np.linalg.norm(H[:, :, idx])) for idx in range(H.shape[2])],
        "G_norms": [float(np.linalg.norm(G[:, :, idx])) for idx in range(G.shape[2])],
        "D_norms": [float(np.linalg.norm(D[:, :, idx])) for idx in range(D.shape[2])],
        "h_SISO_norms": [float(np.linalg.norm(h_siso[:, :, idx])) for idx in range(h_siso.shape[2])],
        "H00": complex(H[0, 0, 0]),
        "G00": complex(G[0, 0, 0]),
        "D00": complex(D[0, 0, 0]),
        "h_SISO00": complex(h_siso[0, 0, 0]),
    }


def evaluate_simris_channel_published_case(
    *,
    environment: str | int,
    scenario: int,
    ris_side: int,
    frequency_GHz: float,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    include_direct_path: bool = True,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> ChannelEvaluation:
    """Evaluate the deterministic SimRIS adapter for a published GUI preset."""
    network = build_simris_published_network(
        environment=environment,
        scenario=scenario,
        ris_side=ris_side,
        frequency_GHz=frequency_GHz,
    )
    channel = SimRISChannel(
        SimRISLoSConfig(
            environment=_normalize_environment(environment),
            scenario=int(scenario),
            array_type=_normalize_array_type(array_type),
            tx_antennas=int(tx_antennas),
            rx_antennas=int(rx_antennas),
            include_direct_path=bool(include_direct_path),
            frequency_GHz=float(frequency_GHz),
            validate_preflight=bool(validate_preflight),
            error_on_invalid=bool(error_on_invalid),
        )
    )
    return channel.evaluate(
        network,
        "ap1",
        "ris1",
        "ue1",
    )


class SimRISChannel:
    """Additive channel adapter for the deterministic SimRIS LOS subset."""

    def __init__(self, config: SimRISLoSConfig | None = None):
        self.config = config or SimRISLoSConfig()

    def evaluate(
        self,
        network: Any,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        **kwargs: Any,
    ) -> ChannelEvaluation:
        ap_node, ris_node, ue_node = network._resolve_connect_nodes(ap_name, ris_name, ue_name)
        config = SimRISLoSConfig(
            environment=_normalize_environment(kwargs.get("environment", self.config.environment)),
            scenario=int(kwargs.get("scenario", self.config.scenario)),
            array_type=_normalize_array_type(kwargs.get("array_type", self.config.array_type)),
            tx_antennas=int(kwargs.get("tx_antennas", self.config.tx_antennas)),
            rx_antennas=int(kwargs.get("rx_antennas", self.config.rx_antennas)),
            include_direct_path=bool(kwargs.get("include_direct_path", self.config.include_direct_path)),
            frequency_GHz=float(kwargs.get("frequency_GHz", self.config.frequency_GHz or (getattr(ap_node, "freq", 5.8e9) / 1.0e9))),
            validate_preflight=bool(kwargs.get("validate_preflight", self.config.validate_preflight)),
            error_on_invalid=bool(kwargs.get("error_on_invalid", self.config.error_on_invalid)),
        )
        metrics = evaluate_simris_los_from_nodes(
            ap_node,
            ris_node,
            ue_node,
            environment=config.environment,
            scenario=config.scenario,
            array_type=config.array_type,
            tx_antennas=config.tx_antennas,
            rx_antennas=config.rx_antennas,
            frequency_GHz=config.frequency_GHz,
            include_direct_path=config.include_direct_path,
            validate_preflight=config.validate_preflight,
            error_on_invalid=config.error_on_invalid,
        )
        ap_gain = float(getattr(ap_node, "antenna_gain_dBi", 3.0))
        ue_gain = float(getattr(ue_node, "antenna_gain_dBi", 3.0))
        tx_power = float(getattr(ap_node, "power_dBm", 20.0))
        bandwidth_MHz = float(getattr(ap_node, "bandwidth_MHz", 20.0))
        noise_figure_dB = float(getattr(ue_node, "noise_figure_dB", 6.0))
        noise_power_dBm = float(-174.0 + 10.0 * np.log10(max(bandwidth_MHz, 1e-6) * 1.0e6) + noise_figure_dB)
        pwr_dBm = tx_power + ap_gain + ue_gain + metrics["channel_gain_dB"]
        snr_dB = pwr_dBm - noise_power_dBm
        result = {
            "snr_dB": float(snr_dB),
            "pwr_dBm": float(pwr_dBm),
            "rssi_dBm": float(pwr_dBm),
            "gain_linear": float(metrics["channel_gain_linear"]),
            "gain_dBi": float(metrics["channel_gain_dB"]),
            "quant_loss_dB": 0.0,
            "beam_angle": float(np.degrees(np.arctan2(ue_node.pos[1] - ris_node.pos[1], ue_node.pos[0] - ris_node.pos[0]))),
            "noise_power_dBm": noise_power_dBm,
            "model": "simris_deterministic_los",
            **metrics,
        }
        return ChannelEvaluation(result=result)


class SimRISStochasticChannel:
    """Seeded additive channel adapter for SimRIS-style stochastic H/G/D generation."""

    def __init__(self, config: SimRISConfig | None = None):
        self.config = config or SimRISConfig()

    def evaluate(
        self,
        network: Any,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        **kwargs: Any,
    ) -> ChannelEvaluation:
        ap_node, ris_node, ue_node = network._resolve_connect_nodes(ap_name, ris_name, ue_name)
        config = SimRISConfig(
            environment=_normalize_environment(kwargs.get("environment", self.config.environment)),
            scenario=int(kwargs.get("scenario", self.config.scenario)),
            array_type=_normalize_array_type(kwargs.get("array_type", self.config.array_type)),
            tx_antennas=int(kwargs.get("tx_antennas", self.config.tx_antennas)),
            rx_antennas=int(kwargs.get("rx_antennas", self.config.rx_antennas)),
            include_direct_path=bool(kwargs.get("include_direct_path", self.config.include_direct_path)),
            frequency_GHz=float(kwargs.get("frequency_GHz", self.config.frequency_GHz or (getattr(ap_node, "freq", 5.8e9) / 1.0e9))),
            num_realizations=int(kwargs.get("num_realizations", self.config.num_realizations)),
            seed=kwargs.get("seed", self.config.seed),
            include_nlos=bool(kwargs.get("include_nlos", self.config.include_nlos)),
            include_shadow_fading=bool(kwargs.get("include_shadow_fading", self.config.include_shadow_fading)),
            force_tx_ris_los=kwargs.get("force_tx_ris_los", self.config.force_tx_ris_los),
            force_ris_rx_los=kwargs.get("force_ris_rx_los", self.config.force_ris_rx_los),
            force_direct_los=kwargs.get("force_direct_los", self.config.force_direct_los),
            validate_preflight=bool(kwargs.get("validate_preflight", self.config.validate_preflight)),
            error_on_invalid=bool(kwargs.get("error_on_invalid", self.config.error_on_invalid)),
        )
        tensors = evaluate_simris_from_nodes(
            ap_node,
            ris_node,
            ue_node,
            environment=config.environment,
            scenario=config.scenario,
            array_type=config.array_type,
            tx_antennas=config.tx_antennas,
            rx_antennas=config.rx_antennas,
            frequency_GHz=config.frequency_GHz,
            num_realizations=config.num_realizations,
            seed=config.seed,
            include_direct_path=config.include_direct_path,
            include_nlos=config.include_nlos,
            include_shadow_fading=config.include_shadow_fading,
            force_tx_ris_los=config.force_tx_ris_los,
            force_ris_rx_los=config.force_ris_rx_los,
            force_direct_los=config.force_direct_los,
            validate_preflight=config.validate_preflight,
            error_on_invalid=config.error_on_invalid,
        )
        first_gain_linear = float(np.asarray(tensors["channel_gain_linear"], dtype=float)[0])
        first_gain_dB = float(np.asarray(tensors["channel_gain_dB"], dtype=float)[0])
        ap_gain = float(getattr(ap_node, "antenna_gain_dBi", 3.0))
        ue_gain = float(getattr(ue_node, "antenna_gain_dBi", 3.0))
        tx_power = float(getattr(ap_node, "power_dBm", 20.0))
        bandwidth_MHz = float(getattr(ap_node, "bandwidth_MHz", 20.0))
        noise_figure_dB = float(getattr(ue_node, "noise_figure_dB", 6.0))
        noise_power_dBm = float(-174.0 + 10.0 * np.log10(max(bandwidth_MHz, 1e-6) * 1.0e6) + noise_figure_dB)
        pwr_dBm = tx_power + ap_gain + ue_gain + first_gain_dB
        snr_dB = pwr_dBm - noise_power_dBm
        result = {
            **tensors,
            "snr_dB": float(snr_dB),
            "pwr_dBm": float(pwr_dBm),
            "rssi_dBm": float(pwr_dBm),
            "gain_linear": first_gain_linear,
            "gain_dBi": first_gain_dB,
            "quant_loss_dB": 0.0,
            "beam_angle": float(np.degrees(np.arctan2(ue_node.pos[1] - ris_node.pos[1], ue_node.pos[0] - ris_node.pos[0]))),
            "noise_power_dBm": noise_power_dBm,
            "path_gain_ap_ris_dB": float(np.asarray(tensors["los_path_gain_ap_ris_dB"], dtype=float)[0]),
            "path_gain_ris_ue_dB": float(np.asarray(tensors["los_path_gain_ris_ue_dB"], dtype=float)[0]),
            "path_gain_direct_dB": float(np.asarray(tensors["los_path_gain_direct_dB"], dtype=float)[0]),
            "path_loss_ap_ris_dB": float(np.asarray(tensors["los_path_loss_ap_ris_dB"], dtype=float)[0]),
            "path_loss_ris_ue_dB": float(np.asarray(tensors["los_path_loss_ris_ue_dB"], dtype=float)[0]),
            "path_loss_direct_dB": float(np.asarray(tensors["los_path_loss_direct_dB"], dtype=float)[0]),
            "theta_tx_ris_deg": float(np.asarray(tensors["theta_tx_ris_deg"], dtype=float)[0]),
            "theta_ris_ue_deg": float(np.asarray(tensors["theta_ris_ue_deg"], dtype=float)[0]),
            "ris_pattern_in_dB": float(np.asarray(tensors["ris_pattern_in_dB"], dtype=float)[0]),
            "ris_pattern_out_dB": float(np.asarray(tensors["ris_pattern_out_dB"], dtype=float)[0]),
            "model": "simris_stochastic",
        }
        return ChannelEvaluation(result=result)


def evaluate_simris_stochastic_channel_published_case(
    *,
    environment: str | int,
    scenario: int,
    ris_side: int,
    frequency_GHz: float,
    array_type: str | int = "ula",
    tx_antennas: int = 1,
    rx_antennas: int = 1,
    num_realizations: int = 1,
    seed: int | None = None,
    include_direct_path: bool = True,
    include_nlos: bool = True,
    include_shadow_fading: bool = True,
    force_tx_ris_los: bool | None = None,
    force_ris_rx_los: bool | None = None,
    force_direct_los: bool | None = None,
    validate_preflight: bool = False,
    error_on_invalid: bool = True,
) -> ChannelEvaluation:
    """Evaluate the stochastic SimRIS adapter for a published GUI preset."""
    network = build_simris_published_network(
        environment=environment,
        scenario=scenario,
        ris_side=ris_side,
        frequency_GHz=frequency_GHz,
    )
    channel = SimRISStochasticChannel(
        SimRISConfig(
            environment=_normalize_environment(environment),
            scenario=int(scenario),
            array_type=_normalize_array_type(array_type),
            tx_antennas=int(tx_antennas),
            rx_antennas=int(rx_antennas),
            include_direct_path=bool(include_direct_path),
            frequency_GHz=float(frequency_GHz),
            num_realizations=int(num_realizations),
            seed=seed,
            include_nlos=bool(include_nlos),
            include_shadow_fading=bool(include_shadow_fading),
            force_tx_ris_los=force_tx_ris_los,
            force_ris_rx_los=force_ris_rx_los,
            force_direct_los=force_direct_los,
            validate_preflight=bool(validate_preflight),
            error_on_invalid=bool(error_on_invalid),
        )
    )
    return channel.evaluate(
        network,
        "ap1",
        "ris1",
        "ue1",
    )
