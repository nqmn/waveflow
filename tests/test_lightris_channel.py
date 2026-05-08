"""Equivalence tests for the Phase 3 LightRIS channel adapter."""

import pytest

from core import RISNetwork
from risnet.channels import (
    ChannelEvaluation,
    ChannelModel,
    LightRISChannel,
    build_lightris_config,
    build_lightris_config_from_nodes,
    evaluate_lightris_from_nodes,
    evaluate_lightris_metrics,
)
from utils.lightris import (
    build_lightris_config as low_level_build_lightris_config,
    build_lightris_config_from_nodes as low_level_build_lightris_config_from_nodes,
    evaluate_lightris_metrics as low_level_evaluate_lightris_metrics,
)


def build_channel_network(*, max_angle_deg=180):
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 5, 0, max_angle_deg=max_angle_deg)
    net.add_ue("ue1", 10, 0)
    return net


def test_waveflow_lightris_module_reexports_official_adapter():
    from waveflow.channels.lightris import LightRISChannel as WaveflowLightRISChannel

    assert WaveflowLightRISChannel is LightRISChannel


def test_lightris_channel_reproduces_current_connect_metrics():
    direct_net = build_channel_network()
    adapter_net = build_channel_network()
    channel: ChannelModel = LightRISChannel()

    direct = direct_net.connect(
        "ap1",
        "ris1",
        "ue1",
        channel_model="lightris",
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )
    evaluation = channel.evaluate(
        adapter_net,
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
    )

    assert isinstance(evaluation, ChannelEvaluation)
    for key in (
        "snr_dB",
        "pwr_dBm",
        "rssi_dBm",
        "gain_linear",
        "gain_dBi",
        "quant_loss_dB",
        "beam_angle",
    ):
        assert evaluation.result[key] == pytest.approx(direct[key])

    assert evaluation.snr_dB == pytest.approx(direct["snr_dB"])
    assert evaluation.pwr_dBm == pytest.approx(direct["pwr_dBm"])
    assert evaluation.rssi_dBm == pytest.approx(direct["rssi_dBm"])
    assert evaluation.gain_dBi == pytest.approx(direct["gain_dBi"])
    assert evaluation.quant_loss_dB == pytest.approx(direct["quant_loss_dB"])
    assert evaluation.result["channel_model_requested"] == "lightris"
    assert evaluation.result["channel_model_used"] == "lightris"


def test_phase3_shared_lightris_helpers_preserve_utils_compatibility():
    net = build_channel_network()
    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    channel_config = build_lightris_config()
    compat_config = low_level_build_lightris_config()
    assert channel_config == compat_config

    channel_node_config = build_lightris_config_from_nodes(ap, ris, ue)
    compat_node_config = low_level_build_lightris_config_from_nodes(ap, ris, ue)
    assert channel_node_config == compat_node_config

    beam_angle_deg = 0.0
    direct_metrics = evaluate_lightris_metrics(ap.pos, ris.pos, ue.pos, beam_angle_deg, channel_node_config)
    compat_metrics = low_level_evaluate_lightris_metrics(
        ap.pos, ris.pos, ue.pos, beam_angle_deg, compat_node_config
    )

    assert direct_metrics.keys() == compat_metrics.keys()
    for key in direct_metrics:
        if isinstance(direct_metrics[key], dict):
            assert direct_metrics[key] == compat_metrics[key]
        else:
            assert direct_metrics[key] == pytest.approx(compat_metrics[key])


def test_phase3_lightris_node_helper_matches_channel_adapter_inputs():
    net = build_channel_network()
    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    helper_result = evaluate_lightris_from_nodes(ap, ris, ue, beam_angle_deg=0.0)
    direct_result = evaluate_lightris_metrics(
        ap.pos,
        ris.pos,
        ue.pos,
        0.0,
        build_lightris_config_from_nodes(ap, ris, ue),
    )

    assert helper_result.keys() == direct_result.keys()
    for key in helper_result:
        if isinstance(helper_result[key], dict):
            assert helper_result[key] == direct_result[key]
        else:
            assert helper_result[key] == pytest.approx(direct_result[key])

