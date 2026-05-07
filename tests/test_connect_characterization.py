"""Characterization tests for RISNetwork.connect public behavior."""

import math

import numpy as np
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


def test_resolve_connect_geometry_reports_default_target_alignment():
    net = build_line_network()
    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")

    geometry = net._resolve_connect_geometry(ap, ris, ue)

    assert geometry["beam_angle_deg"] == pytest.approx(0.0)
    assert geometry["beam_angle_requested_deg"] == pytest.approx(0.0)
    assert geometry["target_angle"] == pytest.approx(0.0)
    assert geometry["beam_hits_ue"] is True


def test_resolve_connect_geometry_marks_missed_beam_as_absent():
    net = build_line_network()
    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")

    geometry = net._resolve_connect_geometry(ap, ris, ue, beam_angle_deg=90.0)

    assert geometry["beam_angle_requested_deg"] == pytest.approx(90.0)
    assert geometry["beam_hits_ue"] is False


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


def test_connect_geometry_metadata_matches_coordinate_math_for_non_collinear_layout():
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap1", 23.09, 26.40, 0.0)
    net.add_ris("ris1", 14.59, 14.47, 0.0, max_angle_deg=60)
    net.add_ue("ue1", 21.34, 15.22, 0.0)

    result = net.connect("ap1", "ris1", "ue1", use_get_snr=False)

    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    expected_ap_ris = float(np.linalg.norm(ris.pos - ap.pos))
    expected_ris_ue = float(np.linalg.norm(ue.pos - ris.pos))
    expected_incident = math.degrees(math.atan2(ap.pos[1] - ris.pos[1], ap.pos[0] - ris.pos[0]))
    expected_reflected = math.degrees(math.atan2(ue.pos[1] - ris.pos[1], ue.pos[0] - ris.pos[0]))
    expected_angle_diff = expected_reflected - expected_incident
    while expected_angle_diff > 180:
        expected_angle_diff -= 360
    while expected_angle_diff < -180:
        expected_angle_diff += 360

    assert expected_ap_ris == pytest.approx(14.6483753365, rel=0, abs=1e-9)
    assert expected_ris_ue == pytest.approx(6.7915388536, rel=0, abs=1e-9)
    assert result["incident_azimuth_deg"] == pytest.approx(expected_incident)
    assert result["reflected_azimuth_deg"] == pytest.approx(expected_reflected)
    assert result["beam_angle"] == pytest.approx(expected_reflected)
    assert result["beam_angle_requested_deg"] == pytest.approx(expected_reflected)
    assert result["target_angle_deg"] == pytest.approx(expected_reflected)
    assert result["local_deflection_deg"] == pytest.approx(expected_reflected)
    assert abs(result["deflection_angle_deg"]) == pytest.approx(abs(expected_angle_diff))
    assert result["angle_diff_deg"] == pytest.approx(expected_angle_diff)


def test_compute_connect_phases_returns_metadata_only_when_enabled():
    net = build_line_network()
    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")

    phase_metadata = net._compute_connect_phases(ap, ris.clone(), ue.clone(), 0.0, compute_phases=True)
    no_phase_metadata = net._compute_connect_phases(ap, ris.clone(), ue.clone(), 0.0, compute_phases=False)

    assert "deflection_angle_deg" in phase_metadata
    assert no_phase_metadata == {}


def test_collect_connect_phase_data_copies_phase_state_to_canonical_ris_node():
    net = build_line_network()
    ap, ris_node, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")
    ris = ris_node.clone()

    net._compute_connect_phases(ap, ris, ue.clone(), 0.0, compute_phases=True)
    phase_data = net._collect_connect_phase_data(ris, ris_node, 0.0, compute_phases=True)

    assert phase_data["current_phases"]
    assert ris_node.current_phases is not None
    assert ris_node.quantized_phases is not None
    assert ris_node.phase_states is not None
    assert ris_node.current_beam_angle == pytest.approx(0.0)
    assert ris_node.phase_metadata == ris.phase_metadata


def test_build_connect_result_preserves_phase_payload_and_absence_flags():
    net = build_line_network()

    result = net._build_connect_result(
        snr_dB=12.5,
        pwr_dBm=-48.0,
        gain_linear=3.2,
        gain_dBi=5.0,
        quant_loss_dB=-0.2,
        beam_angle_deg=10.0,
        beam_angle_requested_deg=15.0,
        ris_normal=0.0,
        local_deflection=10.0,
        target_angle=12.0,
        beam_hits_ue=False,
        phase_data={"current_phases": [0.0, 1.0]},
        rssi_dBm=-50.0,
    )

    assert result["current_phases"] == [0.0, 1.0]
    assert result["ue_present"] is False
    assert result["no_ue_detected"] is True
    assert result["beam_angle_requested_deg"] == pytest.approx(15.0)


def test_persist_connect_feedback_measurement_updates_canonical_ue():
    net = build_line_network()
    ue = net.get("ue1")

    net._persist_connect_feedback_measurement(
        {"feedback_info": {"final_snr_dB": 17.25}},
        "ue1",
    )

    assert ue.snr_measurement_dB == pytest.approx(17.25)


