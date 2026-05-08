"""Focused tests for the additive deterministic SimRIS LOS channel engine."""

from __future__ import annotations

import math

import numpy as np
import pytest

from core import RISNetwork
from risnet.channels import (
    build_simris_published_network,
    evaluate_simris_channel_published_case,
    SimRISChannel,
    SimRISConfig,
    SimRISLoSConfig,
    SimRISStochasticChannel,
    evaluate_simris_from_nodes,
    evaluate_simris_los_from_nodes,
    evaluate_simris_los_published_case,
    evaluate_simris_los_reference,
    evaluate_simris_stochastic_channel_published_case,
    get_simris_published_geometry,
    simulate_simris_channels,
    simulate_simris_published_case,
    summarize_simris_tensors,
    validate_simris_configuration,
)


def build_simris_reference_network() -> RISNetwork:
    """Indoor Scenario 1 geometry adapted from the published SimRIS examples."""
    net = RISNetwork(enable_messaging=False)
    net.add_ap(
        "ap1",
        0.0,
        25.0,
        2.0,
        power_dBm=0.0,
        freq=28e9,
        antenna_gain_dBi=0.0,
        bandwidth_MHz=20.0,
    )
    net.add_ris(
        "ris1",
        40.0,
        50.0,
        2.0,
        N=8,
        bits=0,
        max_angle_deg=180.0,
        normal_angle_deg=0.0,
    )
    net.add_ue(
        "ue1",
        38.0,
        48.0,
        1.0,
        antenna_gain_dBi=0.0,
        noise_figure_dB=6.0,
    )
    return net


def build_simris_scenario2_network() -> RISNetwork:
    """Indoor Scenario 2 geometry adapted from the published SimRIS examples."""
    net = RISNetwork(enable_messaging=False)
    net.add_ap(
        "ap1",
        0.0,
        25.0,
        2.0,
        power_dBm=0.0,
        freq=28e9,
        antenna_gain_dBi=0.0,
        bandwidth_MHz=20.0,
    )
    net.add_ris(
        "ris1",
        70.0,
        30.0,
        2.0,
        N=8,
        bits=0,
        max_angle_deg=180.0,
        normal_angle_deg=0.0,
    )
    net.add_ue(
        "ue1",
        70.0,
        35.0,
        1.0,
        antenna_gain_dBi=0.0,
        noise_figure_dB=6.0,
    )
    return net


def build_simris_outdoor_network() -> RISNetwork:
    """Outdoor Scenario 1 geometry based on the published SimRIS examples."""
    net = RISNetwork(enable_messaging=False)
    net.add_ap(
        "ap1",
        0.0,
        25.0,
        20.0,
        power_dBm=0.0,
        freq=28e9,
        antenna_gain_dBi=0.0,
        bandwidth_MHz=20.0,
    )
    net.add_ris(
        "ris1",
        70.0,
        85.0,
        10.0,
        N=8,
        bits=0,
        max_angle_deg=180.0,
        normal_angle_deg=0.0,
    )
    net.add_ue(
        "ue1",
        80.0,
        75.0,
        1.0,
        antenna_gain_dBi=0.0,
        noise_figure_dB=6.0,
    )
    return net


def deterministic_simris_los_reference_gain_dB(
    net: RISNetwork,
    *,
    environment: str,
) -> float:
    """Closed-form reference for the deterministic LOS slice under test."""
    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    wavelength = 3.0e8 / 28e9
    d_ap_ris = math.dist(ap.pos.tolist(), ris.pos.tolist())
    d_ris_ue = math.dist(ris.pos.tolist(), ue.pos.tolist())

    n_los = 1.73 if environment == "indoor" else 1.98
    q = 0.285
    element_gain = math.pi
    n_total = ris.N * ris.N

    path_gain_ap_ris_dB = -20.0 * math.log10(4.0 * math.pi / wavelength) - 10.0 * n_los * math.log10(d_ap_ris)
    path_gain_ris_ue_dB = -20.0 * math.log10(4.0 * math.pi / wavelength) - 10.0 * n_los * math.log10(d_ris_ue)

    theta_ap_ris = math.degrees(math.asin(min(abs(ris.pos[2] - ap.pos[2]) / d_ap_ris, 1.0)))
    theta_ris_ue = math.degrees(math.asin(min(abs(ris.pos[2] - ue.pos[2]) / d_ris_ue, 1.0)))

    pattern_ap_ris_dB = 10.0 * math.log10(element_gain * (math.cos(math.radians(theta_ap_ris)) ** (2.0 * q)))
    pattern_ris_ue_dB = 10.0 * math.log10(element_gain * (math.cos(math.radians(theta_ris_ue)) ** (2.0 * q)))

    return (
        20.0 * math.log10(n_total)
        + path_gain_ap_ris_dB
        + path_gain_ris_ue_dB
        + pattern_ap_ris_dB
        + pattern_ris_ue_dB
    )


@pytest.mark.parametrize(
    ("network_builder", "environment", "scenario"),
    [
        (build_simris_reference_network, "indoor", 1),
        (build_simris_scenario2_network, "indoor", 2),
        (build_simris_outdoor_network, "outdoor", 1),
    ],
)
def test_simris_channel_matches_deterministic_published_los_reference_and_beats_current_link_budget(
    network_builder,
    environment: str,
    scenario: int,
):
    reference_net = network_builder()
    comparison_net = network_builder()

    channel = SimRISChannel(
        SimRISLoSConfig(
            environment=environment,
            scenario=scenario,
            array_type="ula",
            include_direct_path=False,
        )
    )
    simris = channel.evaluate(
        reference_net,
        "ap1",
        "ris1",
        "ue1",
        frequency_GHz=28.0,
    )
    waveflow = comparison_net.connect(
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )

    expected_gain_dB = deterministic_simris_los_reference_gain_dB(
        reference_net,
        environment=environment,
    )
    simris_error = abs(simris.pwr_dBm - expected_gain_dB)
    waveflow_error = abs(waveflow["pwr_dBm"] - expected_gain_dB)

    assert simris.result["H"].shape == (64, 1)
    assert simris.result["h"].shape == (64, 1)
    assert simris.result["g"].shape == (64, 1)
    assert simris.result["G"].shape == (1, 64)
    assert simris.result["D"].shape == (1, 1)
    assert np.allclose(simris.result["h"], simris.result["H"])
    assert np.allclose(simris.result["g"].T, simris.result["G"])
    assert simris.pwr_dBm == pytest.approx(expected_gain_dB)
    assert simris.gain_dBi == pytest.approx(expected_gain_dB)
    assert simris.result["model"] == "simris_deterministic_los"
    assert simris_error < 1e-9
    assert simris_error < waveflow_error


