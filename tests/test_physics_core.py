"""Physics core coverage tests for functions with no prior test coverage.

Each test validates against an analytically derived or well-known reference value,
not just "does not crash."
"""
import numpy as np
import pytest
from core.physics import Physics, C


# ---------------------------------------------------------------------------
# atmospheric_loss_dB
# ---------------------------------------------------------------------------

class TestAtmosphericLoss:
    def test_below_10ghz_uses_default_alpha(self):
        # alpha = 0.00001, distance = 1000 m → 0.00001 * 1000 = 0.01 dB
        assert Physics.atmospheric_loss_dB(1000, 5.0) == pytest.approx(0.01, rel=1e-6)

    def test_band_10_to_24ghz_linear_alpha(self):
        # freq = 17 GHz → alpha = 0.0001 + (17-10)*0.00002 = 0.0001 + 0.00014 = 0.00024
        # distance = 500 m → loss = 0.00024 * 500 = 0.12 dB
        assert Physics.atmospheric_loss_dB(500, 17.0) == pytest.approx(0.12, rel=1e-6)

    def test_band_24_to_50ghz_linear_alpha(self):
        # freq = 30 GHz → alpha = 0.0003 + (30-24)*0.00015 = 0.0003 + 0.0009 = 0.0012
        # distance = 200 m → loss = 0.0012 * 200 = 0.24 dB
        assert Physics.atmospheric_loss_dB(200, 30.0) == pytest.approx(0.24, rel=1e-6)

    def test_oxygen_absorption_peak_60ghz(self):
        # At 60 GHz: peak_factor = 1 - |60-60|/3 = 1.0
        # alpha = 0.005 + 1.0 * 0.010 = 0.015
        # distance = 100 m → loss = 1.5 dB
        assert Physics.atmospheric_loss_dB(100, 60.0) == pytest.approx(1.5, rel=1e-6)

    def test_oxygen_absorption_57ghz_lower_peak(self):
        # freq = 57 GHz → peak_factor = 1 - |57-60|/3 = 0.0
        # alpha = 0.005 + 0.0 * 0.010 = 0.005
        # distance = 100 m → loss = 0.5 dB
        assert Physics.atmospheric_loss_dB(100, 57.0) == pytest.approx(0.5, rel=1e-6)

    def test_above_64ghz_uses_tail_alpha(self):
        # freq = 70 GHz → alpha = 0.003 + (70-64)*0.00005 = 0.003 + 0.0003 = 0.0033
        # distance = 1000 m → loss = 3.3 dB
        assert Physics.atmospheric_loss_dB(1000, 70.0) == pytest.approx(3.3, rel=1e-6)

    def test_loss_scales_linearly_with_distance(self):
        loss_1km = Physics.atmospheric_loss_dB(1000, 5.0)
        loss_2km = Physics.atmospheric_loss_dB(2000, 5.0)
        assert loss_2km == pytest.approx(2 * loss_1km, rel=1e-6)

    def test_zero_distance_returns_zero(self):
        assert Physics.atmospheric_loss_dB(0, 10.0) == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# rician_fading
# ---------------------------------------------------------------------------

class TestRicianFading:
    def test_high_k_factor_approaches_unity(self):
        # Very high K → nearly deterministic LOS component ≈ 1
        np.random.seed(0)
        samples = [Physics.rician_fading(30.0) for _ in range(500)]
        assert np.mean(samples) == pytest.approx(1.0, abs=0.05)

    def test_zero_k_rayleigh_mean(self):
        # K = 0 dB → K_linear = 1 → NOT Rayleigh, but mean should be near sqrt(π/2(K+1))
        # For K_linear=1: los = sqrt(0.5), scatter_std = sqrt(0.5)
        # Mean of |h| ≈ sqrt(π/4) ≈ 0.886 for this parametrisation
        np.random.seed(42)
        samples = np.array([Physics.rician_fading(0.0) for _ in range(2000)])
        assert samples.mean() == pytest.approx(0.886, abs=0.04)

    def test_returns_positive_magnitude(self):
        np.random.seed(1)
        val = Physics.rician_fading(10.0)
        assert val > 0

    def test_size_returns_array(self):
        np.random.seed(2)
        result = Physics.rician_fading(10.0, size=100)
        assert hasattr(result, '__len__')
        assert len(result) == 100
        assert np.all(result > 0)

    def test_size_1_returns_scalar(self):
        np.random.seed(3)
        val = Physics.rician_fading(10.0, size=1)
        assert np.isscalar(val) or (hasattr(val, 'ndim') and val.ndim == 0)


