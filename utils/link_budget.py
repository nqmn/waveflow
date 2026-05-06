"""Shared RIS link-budget helpers and compatibility wrappers."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Sequence

import numpy as np

from core.physics import Physics


DEFAULT_RIS_LINK_CONFIG: Dict[str, float] = {
    "tx_power_dBm": 15.0,
    "ap_antenna_gain_dBi": 16.0,
    "ue_antenna_gain_dBi": 16.0,
    "bandwidth_mhz": 1.0,
    "noise_figure_dB": 6.0,
    "frequency_ghz": 5.8,
    "ris_elements_per_side": 16,
    "phase_bits": 1,
    "element_efficiency": 0.71,
    "ris_amplifier_gain": 1.0,
    "coherence_loss_dB": 0.0,
    "taper_loss_dB": 1.0,
    "phase_error_loss_dB": 1.0,
    "nearfield_loss_dB": 1.0,
    "reflection_loss_dB": 1.5,
    "element_pattern_gain_dBi": 9.03,
    "other_loss_dB": 0.0,
    "noise_rise_dB": 0.0,
}


def build_link_budget_config(
    overrides: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Create a compatibility link-budget config dictionary."""
    config = DEFAULT_RIS_LINK_CONFIG.copy()
    if overrides:
        config.update({key: value for key, value in overrides.items() if value is not None})
    return config