def test_simris_stochastic_engine_returns_seeded_h_g_d_tensors_with_expected_shapes():
    net = build_simris_reference_network()

    tensors = evaluate_simris_from_nodes(
        net.get("ap1"),
        net.get("ris1"),
        net.get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=3,
        frequency_GHz=28.0,
        num_realizations=4,
        seed=7,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )

    assert tensors["H"].shape == (64, 2, 4)
    assert tensors["h"].shape == (64, 2, 4)
    assert tensors["g"].shape == (64, 3, 4)
    assert tensors["G"].shape == (3, 64, 4)
    assert tensors["D"].shape == (3, 2, 4)
    assert tensors["h_SISO"].shape == (3, 2, 4)
    assert np.allclose(tensors["h"], tensors["H"])
    assert np.allclose(np.transpose(tensors["g"], (1, 0, 2)), tensors["G"])
    assert np.allclose(tensors["h_SISO"], tensors["D"])
    assert len(tensors["metadata"]) == 4
    assert tensors["frequency_GHz"] == pytest.approx(28.0)
    assert tensors["environment"] == "indoor"
    assert tensors["scenario"] == 1
    assert tensors["array_type"] == "ula"
    assert tensors["num_realizations"] == 4
    assert tensors["channel_gain_linear"].shape == (4,)
    assert tensors["channel_gain_dB"].shape == (4,)
    assert tensors["los_path_gain_ap_ris_dB"].shape == (4,)
    assert tensors["los_path_gain_ris_ue_dB"].shape == (4,)
    assert tensors["los_path_gain_direct_dB"].shape == (4,)
    assert tensors["los_path_loss_ap_ris_dB"].shape == (4,)
    assert tensors["los_path_loss_ris_ue_dB"].shape == (4,)
    assert tensors["los_path_loss_direct_dB"].shape == (4,)
    assert tensors["theta_tx_ris_deg"].shape == (4,)
    assert tensors["theta_ris_ue_deg"].shape == (4,)
    assert tensors["ris_pattern_in_dB"].shape == (4,)
    assert tensors["ris_pattern_out_dB"].shape == (4,)


def test_simris_stochastic_helper_reports_per_realization_channel_gain_summary():
    tensors = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=2,
        seed=33,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )

    manual = []
    for idx in range(tensors["H"].shape[2]):
        phase_alignment = np.exp(-1j * np.angle(tensors["G"][0, :, idx] * tensors["H"][:, 0, idx]))
        gain_linear = float(
            np.linalg.norm(
                tensors["G"][:, :, idx] @ np.diag(phase_alignment) @ tensors["H"][:, :, idx] + tensors["D"][:, :, idx],
                ord="fro",
            )
            ** 2
        )
        manual.append(gain_linear)

    assert tensors["channel_gain_linear"] == pytest.approx(manual)
    assert tensors["channel_gain_dB"] == pytest.approx([10.0 * math.log10(max(value, 1e-30)) for value in manual])


def test_simris_stochastic_engine_is_deterministic_for_fixed_seed():
    net = build_simris_reference_network()
    channel = SimRISStochasticChannel(
        SimRISConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            tx_antennas=2,
            rx_antennas=2,
            frequency_GHz=28.0,
            num_realizations=3,
            seed=123,
            include_direct_path=True,
            include_nlos=True,
            include_shadow_fading=True,
        )
    )

    result_a = channel.evaluate(net, "ap1", "ris1", "ue1").result
    result_b = channel.evaluate(build_simris_reference_network(), "ap1", "ris1", "ue1").result

    assert np.allclose(result_a["H"], result_b["H"])
    assert np.allclose(result_a["G"], result_b["G"])
    assert np.allclose(result_a["D"], result_b["D"])
    assert np.allclose(result_a["h_SISO"], result_b["h_SISO"])
    assert result_a["pwr_dBm"] == pytest.approx(result_b["pwr_dBm"])
    assert result_a["noise_power_dBm"] == pytest.approx(result_b["noise_power_dBm"])


def test_simris_stochastic_adapter_exposes_noise_power_metric():
    result = SimRISStochasticChannel(
        SimRISConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            tx_antennas=1,
            rx_antennas=1,
            frequency_GHz=28.0,
            num_realizations=1,
            seed=123,
            include_direct_path=True,
            include_nlos=True,
            include_shadow_fading=True,
        )
    ).evaluate(build_simris_reference_network(), "ap1", "ris1", "ue1").result

    expected_noise = -174.0 + 10.0 * math.log10(20.0e6) + 6.0
    assert result["noise_power_dBm"] == pytest.approx(expected_noise)
    assert result["snr_dB"] == pytest.approx(result["pwr_dBm"] - result["noise_power_dBm"])
    assert result["gain_linear"] == pytest.approx(result["channel_gain_linear"][0])
    assert result["gain_dBi"] == pytest.approx(result["channel_gain_dB"][0])


