"""Regression tests grounded in Burtakov et al. (IEEE Access 2023).

"QRIS: A QuaDRiGa-Based Simulation Platform for Reconfigurable Intelligent
Surfaces," IEEE Access, vol. 11, 2023.

These tests exercise the analytical properties and monotonicity claims that
QRIS validates against SimRIS (Sec. V-C-1 and Figs. 8–9).  They are written
against the Waveflow SimRIS LOS engine (evaluate_simris_los_reference) because
that engine implements the same 3GPP 38.901 indoor/outdoor channel model that
QRIS extends.  The GSCM engine (Phase 7b) should satisfy the same guarantees
once implemented — these tests are therefore forward-compatible regression
anchors.

Coverage:

  1. COS-UC radiation pattern  G_e(θ) = 2(2q+1)·sin²q(θ)  (Eq. 3, q≈0.285)
     — exact value at broadside (θ=0) equals π, near-zero at end-fire (θ=90°),
       monotonically decreasing, hemisphere integral ≈ 4π.

  2. N² channel gain scaling  (QRIS Sec. IV, path loss ∝ d_TI²·d_IR²)
     — doubling RIS side length (8→16, 16→32) raises gain by ≈12 dB.

  3. Frequency ordering: 73 GHz path gain < 28 GHz path gain (indoor),
     5.3 GHz path gain < 3.7 GHz path gain (outdoor UMi).

  4. RIS position sweet-spot (Fig. 8 / Fig. 9): channel gain peaks when RIS
     is near one end (Tx-side or Rx-side) rather than far from both, consistent
     with the d_TI²·d_IR² denominator structure.

  5. Indoor vs outdoor comparison: same geometry and frequency, indoor gain
     must exceed outdoor gain (higher path exponent in UMi).

  6. Frozen numerical regression: pins exact SimRIS LOS engine outputs for the
     QRIS Fig. 8 Indoor geometry and Fig. 9 UMi geometry at the reference seed.

All values captured 2026-05-08 against risnet/channels/simris.py.

Note: The QRIS paper uses COS-UC with q≈0.285; the Waveflow SimRIS engine
uses _ris_pattern_linear which implements the same G_e formula.  The GSCM
engine (future Phase 7b) must pass these same tests once integrated.
"""

import math

import numpy as np
import pytest

import risnet.channels.simris as _simris


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _los_channel_gain(tx, ris, rx, *, N_side, freq_GHz, env="indoor"):
    """Evaluate deterministic LOS channel gain (no direct path, no stochastic)."""
    return _simris.evaluate_simris_los_reference(
        tx_xyz=tx,
        ris_xyz=ris,
        rx_xyz=rx,
        ris_side=N_side,
        frequency_GHz=freq_GHz,
        environment=env,
        include_direct_path=False,
    )["channel_gain_dB"]


# ---------------------------------------------------------------------------
# 1. COS-UC element radiation pattern  (QRIS Eq. 3 / Sec. IV-A)
# ---------------------------------------------------------------------------

class TestCOSUCRadiationPattern:
    """G_e(θ) = 2(2q+1)·sin²q(θ), q ≈ 0.285.
    Waveflow uses the SimRIS half-wave-dipole-like element pattern which
    implements the same functional form.
    """

    def test_broadside_equals_pi(self):
        """G_e(0°) = π exactly (q≈0.285 normalisation, QRIS Eq. 3)."""
        assert _simris._ris_pattern_linear(0.0) == pytest.approx(math.pi, rel=1e-6)

    def test_endfire_is_near_zero(self):
        """G_e(90°) → 0 (end-fire direction has negligible gain)."""
        assert _simris._ris_pattern_linear(90.0) < 1e-6

    def test_monotonically_decreasing_0_to_90(self):
        """Gain must decrease strictly from broadside to end-fire."""
        angles = [0, 15, 30, 45, 60, 75, 90]
        gains = [_simris._ris_pattern_linear(a) for a in angles]
        assert gains == sorted(gains, reverse=True)

    def test_always_non_negative(self):
        """Radiation pattern is a power quantity — never negative."""
        for theta in range(0, 91, 5):
            assert _simris._ris_pattern_linear(float(theta)) >= 0.0

    def test_hemisphere_integral_close_to_4pi(self):
        """Integral of G_e over upper hemisphere ≈ 4π (energy conservation)."""
        thetas = np.linspace(0, math.pi / 2, 500)
        integrand = np.array([_simris._ris_pattern_linear(math.degrees(t)) for t in thetas])
        # ∫ G_e(θ) sin(θ) dθ dφ  over 2π azimuth and [0, π/2] elevation
        integral = 2 * math.pi * np.trapz(integrand * np.sin(thetas), thetas)
        assert integral == pytest.approx(4 * math.pi, rel=0.15)

    def test_45deg_gain_between_broadside_and_endfire(self):
        """G_e(45°) must be strictly between G_e(0°) and G_e(90°)."""
        g0 = _simris._ris_pattern_linear(0.0)
        g45 = _simris._ris_pattern_linear(45.0)
        g90 = _simris._ris_pattern_linear(90.0)
        assert g90 < g45 < g0


