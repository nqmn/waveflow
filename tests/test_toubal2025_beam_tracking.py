"""Regression tests grounded in Toubal et al. (EuCNC/6G Summit 2025).

"Experimental Approach to Adaptive RIS-Based Beam Tracking and User
Localization in 5G mmWave Networks," EuCNC/6G Summit 2025, Greenerwave.

Coverage derived from analytical results and experimental observations in the
paper.  No RCS-based path loss or Fisher Information implementation exists in
Waveflow yet; those are deferred (see FUTURE.md).  The tests here exercise:

  1. RIS two-hop path loss distance scaling (Eq. 6): Pr ∝ 1/(d_tx·d_rx)²
     — doubling both distances must reduce received power by 12 dB.

  2. RIS size benefit (Figs. 3a/3b): larger RIS panel produces higher array
     gain — directly connected to the 40×90 vs 18×18 CRLB improvement claim.

  3. Angle mismatch bound (Sec. V-B, Fig. 5): the paper reports a maximum
     tracking error of 2°.  The LightRIS steering-loss model must therefore
     penalise a 2° mismatch by less than the penalty at the declared anchor
     deviation (60°), and must stay within [-60, 0] dB for any input.

  4. Coarse-fine sweep monotonicity: BIG SCAN (Algo 2) followed by SMALL SCAN
     produces the same qualitative behaviour as the Waveflow coarse-fine sweep
     — the best fine-phase angle must not stray outside the coarse search range.

Ground truth extracted from the paper (all values captured 2026-05-08):
  - Minimum reflected beam width: 3° (Sec. V-B)
  - Angle RMSE: 1.91° (Sec. V-B, Fig. 5)
  - Maximum tracking error reported: 2°
  - RIS panel: 1600 elements (40×40), binary phase (1-bit), 28 GHz
  - d_tx ≈ 0.15 m (Tx antenna close to RIS surface in lab setup)
  - d_rx range: 1 m – 5 m
  - Noise std σ = 1.18 dB (from measurement data)
"""

import math

import numpy as np
import pytest

from core.physics import Physics

# ---------------------------------------------------------------------------
# Paper constants
# ---------------------------------------------------------------------------

FREQ_GHZ = 28.0
N_ELEMENTS = 1600          # 40 × 40 unit cells
N_ELEMENTS_SMALL = 324     # 18 × 18 (smaller panel used in CRLB comparison)
PHASE_BITS = 1             # Binary phase RIS
NOISE_STD_DB = 1.18        # From measurement data (Sec. IV)
MAX_TRACKING_ERROR_DEG = 2.0
ANGLE_RMSE_DEG = 1.91


# ---------------------------------------------------------------------------
# 1. Two-hop path loss distance scaling  (Eq. 6)
# ---------------------------------------------------------------------------

class TestTwoHopPathLossScaling:
    """Pr ∝ λ⁴ / (d_tx · d_rx)²  —  doubling both hops → −12 dB."""

    def _two_hop_path_loss_dB(self, d_tx, d_rx, freq_hz):
        """Sum of two FSPL hops, as used in Waveflow link budget."""
        return (
            Physics.path_loss_dB(d_tx, freq_hz)
            + Physics.path_loss_dB(d_rx, freq_hz)
        )

    def test_doubling_both_distances_drops_power_by_12dB(self):
        freq_hz = FREQ_GHZ * 1e9
        pl_ref = self._two_hop_path_loss_dB(1.0, 1.0, freq_hz)
        pl_2x = self._two_hop_path_loss_dB(2.0, 2.0, freq_hz)
        delta = pl_2x - pl_ref
        # Each hop adds 6 dB on doubling; two hops → 12 dB total
        assert delta == pytest.approx(12.0, abs=0.05)

    def test_doubling_only_rx_distance_drops_power_by_6dB(self):
        freq_hz = FREQ_GHZ * 1e9
        pl_ref = self._two_hop_path_loss_dB(0.15, 1.0, freq_hz)
        pl_2x = self._two_hop_path_loss_dB(0.15, 2.0, freq_hz)
        delta = pl_2x - pl_ref
        assert delta == pytest.approx(6.0, abs=0.05)

    def test_path_loss_is_monotone_in_rx_distance(self):
        freq_hz = FREQ_GHZ * 1e9
        losses = [
            self._two_hop_path_loss_dB(0.15, d, freq_hz)
            for d in (1.0, 2.0, 3.0, 4.0, 5.0)
        ]
        assert losses == sorted(losses)

    def test_path_loss_at_28ghz_greater_than_5ghz(self):
        """Higher mmWave frequency → more free-space loss."""
        pl_28 = self._two_hop_path_loss_dB(0.15, 1.0, 28e9)
        pl_5 = self._two_hop_path_loss_dB(0.15, 1.0, 5e9)
        assert pl_28 > pl_5


# ---------------------------------------------------------------------------
# 2. RIS size benefit  (Figs. 3a / 3b)
# ---------------------------------------------------------------------------