def test_simris_stochastic_adapter_exposes_first_realization_scalar_link_summaries():
    deterministic = SimRISChannel(
        SimRISLoSConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            tx_antennas=1,
            rx_antennas=1,
            include_direct_path=True,
            frequency_GHz=28.0,
        )
    ).evaluate(build_simris_reference_network(), "ap1", "ris1", "ue1").result
    stochastic = SimRISStochasticChannel(
        SimRISConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            tx_antennas=1,
            rx_antennas=1,
            include_direct_path=True,
            frequency_GHz=28.0,
            num_realizations=1,
            seed=0,
            include_nlos=False,
            include_shadow_fading=False,
            force_tx_ris_los=True,
            force_ris_rx_los=True,
            force_direct_los=True,
        )
    ).evaluate(build_simris_reference_network(), "ap1", "ris1", "ue1").result

    assert stochastic["path_gain_ap_ris_dB"] == pytest.approx(deterministic["path_gain_ap_ris_dB"])
    assert stochastic["path_gain_ris_ue_dB"] == pytest.approx(deterministic["path_gain_ris_ue_dB"])
    assert stochastic["path_gain_direct_dB"] == pytest.approx(deterministic["path_gain_direct_dB"])
    assert stochastic["path_loss_ap_ris_dB"] == pytest.approx(deterministic["path_loss_ap_ris_dB"])
    assert stochastic["path_loss_ris_ue_dB"] == pytest.approx(deterministic["path_loss_ris_ue_dB"])
    assert stochastic["path_loss_direct_dB"] == pytest.approx(deterministic["path_loss_direct_dB"])
    assert stochastic["theta_tx_ris_deg"] == pytest.approx(deterministic["theta_tx_ris_deg"])
    assert stochastic["theta_ris_ue_deg"] == pytest.approx(deterministic["theta_ris_ue_deg"])
    assert stochastic["ris_pattern_in_dB"] == pytest.approx(deterministic["ris_pattern_in_dB"])
    assert stochastic["ris_pattern_out_dB"] == pytest.approx(deterministic["ris_pattern_out_dB"])


def test_simris_stochastic_adapter_scalar_los_summaries_are_nan_without_los():
    stochastic = SimRISStochasticChannel(
        SimRISConfig(
            environment="outdoor",
            scenario=1,
            array_type="ula",
            tx_antennas=1,
            rx_antennas=1,
            include_direct_path=True,
            frequency_GHz=28.0,
            num_realizations=1,
            seed=77,
            include_nlos=True,
            include_shadow_fading=False,
            force_tx_ris_los=False,
            force_ris_rx_los=False,
            force_direct_los=False,
        )
    ).evaluate(build_simris_outdoor_network(), "ap1", "ris1", "ue1").result

    assert math.isnan(stochastic["path_gain_ap_ris_dB"])
    assert math.isnan(stochastic["path_gain_ris_ue_dB"])
    assert math.isnan(stochastic["path_gain_direct_dB"])
    assert math.isnan(stochastic["path_loss_ap_ris_dB"])
    assert math.isnan(stochastic["path_loss_ris_ue_dB"])
    assert math.isnan(stochastic["path_loss_direct_dB"])
    assert math.isnan(stochastic["theta_tx_ris_deg"])
    assert math.isnan(stochastic["theta_ris_ue_deg"])
    assert math.isnan(stochastic["ris_pattern_in_dB"])
    assert math.isnan(stochastic["ris_pattern_out_dB"])


def test_simris_stochastic_engine_reduces_to_seeded_los_only_case_when_nlos_and_shadow_are_disabled():
    net = build_simris_reference_network()
    los_channel = SimRISChannel(
        SimRISLoSConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            include_direct_path=False,
            frequency_GHz=28.0,
        )
    )
    stochastic_channel = SimRISStochasticChannel(
        SimRISConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            tx_antennas=1,
            rx_antennas=1,
            include_direct_path=False,
            frequency_GHz=28.0,
            num_realizations=1,
            seed=0,
            include_nlos=False,
            include_shadow_fading=False,
            force_tx_ris_los=True,
            force_ris_rx_los=True,
            force_direct_los=True,
        )
    )

    los = los_channel.evaluate(net, "ap1", "ris1", "ue1").result
    stochastic = stochastic_channel.evaluate(build_simris_reference_network(), "ap1", "ris1", "ue1").result

    assert np.allclose(stochastic["H"][:, :, 0], los["H"])
    assert np.allclose(np.abs(stochastic["G"][:, :, 0]), np.abs(los["G"]))
    assert np.allclose(stochastic["D"][:, :, 0], np.zeros((1, 1), dtype=np.complex128))
    assert np.allclose(stochastic["h_SISO"][:, :, 0], stochastic["D"][:, :, 0])


