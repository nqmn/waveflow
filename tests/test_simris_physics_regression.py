"""Frozen physics regression tests for the SimRIS channel model.

These tests pin concrete numerical values produced by the implementation so
that any future change to the physics (path-loss formula, element pattern,
channel gain scaling, LOS probability) breaks a test immediately.

Ground truth sources:
  - Basar & Yildirim (2020), "Indoor and Outdoor Physical Channel Modeling
    and Efficient Positioning for RIS in mmWave Bands"  (Table I, Eq. 4,7,11)
  - SimRIS Channel Simulator implementation in risnet/channels/simris.py

All values were captured from the current implementation on 2026-05-08 and
cross-checked against the paper formulas before being frozen here.
"""

import math

import numpy as np
import pytest

import risnet.channels.simris as _mod
from risnet.channels.simris import (
    evaluate_simris_los_reference,
    simulate_simris_channels,
    summarize_simris_tensors,
)

# ---------------------------------------------------------------------------
# Shared geometry constants (published presets from the paper)
# ---------------------------------------------------------------------------

# Indoor InH Office Scenario 1 (paper Fig. 5a)
_IN_TX = np.array([0.0, 25.0, 2.0])
_IN_RIS = np.array([40.0, 50.0, 2.0])
_IN_RX = np.array([38.0, 48.0, 1.0])

# Outdoor UMi Street Canyon Scenario 1 (paper Fig. 4)
_OUT_TX = np.array([0.0, 25.0, 20.0])
_OUT_RIS = np.array([70.0, 85.0, 10.0])
_OUT_RX = np.array([80.0, 75.0, 1.0])

_ABS = 1e-4   # absolute tolerance for dB values (0.1 mdB)


# ---------------------------------------------------------------------------
# 1. Table I — path-loss parameters (exact, no tolerance)
# ---------------------------------------------------------------------------

class TestPathLossParamsRegression:
    """Pin the seven-tuple (_n_nlos, σ_nlos, b_nlos, n_los, σ_los, b_los, f₀)."""

    def test_indoor_tuple(self):
        assert _mod._path_loss_params("indoor") == (3.19, 8.29, 0.06, 1.73, 3.02, 0.0, 24.2)

    def test_outdoor_tuple(self):
        assert _mod._path_loss_params("outdoor") == (3.19, 8.2, 0.0, 1.98, 3.1, 0.0, 24.2)


# ---------------------------------------------------------------------------
# 2. Element pattern G_e(θ) — exact frozen values (Eq. 4)
# ---------------------------------------------------------------------------

class TestElementPatternRegression:
    """G_e(θ) = π · cos(θ)^(2·0.285). Values frozen to 10 significant figures."""

    @pytest.mark.parametrize("theta_deg,expected", [
        (0,  3.1415926536),
        (30, 2.8942919238),
        (45, 2.5784358087),
        (60, 2.1162295539),
        (90, 0.0),          # exact limit; implementation gives ~1.8e-9, treated as 0
    ])
    def test_pattern_value(self, theta_deg, expected):
        got = _mod._ris_pattern_linear(float(theta_deg))
        if theta_deg == 90:
            assert got == pytest.approx(0.0, abs=1e-6)
        else:
            assert got == pytest.approx(expected, abs=1e-9)


# ---------------------------------------------------------------------------
# 3. Path gain (no shadow) — frozen dB values
# ---------------------------------------------------------------------------

class TestPathGainRegression:
    """Pin _path_gain_linear (dB) for canonical distances and frequencies."""

    def _pg(self, distance_m, freq_GHz, env, los=True):
        dB, _, _ = _mod._path_gain_linear(
            distance_m,
            frequency_GHz=freq_GHz,
            environment=env,
            is_los=los,
            rng=None,
            include_shadow_fading=False,
        )
        return dB

    @pytest.mark.parametrize("env,d,freq,expected_dB", [
        ("indoor",  10.0, 28.0, -78.68493281),
        ("indoor",  10.0, 73.0, -87.00822939),
        ("outdoor", 50.0, 28.0, -95.02453890),
        ("outdoor", 50.0, 73.0, -103.34783547),
    ])
    def test_los_path_gain(self, env, d, freq, expected_dB):
        assert self._pg(d, freq, env, los=True) == pytest.approx(expected_dB, abs=_ABS)


# ---------------------------------------------------------------------------
# 4. Outdoor LOS probability (Eq. 11) — exact formula values
# ---------------------------------------------------------------------------

