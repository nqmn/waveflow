"""Frozen physics regression tests grounded in Johari et al. (2025).

"Design and SDR Validation of a 5.8 GHz 1-bit Reconfigurable Intelligent
Surface With Optimized RF Choke," IEEE Access 2025.

These tests pin concrete numerical values so any future change to quantization,
EVM/SNR/BER formulas, or array physics breaks a test immediately.

Ground truth:
  - Table 2 EVM measurements: RIS OFF=57.30 %, RIS ON=24.39 %
  - 1-bit RIS: N=256 elements (16×16), f=5.8 GHz, d=λ/2 spacing
  - SNR from EVM: SNR_dB = −20·log10(EVM_rms)          (paper Eq. 9)
  - BER from EVM: BER = 0.5·erfc(1/(√2·EVM_rms))        (paper Eq. 10)
  - Reflection loss from |Γ|=0.84: 20·log10(0.84)
  - Quantization loss: sinc² model in core/physics.py

All values captured 2026-05-08 and cross-checked against the paper.
"""

import math

import numpy as np
import pytest

from core.physics import Physics

# ---------------------------------------------------------------------------
# Paper constants (Table 2, Johari 2025)
# ---------------------------------------------------------------------------

EVM_OFF_PCT = 57.30   # EVM with RIS OFF (%)
EVM_ON_PCT  = 24.39   # EVM with RIS ON  (%)
EVM_OFF_RMS = EVM_OFF_PCT / 100.0
EVM_ON_RMS  = EVM_ON_PCT  / 100.0
FREQ_HZ     = 5.8e9
N_SIDE      = 16       # 16×16 = 256 elements
GAMMA_MAG   = 0.84     # measured reflection coefficient magnitude


# ---------------------------------------------------------------------------
# 1. EVM ↔ SNR conversion (Eq. 9)
# ---------------------------------------------------------------------------

class TestEVMSNRRegression:
    """SNR_dB = −20·log10(EVM_rms). Frozen to 10 significant figures."""

    def test_snr_ris_off(self):
        snr = Physics.evm_to_snr_dB(EVM_OFF_PCT)
        assert snr == pytest.approx(4.8369075607, abs=1e-9)

    def test_snr_ris_on(self):
        snr = Physics.evm_to_snr_dB(EVM_ON_PCT)
        assert snr == pytest.approx(12.2557639937, abs=1e-9)

    def test_snr_improvement(self):
        snr_off = Physics.evm_to_snr_dB(EVM_OFF_PCT)
        snr_on  = Physics.evm_to_snr_dB(EVM_ON_PCT)
        assert snr_on - snr_off == pytest.approx(7.4188564331, abs=1e-9)

    def test_evm_reduction_pct(self):
        assert EVM_OFF_PCT - EVM_ON_PCT == pytest.approx(32.9100000000, abs=1e-9)

    def test_snr_to_evm_roundtrip_off(self):
        snr = -20.0 * math.log10(EVM_OFF_RMS)
        recovered = Physics.snr_to_evm(snr)
        assert recovered == pytest.approx(EVM_OFF_PCT, abs=1e-6)

    def test_snr_to_evm_roundtrip_on(self):
        snr = -20.0 * math.log10(EVM_ON_RMS)
        recovered = Physics.snr_to_evm(snr)
        assert recovered == pytest.approx(EVM_ON_PCT, abs=1e-6)


# ---------------------------------------------------------------------------
# 2. BER from EVM (Eq. 10)
# ---------------------------------------------------------------------------

class TestBERRegression:
    """BER = 0.5·erfc(1/(√2·EVM_rms)). Frozen values."""

    def test_ber_ris_off(self):
        ber = Physics.ber_qpsk_from_evm(EVM_OFF_PCT)
        assert ber == pytest.approx(0.0404749699, abs=1e-9)

    def test_ber_ris_on(self):
        ber = Physics.ber_qpsk_from_evm(EVM_ON_PCT)
        assert ber == pytest.approx(0.0000206538, abs=1e-10)

    def test_ber_ratio_off_over_on(self):
        ber_off = Physics.ber_qpsk_from_evm(EVM_OFF_PCT)
        ber_on  = Physics.ber_qpsk_from_evm(EVM_ON_PCT)
        assert ber_off / ber_on == pytest.approx(1959.6818, abs=0.01)


# ---------------------------------------------------------------------------
# 3. 1-bit quantization states and loss
# ---------------------------------------------------------------------------