# ---------------------------------------------------------------------------
# 2. N² gain scaling  (QRIS Sec. IV — path loss ∝ d_TI² · d_IR²)
# ---------------------------------------------------------------------------

class TestNSquaredGainScaling:
    """Doubling the RIS side length (N → 4N elements) must raise channel
    gain by ≈12 dB because gain scales as N² (QRIS, path-loss model)."""

    _TX = (0.0, 0.0, 3.0)
    _RIS = (5.0, 5.0, 3.0)
    _RX = (20.0, 0.0, 2.0)
    _FREQ = 28.0

    def test_doubling_side_8_to_16_gives_12dB(self):
        g8 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=8, freq_GHz=self._FREQ)
        g16 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=16, freq_GHz=self._FREQ)
        assert g16 - g8 == pytest.approx(12.0, abs=0.5)

    def test_doubling_side_16_to_32_gives_12dB(self):
        g16 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=16, freq_GHz=self._FREQ)
        g32 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=32, freq_GHz=self._FREQ)
        assert g32 - g16 == pytest.approx(12.0, abs=0.5)

    def test_larger_ris_always_better(self):
        gains = [
            _los_channel_gain(self._TX, self._RIS, self._RX, N_side=n, freq_GHz=self._FREQ)
            for n in (4, 8, 16, 32)
        ]
        assert gains == sorted(gains)

    def test_n_squared_ratio_matches_element_count_ratio(self):
        """Gain ratio (dB) must equal 10·log10((N2/N1)²)."""
        n1, n2 = 8, 16
        g1 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=n1, freq_GHz=self._FREQ)
        g2 = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=n2, freq_GHz=self._FREQ)
        expected_dB = 20.0 * math.log10(n2 / n1)  # 20·log10(2) ≈ 6.02... wait N elems=(n²)
        # N_side doubles → N_elements quadruples → gain ∝ N² = 4× per doubling of side
        expected_dB = 10.0 * math.log10((n2 ** 2 / n1 ** 2) ** 2)  # ≈ 12.04 dB
        assert g2 - g1 == pytest.approx(expected_dB, abs=0.5)


# ---------------------------------------------------------------------------
# 3. Frequency ordering  (QRIS Figs. 8 and 9)
# ---------------------------------------------------------------------------

class TestFrequencyOrdering:
    """Higher frequency → more path loss → lower channel gain.
    QRIS Fig. 8: 73 GHz curves lie below 28 GHz for same indoor geometry.
    QRIS Fig. 9: 5.3 GHz curves lie below 3.7 GHz for same UMi geometry.
    """

    _TX_IN = (0.0, 0.0, 3.0)
    _RIS_IN = (5.0, 5.0, 3.0)
    _RX_IN = (20.0, 0.0, 2.0)

    _TX_OUT = (0.0, 0.0, 3.0)
    _RIS_OUT = (25.0, 15.0, 3.0)
    _RX_OUT = (50.0, 0.0, 2.0)

    def test_indoor_73ghz_worse_than_28ghz(self):
        g28 = _los_channel_gain(self._TX_IN, self._RIS_IN, self._RX_IN, N_side=16, freq_GHz=28.0)
        g73 = _los_channel_gain(self._TX_IN, self._RIS_IN, self._RX_IN, N_side=16, freq_GHz=73.0)
        assert g73 < g28

    def test_outdoor_5p3ghz_worse_than_3p7ghz(self):
        g37 = _los_channel_gain(self._TX_OUT, self._RIS_OUT, self._RX_OUT, N_side=8, freq_GHz=3.7, env="outdoor")
        g53 = _los_channel_gain(self._TX_OUT, self._RIS_OUT, self._RX_OUT, N_side=8, freq_GHz=5.3, env="outdoor")
        assert g53 < g37

    def test_indoor_frequency_monotone(self):
        freqs = [5.0, 10.0, 28.0, 60.0, 73.0]
        gains = [_los_channel_gain(self._TX_IN, self._RIS_IN, self._RX_IN, N_side=16, freq_GHz=f) for f in freqs]
        assert gains == sorted(gains, reverse=True)


# ---------------------------------------------------------------------------
# 4. RIS position sweet-spot  (QRIS Figs. 8 / 9, d_TI²·d_IR² denominator)
# ---------------------------------------------------------------------------