def test_simris_los_only_stochastic_metadata_matches_deterministic_path_gain_summary():
    net = build_simris_reference_network()
    deterministic = evaluate_simris_los_from_nodes(
        net.get("ap1"),
        net.get("ris1"),
        net.get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        include_direct_path=True,
    )
    stochastic = evaluate_simris_from_nodes(
        net.get("ap1"),
        net.get("ris1"),
        net.get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=0,
        include_direct_path=True,
        include_nlos=False,
        include_shadow_fading=False,
        force_tx_ris_los=True,
        force_ris_rx_los=True,
        force_direct_los=True,
    )

    tx_meta = stochastic["metadata"][0]["tx_ris"]
    rx_meta = stochastic["metadata"][0]["ris_rx"]
    direct_meta = stochastic["metadata"][0]["direct"]

    assert tx_meta["distance_m"] == pytest.approx(np.linalg.norm(net.get("ap1").pos - net.get("ris1").pos))
    assert rx_meta["distance_m"] == pytest.approx(np.linalg.norm(net.get("ris1").pos - net.get("ue1").pos))
    assert direct_meta["distance_m"] == pytest.approx(np.linalg.norm(net.get("ap1").pos - net.get("ue1").pos))
    assert tx_meta["los_path_gain_dB"] == pytest.approx(deterministic["path_gain_ap_ris_dB"])
    assert rx_meta["los_path_gain_dB"] == pytest.approx(deterministic["path_gain_ris_ue_dB"])
    assert direct_meta["los_path_gain_dB"] == pytest.approx(deterministic["path_gain_direct_dB"])
    assert tx_meta["los_path_gain_linear"] == pytest.approx(10.0 ** (deterministic["path_gain_ap_ris_dB"] / 10.0))
    assert rx_meta["los_path_gain_linear"] == pytest.approx(10.0 ** (deterministic["path_gain_ris_ue_dB"] / 10.0))
    assert direct_meta["los_path_gain_linear"] == pytest.approx(10.0 ** (deterministic["path_gain_direct_dB"] / 10.0))
    assert deterministic["metadata"]["tx_ris"]["distance_m"] == pytest.approx(tx_meta["distance_m"])
    assert deterministic["metadata"]["ris_rx"]["distance_m"] == pytest.approx(rx_meta["distance_m"])
    assert deterministic["metadata"]["direct"]["distance_m"] == pytest.approx(direct_meta["distance_m"])
    assert deterministic["metadata"]["tx_ris"]["los_path_gain_dB"] == pytest.approx(tx_meta["los_path_gain_dB"])
    assert deterministic["metadata"]["ris_rx"]["los_path_gain_dB"] == pytest.approx(rx_meta["los_path_gain_dB"])
    assert deterministic["metadata"]["direct"]["los_path_gain_dB"] == pytest.approx(direct_meta["los_path_gain_dB"])
    assert stochastic["los_path_gain_ap_ris_dB"][0] == pytest.approx(deterministic["path_gain_ap_ris_dB"])
    assert stochastic["los_path_gain_ris_ue_dB"][0] == pytest.approx(deterministic["path_gain_ris_ue_dB"])
    assert stochastic["los_path_gain_direct_dB"][0] == pytest.approx(deterministic["path_gain_direct_dB"])
    assert stochastic["los_path_loss_ap_ris_dB"][0] == pytest.approx(deterministic["path_loss_ap_ris_dB"])
    assert stochastic["los_path_loss_ris_ue_dB"][0] == pytest.approx(deterministic["path_loss_ris_ue_dB"])
    assert stochastic["los_path_loss_direct_dB"][0] == pytest.approx(deterministic["path_loss_direct_dB"])
    assert stochastic["theta_tx_ris_deg"][0] == pytest.approx(deterministic["theta_tx_ris_deg"])
    assert stochastic["theta_ris_ue_deg"][0] == pytest.approx(deterministic["theta_ris_ue_deg"])
    assert stochastic["ris_pattern_in_dB"][0] == pytest.approx(deterministic["ris_pattern_in_dB"])
    assert stochastic["ris_pattern_out_dB"][0] == pytest.approx(deterministic["ris_pattern_out_dB"])


def test_simris_stochastic_los_component_summaries_are_nan_when_forced_los_is_disabled():
    tensors = evaluate_simris_from_nodes(
        build_simris_outdoor_network().get("ap1"),
        build_simris_outdoor_network().get("ris1"),
        build_simris_outdoor_network().get("ue1"),
        environment="outdoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=77,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=False,
        force_tx_ris_los=False,
        force_ris_rx_los=False,
        force_direct_los=False,
    )

    assert math.isnan(tensors["los_path_gain_ap_ris_dB"][0])
    assert math.isnan(tensors["los_path_gain_ris_ue_dB"][0])
    assert math.isnan(tensors["los_path_gain_direct_dB"][0])
    assert math.isnan(tensors["los_path_loss_ap_ris_dB"][0])
    assert math.isnan(tensors["los_path_loss_ris_ue_dB"][0])
    assert math.isnan(tensors["los_path_loss_direct_dB"][0])
    assert math.isnan(tensors["theta_tx_ris_deg"][0])
    assert math.isnan(tensors["theta_ris_ue_deg"][0])
    assert math.isnan(tensors["ris_pattern_in_dB"][0])
    assert math.isnan(tensors["ris_pattern_out_dB"][0])


def test_simris_stochastic_nlos_metadata_reports_cluster_and_scatterer_counts():
    indoor = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=21,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )
    outdoor = evaluate_simris_from_nodes(
        build_simris_outdoor_network().get("ap1"),
        build_simris_outdoor_network().get("ris1"),
        build_simris_outdoor_network().get("ue1"),
        environment="outdoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=22,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )

    indoor_tx = indoor["metadata"][0]["tx_ris"]
    indoor_direct = indoor["metadata"][0]["direct"]
    outdoor_rx = outdoor["metadata"][0]["ris_rx"]
    outdoor_direct = outdoor["metadata"][0]["direct"]

    assert indoor_tx["nlos_cluster_count"] >= 1
    assert indoor_tx["nlos_subray_count"] >= indoor_tx["nlos_cluster_count"]
    assert indoor_tx["nlos_active_scatterer_count"] >= 1
    assert indoor_direct["nlos_cluster_count"] == indoor_tx["nlos_cluster_count"]
    assert indoor_direct["nlos_active_scatterer_count"] == indoor_tx["nlos_active_scatterer_count"]

    assert outdoor_rx["nlos_cluster_count"] >= 1
    assert outdoor_rx["nlos_subray_count"] >= outdoor_rx["nlos_cluster_count"]
    assert outdoor_rx["nlos_active_scatterer_count"] >= 1
    assert outdoor_direct["nlos_cluster_count"] >= 1
    assert outdoor_direct["nlos_subray_count"] >= outdoor_direct["nlos_cluster_count"]
    assert outdoor_direct["nlos_active_scatterer_count"] >= 1


def test_simris_direct_link_generates_seeded_indoor_nlos_when_los_is_forced_off():
    tensors = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=99,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=False,
        force_tx_ris_los=True,
        force_ris_rx_los=True,
        force_direct_los=False,
    )

    direct = tensors["D"][:, :, 0]
    assert not np.allclose(direct, np.zeros((1, 1), dtype=np.complex128))
    assert tensors["metadata"][0]["direct"]["los_indicator"] == 0


def test_simris_direct_link_stays_zero_when_both_los_and_nlos_are_disabled():
    tensors = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        num_realizations=1,
        seed=99,
        include_direct_path=True,
        include_nlos=False,
        include_shadow_fading=False,
        force_tx_ris_los=True,
        force_ris_rx_los=True,
        force_direct_los=False,
    )

    assert np.allclose(tensors["D"][:, :, 0], np.zeros((1, 1), dtype=np.complex128))


def test_simris_scenario2_branch_returns_valid_deterministic_los_tensors():
    net = build_simris_scenario2_network()
    result = SimRISChannel(
        SimRISLoSConfig(
            environment="indoor",
            scenario=2,
            array_type="ula",
            include_direct_path=False,
            frequency_GHz=28.0,
        )
    ).evaluate(net, "ap1", "ris1", "ue1").result

    assert result["H"].shape == (64, 1)
    assert result["G"].shape == (1, 64)
    assert result["channel_gain_linear"] > 0.0
    assert result["scenario"] == 2


