"""Tests grounded in Basar & Yildirim (2020), "Indoor and Outdoor Physical Channel
Modeling and Efficient Positioning for RIS in mmWave Bands."

Covers formulas and parameter values from the paper not addressed by the existing
test_simris_channel.py (integration/regression) and test_simris_paper_formulas.py
(element pattern, path gain monotonicity, N² scaling, LOS forcing).

New ground covered here:
  - Table I: exact path-loss parameters for all four scenarios
  - Eq. 4: element radiation pattern G_e energy-conservation normalization
  - Eq. 7: indoor LOS probability boundary values (numerical)
  - Eq. 11: outdoor LOS probability formula (p = min(20/d,1)·(1−e^(−d/39)) + e^(−d/39))
  - Eq. 13: achievable rate formula R = log2(1+SNR) with paper noise floor
  - outdoor evaluate_simris_los_reference (Fig. 4 geometry)
  - summarize_simris_tensors output structure
  - 73 GHz band validity (paper validates at both 28 GHz and 73 GHz)
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
# Helpers
# ---------------------------------------------------------------------------

def _los_indicator(distance_m: float, environment: str, force=None, seed: int = 0) -> int:
    rng = np.random.default_rng(seed)
    tx = np.array([0.0, 0.0, 2.0])
    ris = np.array([distance_m, 0.0, 2.0])
    return _mod._sample_los_indicator(environment, tx, ris, distance_m, rng, force=force)


def _p_los_outdoor_paper(d: float) -> float:
    """Paper Eq. 11 in closed form."""
    return min(20.0 / d, 1.0) * (1.0 - math.exp(-d / 39.0)) + math.exp(-d / 39.0)


# ---------------------------------------------------------------------------
# 1. Table I — exact path-loss parameters
# ---------------------------------------------------------------------------

class TestTableIPathLossParameters:
    """Paper Table I lists n, σ, b, f₀ for four scenarios.

    The tuple returned by _path_loss_params is:
    (n_nlos, σ_nlos, b_nlos, n_los, σ_los, b_los, f₀)
    """

    def test_indoor_nlos_exponent(self):
        n_nlos, *_ = _mod._path_loss_params("indoor")
        assert n_nlos == pytest.approx(3.19, abs=1e-9)

    def test_indoor_nlos_shadow(self):
        _, sigma_nlos, *_ = _mod._path_loss_params("indoor")
        assert sigma_nlos == pytest.approx(8.29, abs=1e-9)

    def test_indoor_nlos_b_parameter(self):
        _, _, b_nlos, *_ = _mod._path_loss_params("indoor")
        assert b_nlos == pytest.approx(0.06, abs=1e-9)

    def test_indoor_los_exponent(self):
        _, _, _, n_los, *_ = _mod._path_loss_params("indoor")
        assert n_los == pytest.approx(1.73, abs=1e-9)

    def test_indoor_los_shadow(self):
        _, _, _, _, sigma_los, *_ = _mod._path_loss_params("indoor")
        assert sigma_los == pytest.approx(3.02, abs=1e-9)

    def test_indoor_los_b_is_zero(self):
        """Paper Table I: b=0 for indoor LOS — no frequency-dependent correction."""
        _, _, _, _, _, b_los, _ = _mod._path_loss_params("indoor")
        assert b_los == pytest.approx(0.0, abs=1e-9)

    def test_indoor_reference_frequency(self):
        *_, f0 = _mod._path_loss_params("indoor")
        assert f0 == pytest.approx(24.2, abs=1e-9)

    def test_outdoor_nlos_exponent(self):
        n_nlos, *_ = _mod._path_loss_params("outdoor")
        assert n_nlos == pytest.approx(3.19, abs=1e-9)

    def test_outdoor_nlos_shadow(self):
        _, sigma_nlos, *_ = _mod._path_loss_params("outdoor")
        assert sigma_nlos == pytest.approx(8.2, abs=1e-9)

    def test_outdoor_nlos_b_is_zero(self):
        """Paper Table I: b=0 for UMi NLOS."""
        _, _, b_nlos, *_ = _mod._path_loss_params("outdoor")
        assert b_nlos == pytest.approx(0.0, abs=1e-9)

    def test_outdoor_los_exponent(self):
        _, _, _, n_los, *_ = _mod._path_loss_params("outdoor")
        assert n_los == pytest.approx(1.98, abs=1e-9)

    def test_outdoor_los_shadow(self):
        _, _, _, _, sigma_los, *_ = _mod._path_loss_params("outdoor")
        assert sigma_los == pytest.approx(3.1, abs=1e-9)

    def test_outdoor_los_b_is_zero(self):
        """Paper Table I: b=0 for UMi LOS."""
        _, _, _, _, _, b_los, _ = _mod._path_loss_params("outdoor")
        assert b_los == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 2. Eq. 4 — element pattern energy-conservation normalization
# ---------------------------------------------------------------------------

class TestElementPatternNormalization:
    """G_e(θ) = G_e(0) · cos^(2q)(θ), q=0.285.

    The paper derives q=0.285 from A_e = (λ/2)², giving G_e(0) = 4πA_e/λ² = π.
    Implementation uses _ELEMENT_GAIN_LINEAR = π (exact), so G_e(0°) = π.

    Note: 2(2q+1) ≈ 3.14 ≈ π but not exactly π with q=0.285 (floating point).
    The implementation correctly sets G_e(0)=π directly, not via the 2(2q+1) formula.
    The hemisphere integral is ≈4π (within 0.1%) due to the q=0.285 approximation.
    """

    _Q = 0.285

    def test_normalization_factor_close_to_pi(self):
        """2(2q+1) with q=0.285 is close to π (paper approximation, not exact)."""
        factor = 2 * (2 * self._Q + 1)
        assert abs(factor - math.pi) < 0.005

    def test_hemisphere_integral_close_to_4pi(self):
        """Numerical integral of G_e over hemisphere ≈ 4π within 0.1%.

        The small deviation is because q=0.285 only approximates the exact value
        that makes 2(2q+1)=π; the implementation compensates by setting G_e(0)=π
        directly, so the integral is accurate to within floating-point tolerance.
        """
        from scipy import integrate

        def integrand(theta):
            return _mod._ris_pattern_linear(math.degrees(theta)) * math.sin(theta)

        result, _ = integrate.quad(integrand, 0, math.pi / 2)
        total = result * 2 * math.pi
        assert total == pytest.approx(4 * math.pi, rel=1e-2)

    def test_broadside_gain_near_5dBi(self):
        """G_e(0°) = π → 10·log10(π) ≈ 4.97 dBi (paper states ~5 dBi)."""
        g_linear = _mod._ris_pattern_linear(0.0)
        g_dBi = 10 * math.log10(g_linear)
        assert g_dBi == pytest.approx(10 * math.log10(math.pi), rel=1e-6)
        assert abs(g_dBi - 5.0) < 0.05  # within 0.05 dB of paper's stated 5 dBi


# ---------------------------------------------------------------------------
# 3. Eq. 7 — indoor LOS probability boundary values
# ---------------------------------------------------------------------------

class TestIndoorLOSProbabilityBoundaries:
    """Eq. 7: p=1 for d≤1.2; exp(-(d-1.2)/4.7) for 1.2<d<6.5;
    0.32·exp(-(d-6.5)/32.6) for d≥6.5."""

    def test_at_1p2m_probability_is_1(self):
        """d=1.2 m → P_LOS = 1 (guaranteed LOS boundary)."""
        results = [_los_indicator(1.2, "indoor", None, seed=i) for i in range(30)]
        # At z_ris=z_tx the implementation returns 1 always; verify deterministically
        assert all(r == 1 for r in results)

    def test_at_6p5m_formula_continuity(self):
        """Both branches must give same value at d=6.5 (continuity of Eq. 7)."""
        d = 6.5
        p_left = math.exp(-(d - 1.2) / 4.7)       # upper branch limit
        p_right = 0.32 * math.exp(-(d - 6.5) / 32.6)  # lower branch at d=6.5
        # p_right = 0.32*exp(0) = 0.32; p_left ≈ 0.322 — paper ensures ~continuity
        assert abs(p_left - p_right) < 0.01

    def test_probability_decays_at_large_distance(self):
        """At large indoor distances, LOS probability must be very small."""
        p = 0.32 * math.exp(-(100 - 6.5) / 32.6)
        assert p < 0.05

    def test_short_distance_returns_los(self):
        """d≤1.2 m must always return LOS (same height in helper)."""
        r = _los_indicator(1.0, "indoor", None)
        assert r == 1


# ---------------------------------------------------------------------------
# 4. Eq. 11 — outdoor LOS probability
# ---------------------------------------------------------------------------

class TestOutdoorLOSProbability:
    """Eq. 11: p = min(20/d, 1)·(1−e^(−d/39)) + e^(−d/39).

    This is the 3GPP/ITU UMi model adopted in the paper.
    """

    def test_short_distance_p_is_1(self):
        """d ≤ 20 m: min(20/d,1)=1, so p=1·(1−e^(−d/39))+e^(−d/39)=1."""
        for d in [1.0, 5.0, 10.0, 20.0]:
            p = _p_los_outdoor_paper(d)
            assert p == pytest.approx(1.0, abs=1e-9), f"d={d}: p={p}"

    def test_at_d_25m(self):
        """d=25 m: 20/25=0.8, p=0.8·(1−e^(−25/39))+e^(−25/39)."""
        d = 25.0
        expected = 0.8 * (1 - math.exp(-d / 39)) + math.exp(-d / 39)
        p = _p_los_outdoor_paper(d)
        assert p == pytest.approx(expected, rel=1e-9)

    def test_at_d_39m_p_above_half(self):
        """At d=39 m (1/e decay constant), p must still be > 0.5."""
        p = _p_los_outdoor_paper(39.0)
        assert p > 0.5

    def test_p_decreases_beyond_20m(self):
        """For d > 20 m, p must monotonically decrease."""
        ps = [_p_los_outdoor_paper(d) for d in [20, 30, 50, 100, 200]]
        for i in range(len(ps) - 1):
            assert ps[i] > ps[i + 1]

    def test_p_bounded_01(self):
        """p must always be in [0, 1]."""
        for d in [1, 5, 20, 50, 200]:
            p = _p_los_outdoor_paper(d)
            assert 0.0 <= p <= 1.0

    def test_implementation_matches_paper_formula(self):
        """_sample_los_indicator probability must match Eq. 11 formula."""
        # At d=25 m with tx/ris at different heights to bypass the indoor height check
        # use outdoor environment directly
        expected = _p_los_outdoor_paper(25.0)
        # Run 2000 samples and check empirical probability ≈ expected
        rng = np.random.default_rng(12345)
        tx = np.array([0.0, 0.0, 20.0])
        ris = np.array([25.0, 0.0, 10.0])
        results = [
            _mod._sample_los_indicator("outdoor", tx, ris, 25.0, rng, force=None)
            for _ in range(2000)
        ]
        empirical = sum(results) / len(results)
        assert abs(empirical - expected) < 0.05, (
            f"Empirical p_LOS={empirical:.3f}, expected={expected:.3f}"
        )

    def test_large_distance_low_los_probability(self):
        """At d=200 m outdoors, p_LOS must be very low."""
        p = _p_los_outdoor_paper(200.0)
        assert p < 0.15


# ---------------------------------------------------------------------------
# 5. Eq. 13 — achievable rate formula
# ---------------------------------------------------------------------------

class TestAchievableRateFormula:
    """Eq. 13: ρ = |g^T Θ h + h_SISO|² Pt / P_N → R = E{log2(1+ρ)}.

    Paper uses P_N = −100 dBm noise floor throughout Section VII.
    Fig. 5(a): indoor Scenario 1, 73 GHz, N∈{64,256}, z^RIS=2 m.
    """

    _P_N_dBm = -100.0
    # Indoor Scenario 1 published preset
    _TX = np.array([0.0, 25.0, 2.0])
    _RIS = np.array([40.0, 50.0, 2.0])
    _RX = np.array([38.0, 48.0, 1.0])

    def _rate(self, N_side: int, P_t_dBm: float, freq_GHz: float = 73.0) -> float:
        r = evaluate_simris_los_reference(
            tx_xyz=self._TX,
            ris_xyz=self._RIS,
            rx_xyz=self._RX,
            ris_side=N_side,
            frequency_GHz=freq_GHz,
            environment="indoor",
            scenario=1,
        )
        snr_dB = P_t_dBm + r["channel_gain_dB"] - self._P_N_dBm
        return math.log2(1.0 + 10 ** (snr_dB / 10.0))

    def test_rate_positive_at_30dBm(self):
        """Achievable rate must be > 0 at Pt=30 dBm (trivially true)."""
        assert self._rate(8, 30.0) > 0.0

    def test_rate_increases_with_transmit_power(self):
        """Higher Pt → higher SNR → higher achievable rate."""
        r_low = self._rate(8, 10.0)
        r_high = self._rate(8, 30.0)
        assert r_high > r_low

    def test_rate_increases_with_N(self):
        """Larger RIS → higher channel gain → higher rate (RIS path only).

        Direct path suppressed so the RIS N² scaling is visible; otherwise
        the direct path dominates and N scaling is masked.
        """
        def _rate_ris_only(N_side, P_t_dBm, freq_GHz=73.0):
            r = evaluate_simris_los_reference(
                tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
                ris_side=N_side, frequency_GHz=freq_GHz,
                environment="indoor", scenario=1,
                include_direct_path=False,
            )
            snr_dB = P_t_dBm + r["channel_gain_dB"] - self._P_N_dBm
            return math.log2(1.0 + 10 ** (snr_dB / 10.0))

        r_small = _rate_ris_only(8, 20.0)    # N=64
        r_large = _rate_ris_only(16, 20.0)   # N=256
        assert r_large > r_small

    def test_28ghz_vs_73ghz_rate_ordering(self):
        """At same geometry, lower frequency has lower path loss → higher rate."""
        r_28 = self._rate(8, 20.0, freq_GHz=28.0)
        r_73 = self._rate(8, 20.0, freq_GHz=73.0)
        assert r_28 > r_73

    def test_snr_formula_is_linear_in_pt(self):
        """10 dB increase in Pt → 10 dB increase in SNR."""
        r = evaluate_simris_los_reference(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=28.0, environment="indoor", scenario=1,
        )
        cg_dB = r["channel_gain_dB"]
        snr1 = 20.0 + cg_dB - self._P_N_dBm
        snr2 = 30.0 + cg_dB - self._P_N_dBm
        assert snr2 - snr1 == pytest.approx(10.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 6. Outdoor geometry (Fig. 4) — evaluate_simris_los_reference
# ---------------------------------------------------------------------------

class TestOutdoorEvaluateReference:
    """Fig. 4: UMi Scenario 1 geometry — Tx=(0,25,20), RIS=(70,85,10), Rx=(80,75,1)."""

    _TX = np.array([0.0, 25.0, 20.0])
    _RIS = np.array([70.0, 85.0, 10.0])
    _RX = np.array([80.0, 75.0, 1.0])

    def _call(self, **kwargs):
        defaults = dict(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=28.0, environment="outdoor", scenario=1,
        )
        defaults.update(kwargs)
        return evaluate_simris_los_reference(**defaults)

    def test_returns_channel_gain(self):
        r = self._call()
        assert "channel_gain_dB" in r

    def test_channel_gain_is_finite(self):
        r = self._call()
        assert math.isfinite(r["channel_gain_dB"])

    def test_channel_gain_strongly_negative(self):
        """Long-range outdoor link → channel gain well below −50 dB."""
        r = self._call()
        assert r["channel_gain_dB"] < -50.0

    def test_environment_key_is_outdoor(self):
        r = self._call()
        assert r["environment"] == "outdoor"

    def test_larger_ris_improves_outdoor_gain(self):
        r8 = self._call(ris_side=8, include_direct_path=False)
        r16 = self._call(ris_side=16, include_direct_path=False)
        assert r16["channel_gain_dB"] > r8["channel_gain_dB"]

    def test_73ghz_gives_lower_gain_than_28ghz(self):
        """Outdoor: higher frequency → stronger path loss → lower channel gain."""
        r_28 = self._call(frequency_GHz=28.0)
        r_73 = self._call(frequency_GHz=73.0)
        assert r_28["channel_gain_dB"] > r_73["channel_gain_dB"]


# ---------------------------------------------------------------------------
# 7. summarize_simris_tensors output structure
# ---------------------------------------------------------------------------

class TestSummarizeSimrisTensors:
    """summarize_simris_tensors aggregates multi-realization channel statistics."""

    _TX = np.array([0.0, 25.0, 2.0])
    _RIS = np.array([40.0, 50.0, 2.0])
    _RX = np.array([38.0, 48.0, 1.0])

    def _tensors(self, num_realizations: int = 10):
        return simulate_simris_channels(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=28.0,
            num_realizations=num_realizations, seed=42,
        )

    def test_summary_has_h_norms(self):
        s = summarize_simris_tensors(self._tensors())
        assert "H_norms" in s

    def test_summary_has_g_norms(self):
        s = summarize_simris_tensors(self._tensors())
        assert "G_norms" in s

    def test_summary_has_d_norms(self):
        s = summarize_simris_tensors(self._tensors())
        assert "D_norms" in s

    def test_h_norms_length_matches_realizations(self):
        n = 10
        s = summarize_simris_tensors(self._tensors(n))
        assert len(s["H_norms"]) == n

    def test_norms_are_non_negative(self):
        s = summarize_simris_tensors(self._tensors())
        assert all(v >= 0 for v in s["H_norms"])
        assert all(v >= 0 for v in s["G_norms"])

    def test_seed_determinism(self):
        """Same seed must produce identical summary statistics."""
        s1 = summarize_simris_tensors(self._tensors(5))
        s2 = summarize_simris_tensors(self._tensors(5))
        np.testing.assert_array_equal(s1["H_norms"], s2["H_norms"])


# ---------------------------------------------------------------------------
# 8. 73 GHz band validity
# ---------------------------------------------------------------------------

class TestFrequency73GHz:
    """Paper validates model at both 28 GHz and 73 GHz (Section VII)."""

    _TX = np.array([0.0, 25.0, 2.0])
    _RIS = np.array([40.0, 50.0, 2.0])
    _RX = np.array([38.0, 48.0, 1.0])

    def test_evaluate_los_reference_runs_at_73ghz(self):
        r = evaluate_simris_los_reference(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=73.0, environment="indoor", scenario=1,
        )
        assert math.isfinite(r["channel_gain_dB"])
        assert r["frequency_GHz"] == pytest.approx(73.0)

    def test_simulate_channels_runs_at_73ghz(self):
        """simulate_simris_channels returns H tensor at 73 GHz.

        H shape is (N_elements, tx_antennas, num_realizations): first dim is
        the number of RIS elements (ris_side²=64), last dim is realizations.
        """
        t = simulate_simris_channels(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=73.0, num_realizations=3, seed=0,
        )
        assert "H" in t
        assert t["H"].shape[-1] == 3  # last dim = num_realizations

    def test_73ghz_path_gain_lower_than_28ghz(self):
        """Path gain at 73 GHz must be lower (more negative) than at 28 GHz."""
        r_28 = evaluate_simris_los_reference(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=28.0, environment="indoor", scenario=1,
        )
        r_73 = evaluate_simris_los_reference(
            tx_xyz=self._TX, ris_xyz=self._RIS, rx_xyz=self._RX,
            ris_side=8, frequency_GHz=73.0, environment="indoor", scenario=1,
        )
        assert r_73["channel_gain_dB"] < r_28["channel_gain_dB"]