# ---------------------------------------------------------------------------
# mutual_coupling_penalty
# ---------------------------------------------------------------------------

class TestMutualCouplingPenalty:
    def test_disabled_returns_zero(self):
        assert Physics.mutual_coupling_penalty(0.3, coupling_enabled=False) == 0.0

    def test_tight_spacing_returns_2dB(self):
        # spacing ≤ 0.5λ → 2.0 dB
        assert Physics.mutual_coupling_penalty(0.3) == pytest.approx(2.0)
        assert Physics.mutual_coupling_penalty(0.5) == pytest.approx(2.0)

    def test_moderate_spacing_returns_1dB(self):
        # 0.5 < spacing ≤ 0.7λ → 1.0 dB
        assert Physics.mutual_coupling_penalty(0.6) == pytest.approx(1.0)
        assert Physics.mutual_coupling_penalty(0.7) == pytest.approx(1.0)

    def test_wide_spacing_returns_zero(self):
        # spacing > 0.7λ → 0.0 dB
        assert Physics.mutual_coupling_penalty(0.8) == pytest.approx(0.0)
        assert Physics.mutual_coupling_penalty(2.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# quantization_loss_with_state
# ---------------------------------------------------------------------------

class TestQuantizationLossWithState:
    def test_zero_bits_returns_zero(self):
        assert Physics.quantization_loss_with_state(0, 0.0) == pytest.approx(0.0)

    def test_even_state_no_variation(self):
        # state_fraction = 0.0 → state_idx = 0 (even) → variation = 0.0
        base = Physics.quantization_loss_dB(2)
        result = Physics.quantization_loss_with_state(2, 0.0)
        assert result == pytest.approx(base, rel=1e-6)

    def test_odd_state_adds_0p2dB(self):
        # 2-bit: num_states=4; fraction=0.25 → state_idx=1 (odd) → variation=0.2
        base = Physics.quantization_loss_dB(2)
        result = Physics.quantization_loss_with_state(2, 0.25)
        assert result == pytest.approx(base + 0.2, rel=1e-6)

    def test_state_wraps_correctly(self):
        # fraction = 1.0 → state_idx = num_states % num_states = 0 → no variation
        base = Physics.quantization_loss_dB(1)
        result = Physics.quantization_loss_with_state(1, 1.0)
        assert result == pytest.approx(base, rel=1e-6)

    def test_loss_is_negative_dB(self):
        # quantization always reduces gain → loss should be negative
        result = Physics.quantization_loss_with_state(2, 0.0)
        assert result < 0


# ---------------------------------------------------------------------------
# phase_error_per_element
# ---------------------------------------------------------------------------

class TestPhaseErrorPerElement:
    def test_only_quantization_bounded(self):
        # With only quantization, error must be within ±π/(2^bits) / 2
        bits = 2
        bound = np.pi / (2 ** bits) / 2
        for idx in range(8):
            err = Physics.phase_error_per_element(
                idx, 16, bits,
                include_quantization=True,
                include_manufacturing=False,
                include_temperature=False,
                seed=idx,
            )
            assert abs(err) <= bound + 1e-9

    def test_no_error_sources_returns_zero(self):
        err = Physics.phase_error_per_element(
            0, 16, 2,
            include_quantization=False,
            include_manufacturing=False,
            include_temperature=False,
            seed=0,
        )
        assert err == pytest.approx(0.0)

    def test_seeded_is_reproducible(self):
        e1 = Physics.phase_error_per_element(3, 16, 2, seed=99)
        e2 = Physics.phase_error_per_element(3, 16, 2, seed=99)
        assert e1 == pytest.approx(e2)

    def test_different_elements_differ(self):
        e0 = Physics.phase_error_per_element(0, 16, 2, seed=10)
        e1 = Physics.phase_error_per_element(1, 16, 2, seed=10)
        # seed+element_idx differs, so errors should differ
        assert e0 != pytest.approx(e1)

    def test_returns_scalar(self):
        err = Physics.phase_error_per_element(0, 16, 2, seed=0)
        assert np.isscalar(err) or (hasattr(err, 'ndim') and err.ndim == 0)


# ---------------------------------------------------------------------------
# compute_quantized_beam_angle
# ---------------------------------------------------------------------------

class TestComputeQuantizedBeamAngle:
    def test_zero_bits_returns_ideal_unchanged(self):
        angle, err = Physics.compute_quantized_beam_angle(37.5, 0, 16)
        assert angle == pytest.approx(37.5)
        assert err == pytest.approx(0.0)

    def test_zero_degree_angle_no_error(self):
        angle, err = Physics.compute_quantized_beam_angle(0.0, 2, 16)
        assert err == pytest.approx(0.0, abs=1e-9)

    def test_quantized_angle_within_one_step(self):
        # achievable angle must be within ±min_angle_step/2 of ideal
        bits = 2
        num_levels = 2 ** bits
        phase_step = 2 * np.pi / num_levels
        min_angle_step = np.degrees(2 * phase_step / (2 * np.pi))
        ideal = 15.0
        angle, err = Physics.compute_quantized_beam_angle(ideal, bits, 16)
        assert abs(err) <= min_angle_step / 2 + 1e-9

    def test_error_is_ideal_minus_achievable(self):
        ideal = 25.0
        angle, err = Physics.compute_quantized_beam_angle(ideal, 3, 16)
        assert err == pytest.approx(ideal - angle, rel=1e-9)

    def test_more_bits_smaller_error(self):
        ideal = 22.5
        _, err_2bit = Physics.compute_quantized_beam_angle(ideal, 2, 16)
        _, err_4bit = Physics.compute_quantized_beam_angle(ideal, 4, 16)
        assert abs(err_4bit) <= abs(err_2bit) + 1e-9


# ---------------------------------------------------------------------------
# angle_loss_dB
# ---------------------------------------------------------------------------

class TestAngleLossdB:
    def test_zero_deviation_no_loss(self):
        assert Physics.angle_loss_dB(30.0, 30.0) == pytest.approx(0.0, abs=1e-9)

    def test_60_degree_deviation_is_minus40dB(self):
        # formula: loss = -(40/3600) * 60^2 = -40 dB
        assert Physics.angle_loss_dB(90.0, 30.0) == pytest.approx(-40.0, rel=1e-6)

    def test_clamped_at_minus60dB(self):
        # very large deviation → clamped to -60 dB
        result = Physics.angle_loss_dB(0.0, 180.0)
        assert result == pytest.approx(-60.0)

    def test_loss_is_non_positive(self):
        for delta in [0, 10, 30, 60, 90, 180]:
            assert Physics.angle_loss_dB(delta, 0.0) <= 0.0

    def test_symmetric_around_target(self):
        # +θ and -θ offset should give identical loss
        loss_plus = Physics.angle_loss_dB(45.0, 0.0)
        loss_minus = Physics.angle_loss_dB(-45.0, 0.0)
        assert loss_plus == pytest.approx(loss_minus, rel=1e-6)

    def test_wraps_through_360(self):
        # 350° vs 10° → 20° deviation, same as 10° vs -10°
        loss_wrap = Physics.angle_loss_dB(350.0, 10.0)
        loss_direct = Physics.angle_loss_dB(-10.0, 10.0)
        assert loss_wrap == pytest.approx(loss_direct, rel=1e-6)


# ---------------------------------------------------------------------------
# snr_to_evm
# ---------------------------------------------------------------------------

class TestSnrToEvm:
    def test_known_value_20dB(self):
        # SNR = 20 dB → linear = 100 → EVM = 1/sqrt(100) * 100 = 10%
        assert Physics.snr_to_evm(20.0) == pytest.approx(10.0, rel=1e-6)

    def test_known_value_0dB(self):
        # SNR = 0 dB → linear = 1 → EVM = 100%
        assert Physics.snr_to_evm(0.0) == pytest.approx(100.0, rel=1e-6)

    def test_known_value_40dB(self):
        # SNR = 40 dB → linear = 10000 → EVM = 1/100 * 100 = 1%
        assert Physics.snr_to_evm(40.0) == pytest.approx(1.0, rel=1e-6)

    def test_higher_snr_lower_evm(self):
        assert Physics.snr_to_evm(30.0) < Physics.snr_to_evm(10.0)

    def test_evm_is_positive(self):
        assert Physics.snr_to_evm(15.0) > 0


# ---------------------------------------------------------------------------
# multipath_ris_gain
# ---------------------------------------------------------------------------

class TestMultipathRisGain:
    def test_single_path_coherent_phases(self):
        # All-zero phases → ris_response = N → |ris_response|^2 = N^2
        # total_power = amplitude * N^2; gain = total_power / N^2 = amplitude → 0 dB for amp=1
        N = 16
        phases = np.zeros(N)
        paths = [{'amplitude': 1.0, 'phase': 0.0}]
        gain = Physics.multipath_ris_gain(paths, phases)
        assert gain == pytest.approx(0.0, abs=0.5)

    def test_multiple_paths_increase_power(self):
        N = 16
        phases = np.zeros(N)
        paths_one = [{'amplitude': 1.0, 'phase': 0.0}]
        paths_two = [{'amplitude': 1.0, 'phase': 0.0}, {'amplitude': 1.0, 'phase': 0.0}]
        gain_one = Physics.multipath_ris_gain(paths_one, phases)
        gain_two = Physics.multipath_ris_gain(paths_two, phases)
        assert gain_two > gain_one

    def test_zero_amplitude_path_returns_low_gain(self):
        N = 16
        phases = np.zeros(N)
        paths = [{'amplitude': 0.0, 'phase': 0.0}]
        gain = Physics.multipath_ris_gain(paths, phases)
        assert gain < -90  # Near -inf dB, clamped to 10*log10(1e-10)

    def test_returns_scalar_float(self):
        phases = np.zeros(8)
        paths = [{'amplitude': 0.5, 'phase': 0.0}]
        gain = Physics.multipath_ris_gain(paths, phases)
        assert isinstance(gain, float)


# ---------------------------------------------------------------------------
# effective_snr_with_waveform_distortion
# ---------------------------------------------------------------------------

class TestEffectiveSnrWithWaveformDistortion:
    def test_zero_impairments_reduces_only_by_papr_and_eq(self):
        # quant_error=0 → sinc(0)=1 → quant_loss=0 dB
        # papr=8 dB → papr_loss = -8/5 = -1.6 dB
        # eq_loss = 0.5 dB
        # effective = 30 + 0 - 1.6 - 0.5 = 27.9 dB
        result = Physics.effective_snr_with_waveform_distortion(30.0, 0.0, papr_dB=8.0,
                                                                 equalization_error_dB=0.5)
        assert result == pytest.approx(27.9, rel=1e-4)

    def test_effective_snr_less_than_ideal(self):
        ideal = 25.0
        effective = Physics.effective_snr_with_waveform_distortion(ideal, 15.0)
        assert effective < ideal

    def test_larger_quant_error_lower_snr(self):
        snr_small = Physics.effective_snr_with_waveform_distortion(20.0, 5.0)
        snr_large = Physics.effective_snr_with_waveform_distortion(20.0, 30.0)
        assert snr_large < snr_small

    def test_larger_papr_lower_snr(self):
        snr_low_papr = Physics.effective_snr_with_waveform_distortion(20.0, 0.0, papr_dB=4.0)
        snr_high_papr = Physics.effective_snr_with_waveform_distortion(20.0, 0.0, papr_dB=12.0)
        assert snr_high_papr < snr_low_papr


# ---------------------------------------------------------------------------
# ris_coupling_loss_dB
# ---------------------------------------------------------------------------

class TestRisCouplingLossdB:
    def test_simplified_tight_spacing(self):
        # spacing ≤ 0.5: spacing_loss = 2.0
        # N=256 (16x16): count_factor = 20*log10(sqrt(256)/16) = 20*log10(1) = 0 dB
        result = Physics.ris_coupling_loss_dB(0.4, 256, coupling_model='simplified')
        assert result == pytest.approx(2.0, rel=1e-6)

    def test_simplified_moderate_spacing(self):
        # spacing = 0.6 → spacing_loss = 1.0; N=256 → count_factor = 0
        result = Physics.ris_coupling_loss_dB(0.6, 256, coupling_model='simplified')
        assert result == pytest.approx(1.0, rel=1e-6)

    def test_simplified_wide_spacing(self):
        # spacing = 1.0 → spacing_loss = 0.1; N=256 → count_factor = 0
        result = Physics.ris_coupling_loss_dB(1.0, 256, coupling_model='simplified')
        assert result == pytest.approx(0.1, rel=1e-6)

    def test_simplified_count_factor_scales_with_n(self):
        # N=64 → sqrt(64)/16 = 0.5 → count_factor = 20*log10(0.5) ≈ -6.02 dB
        expected_count = 20 * np.log10(np.sqrt(64) / 16)
        result = Physics.ris_coupling_loss_dB(1.0, 64, coupling_model='simplified')
        assert result == pytest.approx(0.1 + expected_count, rel=1e-5)

    def test_detailed_model_returns_finite(self):
        result = Physics.ris_coupling_loss_dB(0.5, 16, coupling_model='detailed')
        assert np.isfinite(result)


# ---------------------------------------------------------------------------
# compute_channel_capacity_bps
# ---------------------------------------------------------------------------

class TestComputeChannelCapacity:
    def test_shannon_formula_known_value(self):
        # SNR = 0 dB → linear = 1 → C = B * log2(2) = B * 1
        bw = 20e6  # 20 MHz
        capacity = Physics.compute_channel_capacity_bps(0.0, bw)
        assert capacity == pytest.approx(bw, rel=1e-6)

    def test_doubling_snr_increases_capacity(self):
        bw = 10e6
        c_low = Physics.compute_channel_capacity_bps(10.0, bw)
        c_high = Physics.compute_channel_capacity_bps(20.0, bw)
        assert c_high > c_low

    def test_doubling_bandwidth_doubles_capacity(self):
        snr = 15.0
        c1 = Physics.compute_channel_capacity_bps(snr, 10e6)
        c2 = Physics.compute_channel_capacity_bps(snr, 20e6)
        assert c2 == pytest.approx(2 * c1, rel=1e-6)

    def test_negative_snr_gives_positive_capacity(self):
        # Even with SNR < 0 dB, Shannon capacity is positive (just small)
        capacity = Physics.compute_channel_capacity_bps(-10.0, 10e6)
        assert capacity > 0

    def test_high_snr_approximation(self):
        # High SNR: C ≈ B * SNR_dB / 10 * log2(10) ≈ B * 3.32 * (SNR_dB/10)
        # For 30 dB: SNR_linear=1000 → C = B*log2(1001) ≈ B*9.967
        bw = 1e6
        snr_linear = 10 ** (30.0 / 10)
        expected = bw * np.log2(1 + snr_linear)
        assert Physics.compute_channel_capacity_bps(30.0, bw) == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# validate_quantization_error
# ---------------------------------------------------------------------------

class TestValidateQuantizationError:
    def test_valid_quantization_passes(self):
        bits = 2
        ideal = np.array([0.0, np.pi / 2, np.pi, 3 * np.pi / 2])
        quantized = Physics.quantize_phase_to_bits(ideal, bits)
        result = Physics.validate_quantization_error(ideal, quantized, bits)
        assert result['status'] == 'valid'

    def test_result_contains_required_keys(self):
        bits = 3
        ideal = np.linspace(0, 2 * np.pi, 8, endpoint=False)
        quantized = Physics.quantize_phase_to_bits(ideal, bits)
        result = Physics.validate_quantization_error(ideal, quantized, bits)
        for key in ('status', 'max_error_deg', 'mean_error_deg', 'rms_error_deg', 'max_allowed_deg'):
            assert key in result

    def test_max_allowed_matches_theory(self):
        # max_allowed = phase_step/2 = (2π/2^bits)/2 in degrees
        bits = 2
        expected_max_deg = np.degrees(np.pi / (2 ** bits))
        ideal = np.zeros(4)
        quantized = np.zeros(4)
        result = Physics.validate_quantization_error(ideal, quantized, bits)
        assert result['max_allowed_deg'] == pytest.approx(expected_max_deg, rel=1e-6)

    def test_zero_error_passes(self):
        phases = np.array([0.0, np.pi, np.pi / 2])
        result = Physics.validate_quantization_error(phases, phases, bits=4)
        assert result['max_error_deg'] == pytest.approx(0.0, abs=1e-9)

    def test_excessive_error_raises(self):
        bits = 2
        ideal = np.array([0.0])
        # Force a large error (> phase_step/2)
        bad_quantized = np.array([np.pi])
        with pytest.raises(ValueError, match="exceeds"):
            Physics.validate_quantization_error(ideal, bad_quantized, bits)