def test_simris_upa_branch_accepts_square_terminal_arrays():
    net = build_simris_reference_network()
    tensors = evaluate_simris_from_nodes(
        net.get("ap1"),
        net.get("ris1"),
        net.get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="upa",
        tx_antennas=4,
        rx_antennas=4,
        frequency_GHz=28.0,
        num_realizations=2,
        seed=17,
        include_direct_path=True,
        include_nlos=False,
        include_shadow_fading=False,
        force_tx_ris_los=True,
        force_ris_rx_los=True,
        force_direct_los=True,
    )

    assert tensors["H"].shape == (64, 4, 2)
    assert tensors["G"].shape == (4, 64, 2)
    assert tensors["D"].shape == (4, 4, 2)
    assert np.any(np.abs(tensors["H"]) > 0.0)
    assert np.any(np.abs(tensors["G"]) > 0.0)


def test_simris_outdoor_stochastic_branch_is_seed_deterministic():
    channel = SimRISStochasticChannel(
        SimRISConfig(
            environment="outdoor",
            scenario=1,
            array_type="ula",
            tx_antennas=2,
            rx_antennas=2,
            frequency_GHz=28.0,
            num_realizations=2,
            seed=202,
            include_direct_path=True,
            include_nlos=True,
            include_shadow_fading=True,
        )
    )

    result_a = channel.evaluate(build_simris_outdoor_network(), "ap1", "ris1", "ue1").result
    result_b = channel.evaluate(build_simris_outdoor_network(), "ap1", "ris1", "ue1").result

    assert np.allclose(result_a["H"], result_b["H"])
    assert np.allclose(result_a["G"], result_b["G"])
    assert np.allclose(result_a["D"], result_b["D"])
    assert result_a["metadata"][0]["ris_rx"]["los_indicator"] in (0, 1)


def test_simris_indoor_ris_rx_los_branch_changes_with_seed_due_to_random_rx_aoa():
    base_kwargs = dict(
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=2,
        frequency_GHz=28.0,
        num_realizations=1,
        include_direct_path=False,
        include_nlos=False,
        include_shadow_fading=False,
        force_tx_ris_los=True,
        force_ris_rx_los=True,
        force_direct_los=False,
    )

    result_a = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        seed=11,
        **base_kwargs,
    )
    result_b = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        seed=12,
        **base_kwargs,
    )

    assert not np.allclose(result_a["G"], result_b["G"])


def test_simris_indoor_seeded_signature_matches_frozen_regression_fixture():
    tensors = evaluate_simris_from_nodes(
        build_simris_reference_network().get("ap1"),
        build_simris_reference_network().get("ris1"),
        build_simris_reference_network().get("ue1"),
        environment="indoor",
        scenario=1,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=2,
        frequency_GHz=28.0,
        num_realizations=2,
        seed=123,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )
    signature = summarize_simris_tensors(tensors)

    assert signature["H_norms"] == pytest.approx([0.0008713406596906708, 0.0007527523031595266])
    assert signature["G_norms"] == pytest.approx([0.007962119534477254, 0.006293720791525881])
    assert signature["D_norms"] == pytest.approx([2.770621818966747e-06, 6.368444033005381e-06])
    assert signature["h_SISO_norms"] == pytest.approx([2.770621818966747e-06, 6.368444033005381e-06])
    assert signature["H00"].real == pytest.approx(6.963013549129728e-05)
    assert signature["H00"].imag == pytest.approx(2.58166191682145e-05)
    assert signature["G00"].real == pytest.approx(0.00035863173546447555)
    assert signature["G00"].imag == pytest.approx(-0.0006055240957347842)
    assert signature["D00"].real == pytest.approx(-8.124416309709132e-07)
    assert signature["D00"].imag == pytest.approx(-4.25709645149441e-07)
    assert signature["h_SISO00"].real == pytest.approx(-8.124416309709132e-07)
    assert signature["h_SISO00"].imag == pytest.approx(-4.25709645149441e-07)


def test_simris_outdoor_seeded_signature_matches_frozen_regression_fixture():
    tensors = evaluate_simris_from_nodes(
        build_simris_outdoor_network().get("ap1"),
        build_simris_outdoor_network().get("ris1"),
        build_simris_outdoor_network().get("ue1"),
        environment="outdoor",
        scenario=1,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=2,
        frequency_GHz=28.0,
        num_realizations=2,
        seed=202,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )
    signature = summarize_simris_tensors(tensors)

    assert signature["H_norms"] == pytest.approx([2.2520758190304584e-05, 1.664515655837888e-05])
    assert signature["G_norms"] == pytest.approx([0.0009251347627465981, 0.0013428654556513926])
    assert signature["D_norms"] == pytest.approx([2.3447434318491114e-06, 1.5103853792998994e-06])
    assert signature["h_SISO_norms"] == pytest.approx([2.3447434318491114e-06, 1.5103853792998994e-06])
    assert signature["H00"].real == pytest.approx(-5.862142444051456e-07)
    assert signature["H00"].imag == pytest.approx(1.6858786456650883e-06)
    assert signature["G00"].real == pytest.approx(-3.374255984337797e-05)
    assert signature["G00"].imag == pytest.approx(-8.294272222703915e-05)
    assert signature["D00"].real == pytest.approx(-1.0542249101495944e-06)
    assert signature["D00"].imag == pytest.approx(3.6129054991810733e-07)
    assert signature["h_SISO00"].real == pytest.approx(-1.0542249101495944e-06)
    assert signature["h_SISO00"].imag == pytest.approx(3.6129054991810733e-07)


def test_simris_validation_accepts_published_style_indoor_geometry():
    net = build_simris_reference_network()
    result = validate_simris_configuration(
        net.get("ap1").pos,
        net.get("ris1").pos,
        net.get("ue1").pos,
        environment="indoor",
        frequency_GHz=28.0,
        ris_side=8,
        tx_antennas=1,
        rx_antennas=1,
    )

    assert result.ok is True
    assert result.errors == ()


