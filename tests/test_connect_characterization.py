"""Characterization tests for RISNetwork.connect public behavior."""

import pytest

from core import RISNetwork


def build_line_network(*, enable_messaging=False, max_angle_deg=180):
    net = RISNetwork(enable_messaging=enable_messaging)
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 5, 0, max_angle_deg=max_angle_deg)
    net.add_ue("ue1", 10, 0)
    return net


def test_connect_returns_current_public_result_shape():
    net = build_line_network()

    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    expected_keys = {
        "snr_dB",
        "pwr_dBm",
        "rssi_dBm",
        "gain_linear",
        "gain_dBi",
        "quant_loss_dB",
        "beam_angle",
        "beam_angle_requested_deg",
        "evm_percent",
        "ris_normal_angle_deg",
        "local_deflection_deg",
        "target_angle_deg",
        "ue_present",
        "no_ue_detected",
        "current_phases",
        "quantized_phases",
        "phase_states",
        "phase_grid",
        "deflection_angle_deg",
        "deflection_angle_clamped_deg",
        "fov_clamped",
        "incident_azimuth_deg",
        "reflected_azimuth_deg",
        "angle_diff_deg",
        "source_height_m",
    }

    assert expected_keys.issubset(result)
    assert isinstance(result["snr_dB"], float)
    assert isinstance(result["pwr_dBm"], float)
    assert result["ue_present"] is True
    assert result["no_ue_detected"] is False


def test_seeded_connect_is_deterministic():
    net_a = build_line_network()
    net_b = build_line_network()

    result_a = net_a.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)
    result_b = net_b.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    for key in ("snr_dB", "pwr_dBm", "gain_dBi", "quant_loss_dB", "beam_angle"):
        assert result_a[key] == pytest.approx(result_b[key])


def test_connect_updates_active_links_and_last_result_by_default():
    net = build_line_network()

    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    link_key = "ap1→ris1→ue1 (Connect)"
    assert link_key in net.active_links

    active = net.active_links[link_key]
    assert active["ap"] == "ap1"
    assert active["ris"] == "ris1"
    assert active["ue"] == "ue1"
    assert active["source"] == "connect"
    assert active["snr_dB"] == pytest.approx(result["snr_dB"])
    assert active["pwr_dBm"] == pytest.approx(result["pwr_dBm"])

    assert net.last_connect_result["ap"] == "ap1"
    assert net.last_connect_result["ris"] == "ris1"
    assert net.last_connect_result["ue"] == "ue1"
    assert net.last_connect_result["parameters"]["seed"] == 42
    assert net.last_connect_result["metrics"]["snr_dB"] == pytest.approx(result["snr_dB"])
    assert net.last_connect_result["captured_at"].endswith("Z")


def test_store_in_active_links_false_skips_link_mutation_but_keeps_last_result():
    net = build_line_network()

    result = net.connect(
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
        store_in_active_links=False,
    )

    assert net.active_links == {}
    assert net.last_connect_result["metrics"]["snr_dB"] == pytest.approx(result["snr_dB"])


def test_compute_phases_persists_phase_data_to_canonical_ris_node():
    net = build_line_network()
    ris = net.get("ris1")

    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    assert result["current_phases"]
    assert result["quantized_phases"]
    assert result["phase_states"]
    assert ris.current_phases is not None
    assert ris.quantized_phases is not None
    assert ris.phase_states is not None
    assert len(ris.current_phases) == ris.N * ris.N
    assert len(ris.quantized_phases) == ris.N * ris.N
    assert len(ris.phase_states) == ris.N * ris.N


def test_compute_phases_false_returns_metrics_without_phase_payload():
    net = build_line_network()

    result = net.connect(
        "ap1",
        "ris1",
        "ue1",
        seed=42,
        use_get_snr=False,
        compute_phases=False,
    )

    assert "snr_dB" in result
    assert "pwr_dBm" in result
    assert "current_phases" not in result
    assert "quantized_phases" not in result
    assert "phase_states" not in result


def test_missing_node_error_lists_missing_and_available_names():
    net = build_line_network()

    with pytest.raises(ValueError) as exc_info:
        net.connect("missing-ap", "ris1", "ue1")

    message = str(exc_info.value)
    assert "Invalid node name" in message
    assert "AP 'missing-ap'" in message
    assert "Available nodes: ap1, ris1, ue1" in message


def test_resolve_connect_nodes_returns_canonical_nodes():
    net = build_line_network()

    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")

    assert ap is net.get("ap1")
    assert ris is net.get("ris1")
    assert ue is net.get("ue1")


def test_resolve_connect_nodes_uses_current_missing_node_error():
    net = build_line_network()

    with pytest.raises(ValueError) as exc_info:
        net._resolve_connect_nodes("missing-ap", "missing-ris", "ue1")

    message = str(exc_info.value)
    assert "Invalid node name" in message
    assert "AP 'missing-ap'" in message
    assert "RIS 'missing-ris'" in message
    assert "Available nodes: ap1, ris1, ue1" in message


def test_fov_rejects_opposite_direction_line_with_default_ris_fov():
    net = build_line_network(max_angle_deg=60)

    with pytest.raises(ValueError) as exc_info:
        net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    message = str(exc_info.value)
    assert "AP outside RIS FOV" in message
    assert "RIS FOV is ±60" in message


def test_beam_that_misses_ue_reports_absence_with_directional_loss_snr():
    net = build_line_network()

    aligned = net.connect(
        "ap1",
        "ris1",
        "ue1",
        beam_angle_deg=0,
        seed=42,
        use_get_snr=False,
    )
    result = net.connect(
        "ap1",
        "ris1",
        "ue1",
        beam_angle_deg=90,
        seed=42,
        use_get_snr=False,
    )

    assert result["ue_present"] is False
    assert result["no_ue_detected"] is True
    assert result["snr_dB"] < aligned["snr_dB"]