def test_lightris_channel_preserves_phase_payload_shape():
    net = build_channel_network()
    channel = LightRISChannel()

    evaluation = channel.evaluate(
        net,
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
    )
    ris = net.get("ris1")

    assert len(evaluation.result["current_phases"]) == ris.N * ris.N
    assert len(evaluation.result["quantized_phases"]) == ris.N * ris.N
    assert len(evaluation.result["phase_states"]) == ris.N * ris.N


def test_lightris_channel_is_deterministic_for_seeded_links():
    channel = LightRISChannel()
    result_a = channel.evaluate(
        build_channel_network(),
        "ap1",
        "ris1",
        "ue1",
        seed=123,
        use_get_snr=False,
    )
    result_b = channel.evaluate(
        build_channel_network(),
        "ap1",
        "ris1",
        "ue1",
        seed=123,
        use_get_snr=False,
    )

    assert result_a.snr_dB == pytest.approx(result_b.snr_dB)
    assert result_a.pwr_dBm == pytest.approx(result_b.pwr_dBm)
    assert result_a.gain_dBi == pytest.approx(result_b.gain_dBi)


def test_lightris_channel_defaults_to_no_active_link_mutation():
    net = build_channel_network()
    channel = LightRISChannel()

    evaluation = channel.evaluate(net, "ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    assert net.active_links == {}
    assert net.last_connect_result["metrics"]["snr_dB"] == pytest.approx(evaluation.snr_dB)


def test_lightris_channel_can_preserve_legacy_active_link_mutation():
    net = build_channel_network()
    channel = LightRISChannel(store_in_active_links=True)

    evaluation = channel.evaluate(net, "ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    link_key = "ap1→ris1→ue1 (Connect)"
    assert link_key in net.active_links
    assert net.active_links[link_key]["snr_dB"] == pytest.approx(evaluation.snr_dB)


def test_lightris_channel_propagates_missing_node_errors():
    channel = LightRISChannel()

    with pytest.raises(ValueError) as exc_info:
        channel.evaluate(build_channel_network(), "missing-ap", "ris1", "ue1")

    assert "Invalid node name" in str(exc_info.value)
    assert "AP 'missing-ap'" in str(exc_info.value)


def test_lightris_channel_propagates_fov_rejections():
    channel = LightRISChannel()

    with pytest.raises(ValueError) as exc_info:
        channel.evaluate(
            build_channel_network(max_angle_deg=60),
            "ap1",
            "ris1",
            "ue1",
            seed=42,
            use_get_snr=False,
        )

    assert "AP outside RIS FOV" in str(exc_info.value)


def test_lightris_channel_reproduces_current_connect_for_environment_blocked_paths():
    direct_net = build_channel_network()
    adapter_net = build_channel_network()
    direct_net.add_wall((2.5, -1.0), (2.5, 1.0), attenuation_dB=30.0, name="ap-ris-wall")
    adapter_net.add_wall((2.5, -1.0), (2.5, 1.0), attenuation_dB=30.0, name="ap-ris-wall")

    has_los, attenuation_dB = adapter_net.environment.check_line_of_sight(
        adapter_net.get("ap1").pos,
        adapter_net.get("ris1").pos,
    )
    assert has_los is False
    assert attenuation_dB == pytest.approx(30.0)

    direct = direct_net.connect(
        "ap1",
        "ris1",
        "ue1",
        channel_model="lightris",
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )
    evaluation = LightRISChannel().evaluate(
        adapter_net,
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
    )

    assert evaluation.snr_dB == pytest.approx(direct["snr_dB"])
    assert evaluation.pwr_dBm == pytest.approx(direct["pwr_dBm"])
    assert evaluation.gain_dBi == pytest.approx(direct["gain_dBi"])


def test_lightris_channel_explicitly_pins_the_official_native_engine_name():
    net = build_channel_network()

    evaluation = LightRISChannel().evaluate(
        net,
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
    )

    assert evaluation.result["channel_model_requested"] == "lightris"
    assert evaluation.result["channel_model_used"] == "lightris"
    assert evaluation.result["channel_model_fallback_reason"] is None