def test_simris_validation_reports_multiple_matlab_style_geometry_errors():
    result = validate_simris_configuration(
        tx_xyz=np.array([1.0, 25.0, 25.0]),
        ris_xyz=np.array([40.0, 50.0, 10.0]),
        rx_xyz=np.array([150.0, 120.0, 3.0]),
        environment="outdoor",
        frequency_GHz=28.0,
        ris_side=8,
        tx_antennas=3,
        rx_antennas=2,
    )

    assert result.ok is False
    assert "Tx should be on xz plane with x=0" in result.errors
    assert "Rx is a ground user equipment; z should be less than or equal to 2" in result.errors
    assert "Nt should be an even square count in SimRIS-style array mode" in result.errors
    assert "Nr should be an even square count in SimRIS-style array mode" in result.errors
    assert "Typical Tx height is 20 meters for outdoor UMi Street Canyon" in result.errors
    assert "Typical cell radius max is 100 meters for outdoor UMi Street Canyon" in result.errors


def test_simris_validation_warns_when_frequency_is_not_published_reference_band():
    net = build_simris_reference_network()
    result = validate_simris_configuration(
        net.get("ap1").pos,
        net.get("ris1").pos,
        net.get("ue1").pos,
        environment="indoor",
        frequency_GHz=60.0,
        ris_side=8,
        tx_antennas=1,
        rx_antennas=1,
    )

    assert any("28 GHz or 73 GHz" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    ("environment", "scenario", "expected_tx", "expected_ris", "expected_rx"),
    [
        ("indoor", 1, (0.0, 25.0, 2.0), (40.0, 50.0, 2.0), (38.0, 48.0, 1.0)),
        ("indoor", 2, (0.0, 25.0, 2.0), (70.0, 30.0, 2.0), (70.0, 35.0, 1.0)),
        ("outdoor", 1, (0.0, 25.0, 20.0), (70.0, 85.0, 10.0), (80.0, 75.0, 1.0)),
        ("outdoor", 2, (0.0, 25.0, 20.0), (85.0, 40.0, 10.0), (70.0, 65.0, 1.0)),
    ],
)
def test_simris_published_geometry_presets_match_gui_recommendations_and_validate(
    environment: str,
    scenario: int,
    expected_tx: tuple[float, float, float],
    expected_ris: tuple[float, float, float],
    expected_rx: tuple[float, float, float],
):
    geometry = get_simris_published_geometry(environment=environment, scenario=scenario)

    assert tuple(geometry["tx_xyz"].tolist()) == expected_tx
    assert tuple(geometry["ris_xyz"].tolist()) == expected_ris
    assert tuple(geometry["rx_xyz"].tolist()) == expected_rx

    validation = validate_simris_configuration(
        geometry["tx_xyz"],
        geometry["ris_xyz"],
        geometry["rx_xyz"],
        environment=environment,
        frequency_GHz=28.0,
        ris_side=8,
        tx_antennas=1,
        rx_antennas=1,
    )
    assert validation.ok is True


def test_simris_published_case_helpers_cover_outdoor_scenario2_end_to_end():
    los = evaluate_simris_los_published_case(
        environment="outdoor",
        scenario=2,
        ris_side=8,
        frequency_GHz=28.0,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        include_direct_path=True,
    )
    stochastic = simulate_simris_published_case(
        environment="outdoor",
        scenario=2,
        ris_side=8,
        frequency_GHz=28.0,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=2,
        num_realizations=2,
        seed=404,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )

    assert los["environment"] == "outdoor"
    assert los["scenario"] == 2
    assert los["H"].shape == (64, 1)
    assert los["G"].shape == (1, 64)
    assert los["D"].shape == (1, 1)
    assert np.allclose(los["g"].T, los["G"])

    assert stochastic["H"].shape == (64, 2, 2)
    assert stochastic["g"].shape == (64, 2, 2)
    assert stochastic["G"].shape == (2, 64, 2)
    assert stochastic["D"].shape == (2, 2, 2)
    assert np.allclose(np.transpose(stochastic["g"], (1, 0, 2)), stochastic["G"])
    assert len(stochastic["metadata"]) == 2


def test_simris_published_network_builder_matches_reference_network_and_runs_channel():
    built = build_simris_published_network(
        environment="indoor",
        scenario=1,
        ris_side=8,
        frequency_GHz=28.0,
    )
    reference = build_simris_reference_network()

    assert np.allclose(built.get("ap1").pos, reference.get("ap1").pos)
    assert np.allclose(built.get("ris1").pos, reference.get("ris1").pos)
    assert np.allclose(built.get("ue1").pos, reference.get("ue1").pos)
    assert built.get("ris1").N == 8
    assert built.get("ap1").freq == pytest.approx(28e9)
    assert built.get("ris1").freq == pytest.approx(28e9)

    result = SimRISChannel(
        SimRISLoSConfig(
            environment="indoor",
            scenario=1,
            array_type="ula",
            include_direct_path=False,
            frequency_GHz=28.0,
        )
    ).evaluate(built, "ap1", "ris1", "ue1")

    assert result.result["H"].shape == (64, 1)
    assert result.result["G"].shape == (1, 64)
    assert result.result["channel_gain_linear"] > 0.0


def test_simris_published_network_builder_propagates_custom_frequency_to_ap_and_ris():
    built = build_simris_published_network(
        environment="outdoor",
        scenario=2,
        ris_side=8,
        frequency_GHz=73.0,
    )

    assert built.get("ap1").freq == pytest.approx(73e9)
    assert built.get("ris1").freq == pytest.approx(73e9)