def build_link_budget_config_from_nodes(
    ap: Any,
    ris: Any,
    ue: Any,
    *,
    frequency_ghz: Optional[float] = None,
    bandwidth_mhz: Optional[float] = None,
    noise_figure_dB: Optional[float] = None,
    overrides: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Build a link-budget config dictionary using node metadata."""
    config = build_link_budget_config(overrides)

    config["tx_power_dBm"] = getattr(ap, "power_dBm", config["tx_power_dBm"])
    config["ap_antenna_gain_dBi"] = getattr(ap, "antenna_gain_dBi", config["ap_antenna_gain_dBi"])
    config["ue_antenna_gain_dBi"] = getattr(ue, "antenna_gain_dBi", config["ue_antenna_gain_dBi"])
    config["bandwidth_mhz"] = bandwidth_mhz or getattr(ap, "bandwidth_MHz", config["bandwidth_mhz"])
    config["noise_figure_dB"] = noise_figure_dB or getattr(
        ue, "noise_figure_dB", config["noise_figure_dB"]
    )
    freq = frequency_ghz or getattr(ap, "freq", config["frequency_ghz"] * 1e9)
    config["frequency_ghz"] = freq / 1e9 if freq > 10 else freq
    config["ris_elements_per_side"] = max(1, getattr(ris, "N", config["ris_elements_per_side"]))
    config["phase_bits"] = getattr(ris, "bits", config["phase_bits"])
    config["element_efficiency"] = getattr(ris, "element_efficiency", config["element_efficiency"])
    config["ris_amplifier_gain"] = getattr(ris, "amplifier_gain", config["ris_amplifier_gain"])
    config["coherence_loss_dB"] = getattr(ris, "coherence_loss_dB", config["coherence_loss_dB"])
    config["taper_loss_dB"] = getattr(ris, "taper_loss_dB", config["taper_loss_dB"])
    config["phase_error_loss_dB"] = getattr(
        ris, "phase_error_loss_dB", config["phase_error_loss_dB"]
    )
    config["nearfield_loss_dB"] = getattr(ris, "nearfield_loss_dB", config["nearfield_loss_dB"])
    config["reflection_loss_dB"] = getattr(ris, "reflection_loss_dB", config["reflection_loss_dB"])
    config["element_pattern_gain_dBi"] = getattr(
        ris, "element_pattern_gain_dBi", config["element_pattern_gain_dBi"]
    )
    config["other_loss_dB"] = getattr(ris, "other_loss_dB", config["other_loss_dB"])
    config["noise_rise_dB"] = getattr(ris, "noise_rise_dB", config["noise_rise_dB"])
    return config


def evaluate_ris_link_metrics(
    ap_pos: Sequence[float],
    ris_pos: Sequence[float],
    ue_pos: Sequence[float],
    beam_angle_deg: float,
    physics_config: Mapping[str, float],
) -> Dict[str, float]:
    """Compute SNR/RSSI for an AP→RIS→UE link using shared Phase 3 helpers."""
    ap_pos = np.asarray(ap_pos, dtype=float)
    ris_pos = np.asarray(ris_pos, dtype=float)
    ue_pos = np.asarray(ue_pos, dtype=float)

    d_ap_ris = float(np.linalg.norm(ap_pos - ris_pos))
    d_ris_ue = float(np.linalg.norm(ue_pos - ris_pos))

    frequency_hz = physics_config["frequency_ghz"] * 1e9
    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, frequency_hz)
    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, frequency_hz)

    target_angle = np.degrees(np.arctan2(ue_pos[1] - ris_pos[1], ue_pos[0] - ris_pos[0])) % 360
    angle_loss_dB = Physics.angle_loss_dB(beam_angle_deg, target_angle)

    quant_loss_dB = Physics.quantization_loss_dB(
        physics_config["phase_bits"],
        element_efficiency=physics_config["element_efficiency"],
    )
    quant_loss_positive = max(-quant_loss_dB, 0.0)
    efficiency_loss = -10 * np.log10(max(physics_config["element_efficiency"], 1e-3))

    elements_per_side = max(1, int(round(physics_config["ris_elements_per_side"])))
    total_elements = elements_per_side * elements_per_side
    af_ideal = 20 * np.log10(max(total_elements, 1))

    total_af_losses = (
        quant_loss_positive
        + physics_config["taper_loss_dB"]
        + physics_config["phase_error_loss_dB"]
        + physics_config["nearfield_loss_dB"]
        + efficiency_loss
        + physics_config["coherence_loss_dB"]
        + physics_config["other_loss_dB"]
        + angle_loss_dB
    )
    af_real = max(af_ideal - total_af_losses, 0.0)

    ris_gain_dBi = (
        af_real
        + physics_config["element_pattern_gain_dBi"]
        - physics_config["reflection_loss_dB"]
    )
    amplifier_gain_linear = physics_config["ris_amplifier_gain"]
    if amplifier_gain_linear > 1.0:
        ris_gain_dBi += 10 * np.log10(amplifier_gain_linear)

    total_gain_dBi = (
        ris_gain_dBi
        + physics_config["ap_antenna_gain_dBi"]
        + physics_config["ue_antenna_gain_dBi"]
    )
    total_loss_dB = pl_ap_ris + pl_ris_ue
    received_power_dBm = physics_config["tx_power_dBm"] - total_loss_dB + total_gain_dBi

    bandwidth_hz = max(physics_config["bandwidth_mhz"], 1e-3) * 1e6
    noise_power_dBm = (
        -174
        + 10 * np.log10(bandwidth_hz)
        + physics_config["noise_figure_dB"]
        + physics_config["noise_rise_dB"]
    )
    snr_dB = received_power_dBm - noise_power_dBm

    return {
        "snr_dB": snr_dB,
        "rssi_dBm": received_power_dBm,
        "received_power_dBm": received_power_dBm,
        "noise_power_dBm": noise_power_dBm,
        "total_gain_dBi": total_gain_dBi,
        "total_loss_dB": total_loss_dB,
        "af_real_dB": af_real,
        "angle_loss_dB": angle_loss_dB,
        "quant_loss_dB": quant_loss_dB,
    }


def evaluate_ris_link_from_nodes(
    ap: Any,
    ris: Any,
    ue: Any,
    *,
    beam_angle_deg: Optional[float] = None,
    frequency_ghz: Optional[float] = None,
    bandwidth_mhz: Optional[float] = None,
    noise_figure_dB: Optional[float] = None,
    overrides: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Evaluate RIS link metrics directly from node metadata."""
    if beam_angle_deg is None:
        beam_angle_deg = float(np.degrees(np.arctan2(ue.pos[1] - ris.pos[1], ue.pos[0] - ris.pos[0])) % 360)

    config = build_link_budget_config_from_nodes(
        ap,
        ris,
        ue,
        frequency_ghz=frequency_ghz,
        bandwidth_mhz=bandwidth_mhz,
        noise_figure_dB=noise_figure_dB,
        overrides=overrides,
    )
    return evaluate_ris_link_metrics(ap.pos, ris.pos, ue.pos, beam_angle_deg, config)


def build_config(overrides: Optional[Mapping[str, float]] = None) -> Dict[str, float]:
    """Compatibility wrapper around the Phase 3 channel helper."""
    return build_link_budget_config(overrides)


def build_config_from_nodes(
    ap,
    ris,
    ue,
    frequency_ghz: Optional[float] = None,
    bandwidth_mhz: Optional[float] = None,
    noise_figure_dB: Optional[float] = None,
    overrides: Optional[Mapping[str, float]] = None,
) -> Dict[str, float]:
    """Compatibility wrapper around the Phase 3 channel helper."""
    return build_link_budget_config_from_nodes(
        ap,
        ris,
        ue,
        frequency_ghz=frequency_ghz,
        bandwidth_mhz=bandwidth_mhz,
        noise_figure_dB=noise_figure_dB,
        overrides=overrides,
    )


def compute_ris_link_metrics(
    ap_pos: Sequence[float],
    ris_pos: Sequence[float],
    ue_pos: Sequence[float],
    beam_angle_deg: float,
    physics_config: Mapping[str, float],
) -> Dict[str, float]:
    """Compatibility wrapper around the Phase 3 channel helper."""
    return evaluate_ris_link_metrics(ap_pos, ris_pos, ue_pos, beam_angle_deg, physics_config)