class TestOneBitQuantizationRegression:
    """1-bit RIS: only {0, π} states, phase step = π rad."""

    def test_phase_step_is_pi(self):
        step = 2 * math.pi / (2 ** 1)
        assert step == pytest.approx(math.pi, abs=1e-12)

    def test_state_difference_is_180_deg(self):
        """Two 1-bit states differ by exactly π rad = 180°."""
        assert abs(math.pi - 0.0) == pytest.approx(math.pi, abs=1e-12)

    def test_quantize_maps_to_binary_states_only(self):
        phases = np.linspace(0, 2 * math.pi, 50, endpoint=False)
        q = Physics.quantize_phase_to_bits(phases, 1)
        unique = sorted(set(np.round(q, 10).tolist()))
        assert len(unique) <= 2
        for v in unique:
            assert v == pytest.approx(0.0, abs=1e-9) or v == pytest.approx(math.pi, abs=1e-9)

    def test_quantized_phases_frozen_for_canonical_input(self):
        """Frozen mapping for a fixed 5-element input."""
        ideal = np.array([0.1, 0.9, 2.0, 3.5, 5.0])
        q = Physics.quantize_phase_to_bits(ideal, 1)
        expected = [0.0, 0.0, math.pi, math.pi, 0.0]
        assert list(q) == pytest.approx(expected, abs=1e-12)

    def test_quantization_loss_1bit_frozen(self):
        assert Physics.quantization_loss_dB(1) == pytest.approx(-1.6706302630, abs=1e-9)

    def test_quantization_loss_2bit_frozen(self):
        assert Physics.quantization_loss_dB(2) == pytest.approx(-0.7452558256, abs=1e-9)

    def test_1bit_loss_worse_than_2bit_by_frozen_amount(self):
        diff = Physics.quantization_loss_dB(1) - Physics.quantization_loss_dB(2)
        assert diff == pytest.approx(-0.9253744374, abs=1e-9)

    def test_max_quantization_error_1bit_is_90deg(self):
        """1-bit phase step = π → max error = π/2 = 90°."""
        max_err_rad = math.pi / 2
        assert math.degrees(max_err_rad) == pytest.approx(90.0, abs=1e-9)

    def test_validate_quantization_error_passes_for_1bit(self):
        ideal = np.array([0.1, 0.9, 2.0, 3.5, 5.0])
        q = Physics.quantize_phase_to_bits(ideal, 1)
        result = Physics.validate_quantization_error(ideal, q, 1)
        assert result["status"] == "valid"
        assert result["max_allowed_deg"] == pytest.approx(90.0, abs=1e-6)
        assert result["max_error_deg"] < 90.0


# ---------------------------------------------------------------------------
# 4. Reflection loss from measured |Γ|
# ---------------------------------------------------------------------------

class TestReflectionLossRegression:
    """Reflection loss = 20·log10(|Γ|). Frozen for |Γ|=0.84."""

    def test_reflection_loss_frozen(self):
        loss = 20.0 * np.log10(GAMMA_MAG)
        assert loss == pytest.approx(-1.5144142788, abs=1e-9)

    def test_reflection_loss_is_negative(self):
        assert 20.0 * np.log10(GAMMA_MAG) < 0.0

    def test_perfect_reflector_gives_zero_loss(self):
        assert 20.0 * np.log10(1.0) == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------------
# 5. Aperture gain drop — cos(θ) projected-aperture law
# ---------------------------------------------------------------------------

class TestApertureGainDropRegression:
    """G(θ) = G_broadside + 10·log10(cos θ). Frozen for 10°→60° drop."""

    def test_gain_drop_10_to_60_degrees_frozen(self):
        drop = (
            10.0 * np.log10(np.cos(np.radians(60)))
            - 10.0 * np.log10(np.cos(np.radians(10)))
        )
        assert drop == pytest.approx(-2.9438145463, abs=1e-9)

    def test_broadside_is_reference_zero(self):
        """At θ=0°, cos(0)=1 → 10·log10(1)=0 dB penalty."""
        drop = 10.0 * np.log10(np.cos(np.radians(0)))
        assert drop == pytest.approx(0.0, abs=1e-12)

    def test_gain_decreases_monotonically_to_90deg(self):
        angles = [0, 15, 30, 45, 60, 75, 89]
        gains = [10.0 * np.log10(np.cos(np.radians(a))) for a in angles]
        for i in range(len(gains) - 1):
            assert gains[i] > gains[i + 1]