@pytest.mark.parametrize(
    ("environment", "scenario"),
    [
        ("indoor", 1),
        ("indoor", 2),
        ("outdoor", 1),
        ("outdoor", 2),
    ],
)
def test_simris_published_case_and_built_network_match_deterministic_los_results(
    environment: str,
    scenario: int,
):
    built = build_simris_published_network(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
    )
    direct = evaluate_simris_los_published_case(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        include_direct_path=True,
    )
    via_nodes = evaluate_simris_los_from_nodes(
        built.get("ap1"),
        built.get("ris1"),
        built.get("ue1"),
        environment=environment,
        scenario=scenario,
        array_type="ula",
        tx_antennas=1,
        rx_antennas=1,
        frequency_GHz=28.0,
        include_direct_path=True,
    )

    assert np.allclose(direct["H"], via_nodes["H"])
    assert np.allclose(direct["G"], via_nodes["G"])
    assert np.allclose(direct["D"], via_nodes["D"])
    assert direct["channel_gain_linear"] == pytest.approx(via_nodes["channel_gain_linear"])
    assert direct["channel_gain_dB"] == pytest.approx(via_nodes["channel_gain_dB"])


@pytest.mark.parametrize(
    ("environment", "scenario"),
    [
        ("indoor", 1),
        ("indoor", 2),
        ("outdoor", 1),
        ("outdoor", 2),
    ],
)
def test_simris_published_case_and_built_network_match_stochastic_results(
    environment: str,
    scenario: int,
):
    built = build_simris_published_network(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
    )
    direct = simulate_simris_published_case(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=2,
        num_realizations=2,
        seed=909,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )
    via_nodes = evaluate_simris_from_nodes(
        built.get("ap1"),
        built.get("ris1"),
        built.get("ue1"),
        environment=environment,
        scenario=scenario,
        array_type="ula",
        tx_antennas=2,
        rx_antennas=2,
        frequency_GHz=28.0,
        num_realizations=2,
        seed=909,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )

    assert np.allclose(direct["H"], via_nodes["H"])
    assert np.allclose(direct["G"], via_nodes["G"])
    assert np.allclose(direct["D"], via_nodes["D"])
    assert np.allclose(direct["h"], via_nodes["h"])
    assert np.allclose(direct["g"], via_nodes["g"])
    assert np.allclose(direct["h_SISO"], via_nodes["h_SISO"])
    assert len(direct["metadata"]) == len(via_nodes["metadata"]) == 2
    for direct_meta, via_meta in zip(direct["metadata"], via_nodes["metadata"], strict=True):
        assert direct_meta["tx_ris"]["los_indicator"] == via_meta["tx_ris"]["los_indicator"]
        assert direct_meta["ris_rx"]["los_indicator"] == via_meta["ris_rx"]["los_indicator"]
        assert direct_meta["direct"]["los_indicator"] == via_meta["direct"]["los_indicator"]


@pytest.mark.parametrize(
    ("environment", "scenario"),
    [
        ("indoor", 1),
        ("indoor", 2),
        ("outdoor", 1),
        ("outdoor", 2),
    ],
)
def test_simris_published_case_adapter_helpers_match_built_network_adapters(
    environment: str,
    scenario: int,
):
    built = build_simris_published_network(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
    )
    deterministic_direct = evaluate_simris_channel_published_case(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
        include_direct_path=True,
    )
    deterministic_via_network = SimRISChannel(
        SimRISLoSConfig(
            environment=environment,
            scenario=scenario,
            array_type="ula",
            include_direct_path=True,
            frequency_GHz=28.0,
        )
    ).evaluate(built, "ap1", "ris1", "ue1")

    stochastic_direct = evaluate_simris_stochastic_channel_published_case(
        environment=environment,
        scenario=scenario,
        ris_side=8,
        frequency_GHz=28.0,
        tx_antennas=2,
        rx_antennas=2,
        num_realizations=2,
        seed=111,
        include_direct_path=True,
        include_nlos=True,
        include_shadow_fading=True,
    )
    stochastic_via_network = SimRISStochasticChannel(
        SimRISConfig(
            environment=environment,
            scenario=scenario,
            array_type="ula",
            tx_antennas=2,
            rx_antennas=2,
            include_direct_path=True,
            frequency_GHz=28.0,
            num_realizations=2,
            seed=111,
            include_nlos=True,
            include_shadow_fading=True,
        )
    ).evaluate(built, "ap1", "ris1", "ue1")

    assert deterministic_direct.pwr_dBm == pytest.approx(deterministic_via_network.pwr_dBm)
    assert deterministic_direct.snr_dB == pytest.approx(deterministic_via_network.snr_dB)
    assert np.allclose(deterministic_direct.result["H"], deterministic_via_network.result["H"])
    assert np.allclose(deterministic_direct.result["G"], deterministic_via_network.result["G"])
    assert np.allclose(deterministic_direct.result["D"], deterministic_via_network.result["D"])

    assert stochastic_direct.pwr_dBm == pytest.approx(stochastic_via_network.pwr_dBm)
    assert stochastic_direct.snr_dB == pytest.approx(stochastic_via_network.snr_dB)
    assert np.allclose(stochastic_direct.result["H"], stochastic_via_network.result["H"])
    assert np.allclose(stochastic_direct.result["G"], stochastic_via_network.result["G"])
    assert np.allclose(stochastic_direct.result["D"], stochastic_via_network.result["D"])


def test_simris_stochastic_channel_preflight_can_raise_on_invalid_geometry():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 1.0, 25.0, 25.0, power_dBm=0.0, freq=28e9, antenna_gain_dBi=0.0, bandwidth_MHz=20.0)
    net.add_ris("ris1", 40.0, 50.0, 10.0, N=8, bits=0, max_angle_deg=180.0, normal_angle_deg=0.0)
    net.add_ue("ue1", 150.0, 120.0, 3.0, antenna_gain_dBi=0.0, noise_figure_dB=6.0)

    channel = SimRISStochasticChannel(
        SimRISConfig(
            environment="outdoor",
            scenario=1,
            frequency_GHz=28.0,
            validate_preflight=True,
            error_on_invalid=True,
        )
    )

    with pytest.raises(ValueError) as exc_info:
        channel.evaluate(net, "ap1", "ris1", "ue1")

    message = str(exc_info.value)
    assert "Tx should be on xz plane with x=0" in message
    assert "Rx is a ground user equipment" in message