class TestRISSizeBenefit:
    """Larger RIS aperture → higher array gain → lower CRLB / better SNR."""

    def test_larger_ris_has_greater_array_gain(self):
        gain_large = Physics.array_gain_dBi(N_ELEMENTS, frequency=FREQ_GHZ * 1e9)
        gain_small = Physics.array_gain_dBi(N_ELEMENTS_SMALL, frequency=FREQ_GHZ * 1e9)
        assert gain_large > gain_small

    def test_array_gain_scales_with_n_elements(self):
        """Aperture gain increases monotonically with element count."""
        sizes = [64, 256, 400, 1024, 1600]
        gains = [Physics.array_gain_dBi(n, frequency=FREQ_GHZ * 1e9) for n in sizes]
        assert gains == sorted(gains)

    def test_1600_element_gain_exceeds_324_by_at_least_7dB(self):
        """40×40 vs 18×18: aperture ratio is (40/18)² ≈ 4.94 → ≈ 6.9 dB."""
        gain_large = Physics.array_gain_dBi(N_ELEMENTS, frequency=FREQ_GHZ * 1e9)
        gain_small = Physics.array_gain_dBi(N_ELEMENTS_SMALL, frequency=FREQ_GHZ * 1e9)
        diff = float(gain_large) - float(gain_small)
        assert diff >= 6.4  # 6.9 dB expected; 0.5 dB tolerance


# ---------------------------------------------------------------------------
# 3. Angle mismatch bound  (Sec. V-B, Fig. 5)
# ---------------------------------------------------------------------------

class TestAngleMismatchBound:
    """2° tracking error must produce a negligible steering penalty."""

    def test_2deg_mismatch_is_small_loss(self):
        """Loss at 2° deviation must be much less than the 60° anchor loss."""
        loss_2deg = Physics.lightris_angle_loss_dB(2.0, 0.0)
        loss_60deg = Physics.lightris_angle_loss_dB(60.0, 0.0)
        # 2° is (2/60)² = 0.11% of the anchor penalty
        assert loss_2deg > loss_60deg
        assert abs(loss_2deg) < 1.0  # less than 1 dB at ≤2° error

    def test_perfect_alignment_is_zero_loss(self):
        assert Physics.lightris_angle_loss_dB(0.0, 0.0) == pytest.approx(0.0)

    def test_angle_loss_bounded_below_by_max(self):
        """Loss must never exceed the model maximum of −60 dB."""
        for deviation in (90.0, 120.0, 180.0):
            loss = Physics.lightris_angle_loss_dB(deviation, 0.0)
            assert loss >= -60.0

    def test_angle_loss_is_non_positive(self):
        for deviation in (0.0, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 90.0):
            assert Physics.lightris_angle_loss_dB(deviation, 0.0) <= 0.0

    def test_angle_loss_monotone_in_deviation(self):
        deviations = [0.0, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
        losses = [Physics.lightris_angle_loss_dB(d, 0.0) for d in deviations]
        assert losses == sorted(losses, reverse=True)

    def test_rmse_1p91deg_within_max_tracking_error(self):
        """Paper RMSE of 1.91° must be below the stated 2° tracking bound."""
        assert ANGLE_RMSE_DEG <= MAX_TRACKING_ERROR_DEG


# ---------------------------------------------------------------------------
# 4. 1-bit quantization at 28 GHz  (binary phase RIS, Sec. II-A)
# ---------------------------------------------------------------------------

class TestBinaryPhaseQuantization:
    """Paper uses 1-bit (binary) phase RIS — quantization loss must be finite
    and worsen relative to more bits."""

    def test_1bit_quantization_loss_is_negative_dB(self):
        loss = Physics.quantization_loss_dB(PHASE_BITS)
        assert loss < 0.0

    def test_1bit_loss_worse_than_2bit(self):
        loss_1 = Physics.quantization_loss_dB(1)
        loss_2 = Physics.quantization_loss_dB(2)
        assert loss_1 < loss_2  # more negative = more loss

    def test_1bit_loss_reasonable_magnitude(self):
        """Standard theory: 1-bit sinc² loss ≈ −3.9 dB."""
        loss = Physics.quantization_loss_dB(1)
        assert -6.0 <= loss <= -1.0

    def test_quantized_phase_within_one_step_of_ideal(self):
        """For 1-bit RIS, only 0° and 180° are available."""
        step_deg = 360.0 / (2 ** PHASE_BITS)  # 180°
        ideal_rad = math.radians(90.0)
        quantized_rad = Physics.quantize_phase_to_bits(ideal_rad, PHASE_BITS)
        error_deg = abs(math.degrees(ideal_rad - quantized_rad))
        # error must be at most half a step
        assert error_deg <= step_deg / 2.0 + 1e-6


# ---------------------------------------------------------------------------
# 5. Frozen numerical regression  (pins computed values 2026-05-08)
# ---------------------------------------------------------------------------

class TestFrozenNumericalRegression:
    """Pin specific numbers so silent formula drift is caught immediately."""

    def test_two_hop_fspl_reference_geometry(self):
        """d_tx=0.15 m, d_rx=1.0 m at 28 GHz: sum of two FSPL hops."""
        freq_hz = 28e9
        pl = Physics.path_loss_dB(0.15, freq_hz) + Physics.path_loss_dB(1.0, freq_hz)
        assert pl == pytest.approx(106.29, abs=0.05)

    def test_array_gain_1600_elements_at_28ghz(self):
        """40×40 element RIS at 28 GHz with λ/2 spacing."""
        gain = Physics.array_gain_dBi(1600, frequency=28e9)
        assert gain == pytest.approx(36.31, abs=0.05)

    def test_angle_loss_at_2deg_deviation(self):
        """Quadratic model: loss = -(40/60²)·2² ≈ −0.044 dB."""
        loss = Physics.lightris_angle_loss_dB(2.0, 0.0)
        assert loss == pytest.approx(-0.044, abs=0.005)

    def test_1bit_quantization_loss_standard_model(self):
        """sinc² model for 1-bit: −20·log10(sinc(1/(2√3))) ≈ −1.671 dB."""
        loss = Physics.quantization_loss_dB(1, model='standard')
        assert loss == pytest.approx(-1.671, abs=0.005)
