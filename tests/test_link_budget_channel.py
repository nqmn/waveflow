"""Equivalence tests for the Phase 3 link-budget channel adapter."""

import pytest

from core import RISNetwork
from risnet.channels import ChannelEvaluation, ChannelModel, LinkBudgetChannel


def build_channel_network(*, max_angle_deg=180):
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 5, 0, max_angle_deg=max_angle_deg)
    net.add_ue("ue1", 10, 0)
    return net


def test_link_budget_channel_reproduces_current_connect_metrics():
    direct_net = build_channel_network()
    adapter_net = build_channel_network()
    channel: ChannelModel = LinkBudgetChannel()

    direct = direct_net.connect(
        "ap1",
        "ris1",
        "ue1",
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


def test_link_budget_channel_preserves_phase_payload_shape():
    net = build_channel_network()
    channel = LinkBudgetChannel()

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


def test_link_budget_channel_is_deterministic_for_seeded_links():
    channel = LinkBudgetChannel()
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


def test_link_budget_channel_defaults_to_no_active_link_mutation():
    net = build_channel_network()
    channel = LinkBudgetChannel()

    evaluation = channel.evaluate(net, "ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    assert net.active_links == {}
    assert net.last_connect_result["metrics"]["snr_dB"] == pytest.approx(evaluation.snr_dB)


def test_link_budget_channel_can_preserve_legacy_active_link_mutation():
    net = build_channel_network()
    channel = LinkBudgetChannel(store_in_active_links=True)

    evaluation = channel.evaluate(net, "ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    link_key = "ap1→ris1→ue1 (Connect)"
    assert link_key in net.active_links
    assert net.active_links[link_key]["snr_dB"] == pytest.approx(evaluation.snr_dB)


def test_link_budget_channel_propagates_missing_node_errors():
    channel = LinkBudgetChannel()

    with pytest.raises(ValueError) as exc_info:
        channel.evaluate(build_channel_network(), "missing-ap", "ris1", "ue1")

    assert "Invalid node name" in str(exc_info.value)
    assert "AP 'missing-ap'" in str(exc_info.value)


def test_link_budget_channel_propagates_fov_rejections():
    channel = LinkBudgetChannel()

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


def test_link_budget_channel_reproduces_current_connect_for_environment_blocked_paths():
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
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )
    evaluation = LinkBudgetChannel().evaluate(
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