def test_simris_stochastic_channel_preflight_can_report_without_blocking():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 1.0, 25.0, 25.0, power_dBm=0.0, freq=28e9, antenna_gain_dBi=0.0, bandwidth_MHz=20.0)
    net.add_ris("ris1", 40.0, 50.0, 10.0, N=8, bits=0, max_angle_deg=180.0, normal_angle_deg=0.0)
    net.add_ue("ue1", 150.0, 120.0, 3.0, antenna_gain_dBi=0.0, noise_figure_dB=6.0)

    channel = SimRISStochasticChannel(
        SimRISConfig(
            environment="outdoor",
            scenario=1,
            frequency_GHz=28.0,
            validate_preflight=True,
            error_on_invalid=False,
            seed=7,
            num_realizations=1,
        )
    )
    result = channel.evaluate(net, "ap1", "ris1", "ue1").result

    assert result["validation"]["ok"] is False
    assert "Tx should be on xz plane with x=0" in result["validation"]["errors"]


def test_simris_raw_los_helper_preflight_can_raise_on_invalid_geometry():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 1.0, 25.0, 25.0, power_dBm=0.0, freq=28e9, antenna_gain_dBi=0.0, bandwidth_MHz=20.0)
    net.add_ris("ris1", 40.0, 50.0, 10.0, N=8, bits=0, max_angle_deg=180.0, normal_angle_deg=0.0)
    net.add_ue("ue1", 150.0, 120.0, 3.0, antenna_gain_dBi=0.0, noise_figure_dB=6.0)

    with pytest.raises(ValueError) as exc_info:
        evaluate_simris_los_from_nodes(
            net.nodes["ap1"],
            net.nodes["ris1"],
            net.nodes["ue1"],
            environment="outdoor",
            scenario=1,
            frequency_GHz=28.0,
            validate_preflight=True,
            error_on_invalid=True,
        )

    message = str(exc_info.value)
    assert "Tx should be on xz plane with x=0" in message
    assert "Rx is a ground user equipment" in message


def test_simris_raw_stochastic_helper_preflight_can_report_without_blocking():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 1.0, 25.0, 25.0, power_dBm=0.0, freq=28e9, antenna_gain_dBi=0.0, bandwidth_MHz=20.0)
    net.add_ris("ris1", 40.0, 50.0, 10.0, N=8, bits=0, max_angle_deg=180.0, normal_angle_deg=0.0)
    net.add_ue("ue1", 150.0, 120.0, 3.0, antenna_gain_dBi=0.0, noise_figure_dB=6.0)

    result = evaluate_simris_from_nodes(
        net.nodes["ap1"],
        net.nodes["ris1"],
        net.nodes["ue1"],
        environment="outdoor",
        scenario=1,
        frequency_GHz=28.0,
        seed=7,
        num_realizations=1,
        validate_preflight=True,
        error_on_invalid=False,
    )

    assert result["validation"]["ok"] is False
    assert "Tx should be on xz plane with x=0" in result["validation"]["errors"]
    assert any("Rx is a ground user equipment" in error for error in result["validation"]["errors"])


def test_simris_published_case_raw_helpers_surface_preflight_warnings_and_errors():
    los = evaluate_simris_los_published_case(
        environment="indoor",
        scenario=1,
        ris_side=8,
        frequency_GHz=60.0,
        validate_preflight=True,
        error_on_invalid=False,
    )
    stochastic = simulate_simris_published_case(
        environment="indoor",
        scenario=1,
        ris_side=8,
        frequency_GHz=28.0,
        tx_antennas=3,
        num_realizations=1,
        seed=11,
        validate_preflight=True,
        error_on_invalid=False,
    )

    assert los["validation"]["ok"] is True
    assert "Published SimRIS examples and tuned parameters target 28 GHz or 73 GHz" in los["validation"]["warnings"]
    assert stochastic["validation"]["ok"] is False
    assert "Nt should be an even square count in SimRIS-style array mode" in stochastic["validation"]["errors"]


def test_simris_base_los_reference_can_surface_preflight_warning():
    geometry = get_simris_published_geometry(environment="indoor", scenario=1)
    result = evaluate_simris_los_reference(
        geometry["tx_xyz"],
        geometry["ris_xyz"],
        geometry["rx_xyz"],
        ris_side=8,
        frequency_GHz=60.0,
        environment="indoor",
        scenario=1,
        validate_preflight=True,
        error_on_invalid=False,
    )

    assert result["validation"]["ok"] is True
    assert "Published SimRIS examples and tuned parameters target 28 GHz or 73 GHz" in result["validation"]["warnings"]


def test_simris_base_stochastic_generator_can_raise_on_invalid_preflight():
    with pytest.raises(ValueError) as exc_info:
        simulate_simris_channels(
            np.array([1.0, 25.0, 25.0], dtype=float),
            np.array([40.0, 50.0, 10.0], dtype=float),
            np.array([150.0, 120.0, 3.0], dtype=float),
            ris_side=8,
            frequency_GHz=28.0,
            environment="outdoor",
            scenario=1,
            tx_antennas=1,
            rx_antennas=1,
            num_realizations=1,
            seed=7,
            validate_preflight=True,
            error_on_invalid=True,
        )

    message = str(exc_info.value)
    assert "Tx should be on xz plane with x=0" in message
    assert "Rx is a ground user equipment" in message


def test_simris_published_case_adapter_helper_can_surface_preflight_warning():
    result = evaluate_simris_channel_published_case(
        environment="indoor",
        scenario=1,
        ris_side=8,
        frequency_GHz=60.0,
        validate_preflight=True,
        error_on_invalid=False,
    ).result

    assert result["validation"]["ok"] is True
    assert "Published SimRIS examples and tuned parameters target 28 GHz or 73 GHz" in result["validation"]["warnings"]


def test_simris_published_case_stochastic_adapter_helper_can_report_invalid_preflight():
    result = evaluate_simris_stochastic_channel_published_case(
        environment="indoor",
        scenario=1,
        ris_side=8,
        frequency_GHz=28.0,
        tx_antennas=3,
        num_realizations=1,
        seed=5,
        validate_preflight=True,
        error_on_invalid=False,
    ).result

    assert result["validation"]["ok"] is False
    assert "Nt should be an even square count in SimRIS-style array mode" in result["validation"]["errors"]