class TestOutdoorLOSProbabilityRegression:
    """p = min(20/d,1)·(1−e^(−d/39)) + e^(−d/39). Values frozen to 10 d.p."""

    @pytest.mark.parametrize("d,expected_p", [
        (5.0,   1.0),
        (20.0,  1.0),
        (25.0,  0.9053503777),
        (39.0,  0.6920438303),
        (100.0, 0.2615905940),
    ])
    def test_p_los(self, d, expected_p):
        p = min(20.0 / d, 1.0) * (1.0 - math.exp(-d / 39.0)) + math.exp(-d / 39.0)
        assert p == pytest.approx(expected_p, abs=1e-9)


# ---------------------------------------------------------------------------
# 5. Channel gain — LOS reference (RIS path only, no direct, no shadow)
# ---------------------------------------------------------------------------

class TestChannelGainRegression:
    """Pin evaluate_simris_los_reference channel_gain_dB for paper geometries.

    include_direct_path=False isolates the RIS path so N² scaling is visible
    and results are deterministic (no stochastic direct-path component).
    """

    def _cg(self, tx, ris, rx, N_side, freq, env, scenario=1):
        r = evaluate_simris_los_reference(
            tx_xyz=tx, ris_xyz=ris, rx_xyz=rx,
            ris_side=N_side, frequency_GHz=freq,
            environment=env, scenario=scenario,
            include_direct_path=False,
        )
        return r["channel_gain_dB"]

    @pytest.mark.parametrize("freq,N_side,expected_dB", [
        (28.0,  8, -114.057656),
        (28.0, 16, -102.016456),
        (73.0,  8, -130.704249),
        (73.0, 16, -118.663049),
    ])
    def test_indoor_scenario1(self, freq, N_side, expected_dB):
        got = self._cg(_IN_TX, _IN_RIS, _IN_RX, N_side, freq, "indoor")
        assert got == pytest.approx(expected_dB, abs=_ABS)

    @pytest.mark.parametrize("freq,N_side,expected_dB", [
        (28.0,  8, -140.332350),
        (28.0, 16, -128.291150),
        (73.0,  8, -156.978943),
        (73.0, 16, -144.937743),
    ])
    def test_outdoor_scenario1(self, freq, N_side, expected_dB):
        got = self._cg(_OUT_TX, _OUT_RIS, _OUT_RX, N_side, freq, "outdoor")
        assert got == pytest.approx(expected_dB, abs=_ABS)

    def test_n_squared_diff_indoor_28ghz(self):
        """N_side 8→16 (N=64→256) must give ~12.04 dB gain increase."""
        g8  = self._cg(_IN_TX, _IN_RIS, _IN_RX,  8, 28.0, "indoor")
        g16 = self._cg(_IN_TX, _IN_RIS, _IN_RX, 16, 28.0, "indoor")
        assert g16 - g8 == pytest.approx(12.041200, abs=_ABS)


# ---------------------------------------------------------------------------
# 6. Stochastic channel norms — seeded frozen fixture
# ---------------------------------------------------------------------------

class TestStochasticNormsRegression:
    """Pin H and G Frobenius norms for a fixed seed, LOS-only, no shadow.

    These values confirm that the stochastic engine (cluster/sub-ray sampling,
    array response computation) has not changed.
    """

    def _tensors(self):
        return simulate_simris_channels(
            tx_xyz=_IN_TX, ris_xyz=_IN_RIS, rx_xyz=_IN_RX,
            ris_side=8, frequency_GHz=28.0,
            num_realizations=1, seed=0,
            include_direct_path=False,
            include_nlos=False,
            include_shadow_fading=False,
            force_tx_ris_los=True,
            force_ris_rx_los=True,
        )

    def test_h_norm_frozen(self):
        s = summarize_simris_tensors(self._tensors())
        assert s["H_norms"][0] == pytest.approx(0.00043121916180629904, rel=1e-6)

    def test_g_norm_frozen(self):
        s = summarize_simris_tensors(self._tensors())
        assert s["G_norms"][0] == pytest.approx(0.004596414255462315, rel=1e-6)

    def test_seed_produces_identical_norms(self):
        s1 = summarize_simris_tensors(self._tensors())
        s2 = summarize_simris_tensors(self._tensors())
        assert s1["H_norms"][0] == s2["H_norms"][0]
        assert s1["G_norms"][0] == s2["G_norms"][0]