def test_persist_connect_metadata_stores_link_snapshot_on_canonical_ue():
    net = build_line_network()
    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")

    net._persist_connect_metadata(
        ue,
        ap_key="ap1",
        ris_key="ris1",
        ue_key="ue1",
        ap=ap,
        total_loss_dB=80.0,
        total_gain_dBi=25.0,
        bandwidth_MHz=20.0,
        noise_figure_dB=6.0,
        beam_angle_deg=0.0,
        beam_angle_requested_deg=0.0,
        target_angle=0.0,
        quant_loss_dB=-0.1,
        gain_dBi=19.0,
        ap_antenna_gain_dBi=3.0,
        ue_antenna_gain_dBi=3.0,
        pwr_dBm=-49.0,
        beam_hits_ue=True,
        snr_computed_dB=21.0,
    )

    stored = ue.get_link_metadata("ap1", "ris1")
    assert ue.snr_measurement_dB == pytest.approx(21.0)
    assert stored["ap_name"] == "ap1"
    assert stored["ris_name"] == "ris1"
    assert stored["bandwidth_MHz"] == pytest.approx(20.0)
    assert stored["ue_present"] is True


def test_resolve_connect_reported_snr_uses_messaging_override_when_available():
    net = build_line_network(enable_messaging=False)

    class StubMessaging:
        def get_snr(self, ue_name, ris_name, ap_name=None):
            assert ue_name == "ue1"
            assert ris_name == "ris1"
            assert ap_name == "ap1"
            return 33.0

    net.snr_messaging = StubMessaging()

    reported = net._resolve_connect_reported_snr(
        use_get_snr=True,
        ue_key="ue1",
        ris_key="ris1",
        ap_key="ap1",
        snr_computed_dB=12.0,
    )

    assert reported == pytest.approx(33.0)


def test_resolve_connect_reported_snr_falls_back_to_computed_value_when_query_missing():
    net = build_line_network(enable_messaging=False)

    class StubMessaging:
        def get_snr(self, ue_name, ris_name, ap_name=None):
            return None

    net.snr_messaging = StubMessaging()

    reported = net._resolve_connect_reported_snr(
        use_get_snr=True,
        ue_key="ue1",
        ris_key="ris1",
        ap_key="ap1",
        snr_computed_dB=12.0,
    )

    assert reported == pytest.approx(12.0)


def test_store_connect_active_link_records_snapshot_with_phase_angles():
    net = build_line_network()

    result = {
        "snr_dB": 18.0,
        "pwr_dBm": -45.0,
        "gain_dBi": 12.0,
        "quant_loss_dB": -0.3,
        "deflection_angle_deg": 5.0,
        "current_phases": [0.0],
        "quantized_phases": [0.0],
        "phase_states": [0],
        "incident_azimuth_deg": 180.0,
        "reflected_azimuth_deg": 0.0,
    }

    net._store_connect_active_link(
        store_in_active_links=True,
        ap_key="ap1",
        ris_key="ris1",
        ue_key="ue1",
        result=result,
        local_deflection=5.0,
        beam_angle_deg=0.0,
        ris_normal=0.0,
    )

    active = net.active_links["ap1→ris1→ue1 (Connect)"]
    assert active["source"] == "connect"
    assert active["beam_angle_local"] == pytest.approx(5.0)
    assert active["beam_angle_absolute"] == pytest.approx(0.0)
    assert active["current_phases"] == [0.0]


def test_store_last_connect_result_captures_parameter_snapshot():
    net = build_line_network()

    net._store_last_connect_result(
        ap_key="ap1",
        ris_key="ris1",
        ue_key="ue1",
        beam_angle_deg=10.0,
        compute_phases=True,
        bandwidth_MHz=40.0,
        seed=7,
        enable_feedback=True,
        max_feedback_iterations=4,
        result={"snr_dB": 19.0},
    )

    assert net.last_connect_result["ap"] == "ap1"
    assert net.last_connect_result["parameters"]["beam_angle_deg"] == pytest.approx(10.0)
    assert net.last_connect_result["parameters"]["bandwidth_MHz"] == pytest.approx(40.0)
    assert net.last_connect_result["parameters"]["enable_feedback"] is True
    assert net.last_connect_result["metrics"]["snr_dB"] == pytest.approx(19.0)


def test_prepare_connect_link_budget_applies_impairments_and_phase_metadata():
    net = build_line_network()
    net.set_impairments({"extra_path_loss_dB_ris": 7.5})
    ap, ris, ue = net._resolve_connect_nodes("ap1", "ris1", "ue1")
    ris = ris.clone()

    budget = net._prepare_connect_link_budget(
        ap,
        ris,
        ue,
        d_ap_ris=5.0,
        d_ris_ue=5.0,
        beam_angle_deg=0.0,
        target_angle=0.0,
        phase_metadata={"deflection_angle_deg": 4.0},
        bandwidth_MHz=20.0,
    )

    assert budget["bandwidth_MHz"] == pytest.approx(20.0)
    assert budget["total_loss_dB"] > 0.0
    assert ris.local_beam_deflection_deg == pytest.approx(4.0)
    assert budget["pwr_dBm"] < 0.0


def test_compute_connect_snr_uses_array_factor_adjustment_when_phase_metadata_exists():
    net = build_line_network()
    ap, ris, _ = net._resolve_connect_nodes("ap1", "ris1", "ue1")
    ris = ris.clone()
    ris.current_phases = np.zeros(ris.N * ris.N)
    ris.phase_metadata = {"azimuth_out_deg": 30.0}

    with_af = net._compute_connect_snr(
        ap,
        ris,
        bandwidth_MHz=20.0,
        noise_figure_dB=6.0,
        total_loss_dB=80.0,
        total_gain_dBi=25.0,
        target_angle=0.0,
        seed=42,
    )

    ris.phase_metadata = {}
    without_af = net._compute_connect_snr(
        ap,
        ris,
        bandwidth_MHz=20.0,
        noise_figure_dB=6.0,
        total_loss_dB=80.0,
        total_gain_dBi=25.0,
        target_angle=0.0,
        seed=42,
    )

    assert with_af["gain_dBi"] < without_af["gain_dBi"]
    assert with_af["snr_dB"] < without_af["snr_dB"]
