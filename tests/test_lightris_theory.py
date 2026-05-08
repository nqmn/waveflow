"""Analytical guarantee checks for the LightRIS engine."""

import pytest

from core.physics import Physics
from utils.lightris import (
    LIGHTRIS_ANALYTICAL_ASSUMPTIONS,
    build_lightris_config,
    evaluate_lightris_decomposition,
    evaluate_lightris_metrics,
    validate_lightris_config,
)


def test_angular_deviation_is_bounded_and_symmetric():
    assert Physics.angular_deviation_deg(0.0, 0.0) == pytest.approx(0.0)
    assert Physics.angular_deviation_deg(10.0, 350.0) == pytest.approx(20.0)
    assert Physics.angular_deviation_deg(350.0, 10.0) == pytest.approx(20.0)
    assert Physics.angular_deviation_deg(90.0, 270.0) == pytest.approx(180.0)


def test_lightris_angle_loss_is_zero_at_alignment_and_bounded():
    assert Physics.lightris_angle_loss_dB(15.0, 15.0) == pytest.approx(0.0)
    assert -60.0 <= Physics.lightris_angle_loss_dB(180.0, 0.0) <= 0.0


def test_lightris_angle_loss_is_monotone_in_angular_deviation():
    losses = [
        Physics.lightris_angle_loss_dB(delta, 0.0)
        for delta in (0.0, 10.0, 20.0, 30.0, 60.0, 120.0)
    ]
    assert losses == sorted(losses, reverse=True)


def test_lightris_total_correction_loss_is_nonnegative_and_additive():
    correction = Physics.lightris_total_correction_loss_dB(
        quantization_loss_dB=-1.5,
        angle_loss_dB=-4.0,
        taper_loss_dB=1.0,
        phase_error_loss_dB=0.5,
        nearfield_loss_dB=0.25,
        efficiency_loss_dB=0.75,
        coherence_loss_dB=0.1,
        other_loss_dB=0.9,
    )

    for key, value in correction.items():
        if key == "total_loss_dB":
            continue
        assert value >= 0.0

    subtotal = sum(
        value
        for key, value in correction.items()
        if key != "total_loss_dB"
    )
    assert correction["total_loss_dB"] == pytest.approx(subtotal)


def test_lightris_metrics_expose_theoretical_correction_breakdown():
    config = build_lightris_config()
    metrics = evaluate_lightris_metrics(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
        physics_config=config,
    )

    assert metrics["angular_deviation_deg"] == pytest.approx(0.0)
    correction = metrics["correction_terms_dB"]
    assert correction["total_loss_dB"] >= 0.0
    assert correction["angle_loss_dB"] == pytest.approx(0.0)


def test_lightris_decomposition_is_self_consistent():
    config = build_lightris_config()
    decomposition = evaluate_lightris_decomposition(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
        physics_config=config,
    )

    assert decomposition["assumptions"] == LIGHTRIS_ANALYTICAL_ASSUMPTIONS
    assert decomposition["metrics"]["total_loss_dB"] == pytest.approx(
        decomposition["path_terms_dB"]["total_path_loss_dB"]
    )
    assert decomposition["metrics"]["total_gain_dBi"] == pytest.approx(
        decomposition["gain_terms_dB"]["total_gain_dBi"]
    )
    assert decomposition["metrics"]["noise_power_dBm"] == pytest.approx(
        decomposition["noise_terms_dB"]["noise_power_dBm"]
    )


def test_lightris_metrics_embed_full_decomposition():
    config = build_lightris_config()
    metrics = evaluate_lightris_metrics(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
        physics_config=config,
    )

    assert metrics["decomposition"]["metrics"]["snr_dB"] == pytest.approx(metrics["snr_dB"])


def test_lightris_validation_rejects_invalid_configs():
    validation = validate_lightris_config(
        {
            "frequency_ghz": -1.0,
            "bandwidth_mhz": 0.0,
            "element_efficiency": 1.5,
            "ris_amplifier_gain": 0.5,
        }
    )

    assert validation["ok"] is False
    assert validation["errors"]


def test_lightris_validation_reports_assumptions_and_warnings():
    validation = validate_lightris_config({"phase_bits": 9, "frequency_ghz": 140.0})

    assert validation["ok"] is True
    assert validation["assumptions"] == LIGHTRIS_ANALYTICAL_ASSUMPTIONS
    assert validation["warnings"]


def test_lightris_snr_is_monotone_in_tx_power():
    config_low = build_lightris_config({"tx_power_dBm": 10.0})
    config_high = build_lightris_config({"tx_power_dBm": 20.0})
    geom = dict(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
    )

    low = evaluate_lightris_metrics(physics_config=config_low, **geom)
    high = evaluate_lightris_metrics(physics_config=config_high, **geom)

    assert high["snr_dB"] > low["snr_dB"]


def test_lightris_snr_is_nonincreasing_with_distance():
    config = build_lightris_config()
    near = evaluate_lightris_metrics(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
        physics_config=config,
    )
    far = evaluate_lightris_metrics(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(10.0, 0.0, 0.0),
        ue_pos=(20.0, 0.0, 0.0),
        beam_angle_deg=0.0,
        physics_config=config,
    )

    assert far["snr_dB"] < near["snr_dB"]


def test_lightris_snr_is_nondecreasing_with_more_elements():
    base_geom = dict(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
    )
    small = evaluate_lightris_metrics(
        physics_config=build_lightris_config({"ris_elements_per_side": 8}),
        **base_geom,
    )
    large = evaluate_lightris_metrics(
        physics_config=build_lightris_config({"ris_elements_per_side": 16}),
        **base_geom,
    )

    assert large["snr_dB"] > small["snr_dB"]


def test_lightris_snr_is_nondecreasing_with_more_phase_bits():
    base_geom = dict(
        ap_pos=(0.0, 0.0, 0.0),
        ris_pos=(5.0, 0.0, 0.0),
        ue_pos=(10.0, 0.0, 0.0),
        beam_angle_deg=0.0,
    )
    one_bit = evaluate_lightris_metrics(
        physics_config=build_lightris_config({"phase_bits": 1}),
        **base_geom,
    )
    two_bit = evaluate_lightris_metrics(
        physics_config=build_lightris_config({"phase_bits": 2}),
        **base_geom,
    )

    assert two_bit["snr_dB"] > one_bit["snr_dB"]