class TestRISPositionSweetSpot:
    """Path loss ∝ d_TI² · d_IR².  The minimum (best SNR) is achieved when
    the RIS is near either the Tx or the Rx, not equidistant from both.
    QRIS Fig. 8 shows peak SNR at x_RIS → 0 (near Tx) and x_RIS → 20 (near Rx).
    """

    _TX = (0.0, 0.0, 3.0)
    _RX = (20.0, 0.0, 2.0)
    _Y = 5.0
    _Z = 3.0
    _N = 16
    _FREQ = 28.0

    def _gain(self, x):
        return _los_channel_gain(
            self._TX, (x, self._Y, self._Z), self._RX,
            N_side=self._N, freq_GHz=self._FREQ,
        )

    def test_near_tx_better_than_midpoint(self):
        """x_RIS=1 (near Tx) should have higher gain than x_RIS=10 (midpoint)."""
        assert self._gain(1.0) > self._gain(10.0)

    def test_near_rx_better_than_midpoint(self):
        """x_RIS=19 (near Rx) should have higher gain than x_RIS=10 (midpoint)."""
        assert self._gain(19.0) > self._gain(10.0)

    def test_gain_is_symmetric_at_tx_and_rx_ends(self):
        """Gain at x=1 (near Tx) and x=19 (near Rx) should be similar (≤3 dB apart)."""
        diff = abs(self._gain(1.0) - self._gain(19.0))
        assert diff < 3.0

    def test_midpoint_is_local_minimum(self):
        """x=10 must be worse than both x=5 and x=15."""
        assert self._gain(5.0) > self._gain(10.0)
        assert self._gain(15.0) > self._gain(10.0)


# ---------------------------------------------------------------------------
# 5. Indoor vs outdoor  (same geometry and frequency)
# ---------------------------------------------------------------------------

class TestIndoorOutdoorComparison:
    """Indoor InH-Office has a shorter path-loss exponent than UMi outdoor
    at the same short distances → indoor channel gain should be higher.
    """

    _TX = (0.0, 0.0, 3.0)
    _RIS = (5.0, 5.0, 3.0)
    _RX = (20.0, 0.0, 2.0)
    _N = 8
    _FREQ = 5.3

    def test_indoor_gain_exceeds_outdoor_at_same_geometry(self):
        g_in = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=self._N, freq_GHz=self._FREQ, env="indoor")
        g_out = _los_channel_gain(self._TX, self._RIS, self._RX, N_side=self._N, freq_GHz=self._FREQ, env="outdoor")
        assert g_in > g_out


# ---------------------------------------------------------------------------
# 6. Frozen numerical regression  (pins exact values, captured 2026-05-08)
# ---------------------------------------------------------------------------

class TestFrozenNumericalRegression:
    """Exact values from risnet/channels/simris.py, captured 2026-05-08.
    Any silent change to path-loss parameters, element pattern, or array
    response formulas will break these tests immediately.
    """

    def test_cos_uc_broadside_is_pi(self):
        assert _simris._ris_pattern_linear(0.0) == pytest.approx(math.pi, rel=1e-9)

    def test_cos_uc_45deg(self):
        assert _simris._ris_pattern_linear(45.0) == pytest.approx(2.578, abs=0.001)

    def test_n_squared_diff_8_to_16_indoor_28ghz(self):
        """Pins the exact 12.041 dB N² scaling increment."""
        g8 = _los_channel_gain((0,0,3), (5,5,3), (20,0,2), N_side=8, freq_GHz=28.0)
        g16 = _los_channel_gain((0,0,3), (5,5,3), (20,0,2), N_side=16, freq_GHz=28.0)
        assert g16 - g8 == pytest.approx(12.041, abs=0.005)

    def test_indoor_28ghz_channel_gain_n16(self):
        """Indoor, 28 GHz, N_side=16, Tx=(0,0,3), RIS=(5,5,3), Rx=(20,0,2)."""
        g = _los_channel_gain((0,0,3), (5,5,3), (20,0,2), N_side=16, freq_GHz=28.0)
        assert g == pytest.approx(-100.12, abs=0.05)

    def test_indoor_73ghz_channel_gain_n16(self):
        """Indoor, 73 GHz — higher loss than 28 GHz by ~16.6 dB."""
        g = _los_channel_gain((0,0,3), (5,5,3), (20,0,2), N_side=16, freq_GHz=73.0)
        assert g == pytest.approx(-116.77, abs=0.05)

    def test_outdoor_3p7ghz_channel_gain_n8(self):
        """UMi outdoor, 3.7 GHz, N_side=8, QRIS Fig. 9 reference geometry."""
        g = _los_channel_gain((0,0,3), (25,15,3), (50,0,2), N_side=8, freq_GHz=3.7, env="outdoor")
        assert g == pytest.approx(-99.55, abs=0.05)

    def test_outdoor_5p3ghz_channel_gain_n8(self):
        """UMi outdoor, 5.3 GHz, N_side=8."""
        g = _los_channel_gain((0,0,3), (25,15,3), (50,0,2), N_side=8, freq_GHz=5.3, env="outdoor")
        assert g == pytest.approx(-105.80, abs=0.05)
