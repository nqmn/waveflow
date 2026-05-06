"""Physics validation test suite for the `testphysics` CLI command."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from core.physics import Physics, C


# ---------------------------------------------------------------------------
# Data structures (reuse the same shape as test_suite.py)
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str

    def render(self) -> str:
        icon = "✓" if self.passed else "✗"
        return f"    {icon} {self.name}: {self.detail}"


@dataclass
class SectionResult:
    title: str
    checks: List[CheckResult] = field(default_factory=list)
    extra_lines: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def render(self, idx: int, total: int) -> str:
        icon = "✓" if self.passed else "✗"
        header = f"[{idx}/{total}] {icon} {self.title}"
        body_lines = [c.render() for c in self.checks] + self.extra_lines
        return header + "\n" + "\n".join(body_lines)


@dataclass
class PhysicsSuiteResults:
    sections: List[SectionResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(s.passed for s in self.sections)

    def format_text(self) -> str:
        total = len(self.sections)
        parts = [s.render(i + 1, total) for i, s in enumerate(self.sections)]
        summary = "✓ All physics checks passed!" if self.all_passed else "✗ Some checks FAILED — see above."
        return "\n".join(parts) + f"\n\n{summary}"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _check(name: str, expr: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, passed=expr, detail=detail)


def _approx(actual: float, expected: float, tol: float = 0.01) -> bool:
    return abs(actual - expected) <= tol


# ---------------------------------------------------------------------------
# Section runners
# ---------------------------------------------------------------------------

def _section_path_loss() -> SectionResult:
    sec = SectionResult("Free-Space Path Loss (FSPL)")

    # FSPL formula: 20*log10(4πdf/c)
    # d=10 m, f=10 GHz → expected
    d, f = 10.0, 10e9
    expected = 20 * np.log10(4 * np.pi * d * f / C)
    actual = Physics.path_loss_dB(d, f)
    sec.checks.append(_check(
        "10 m, 10 GHz", _approx(actual, expected, 0.01),
        f"{actual:.3f} dB (expected {expected:.3f} dB)"
    ))

    # d=100 m → +20 dB from d=10 m
    pl_10 = Physics.path_loss_dB(10, f)
    pl_100 = Physics.path_loss_dB(100, f)
    delta = pl_100 - pl_10
    sec.checks.append(_check(
        "Double-distance rule (+20 dB per decade)", _approx(delta, 20.0, 0.01),
        f"delta = {delta:.3f} dB"
    ))

    # Zero/negative distance edge
    sec.checks.append(_check(
        "d=0 returns 0", Physics.path_loss_dB(0, f) == 0.0,
        f"{Physics.path_loss_dB(0, f):.3f} dB"
    ))

    return sec


def _section_atmospheric_loss() -> SectionResult:
    sec = SectionResult("Atmospheric Absorption Loss")

    # Below 10 GHz: alpha=0.00001, d=1000 m → 0.01 dB
    actual = Physics.atmospheric_loss_dB(1000, 5.0)
    sec.checks.append(_check(
        "5 GHz / 1 km default alpha", _approx(actual, 0.01, 1e-6),
        f"{actual:.6f} dB (expected 0.010000 dB)"
    ))

    # 17 GHz: alpha = 0.0001+(7*0.00002)=0.00024, d=500 m → 0.12 dB
    actual = Physics.atmospheric_loss_dB(500, 17.0)
    sec.checks.append(_check(
        "17 GHz / 500 m band interpolation", _approx(actual, 0.12, 1e-6),
        f"{actual:.6f} dB (expected 0.120000 dB)"
    ))

    # 60 GHz oxygen peak: alpha=0.015, d=100 m → 1.5 dB
    actual = Physics.atmospheric_loss_dB(100, 60.0)
    sec.checks.append(_check(
        "60 GHz oxygen peak / 100 m", _approx(actual, 1.5, 1e-6),
        f"{actual:.6f} dB (expected 1.500000 dB)"
    ))

    # Linear with distance
    loss_1k = Physics.atmospheric_loss_dB(1000, 5.0)
    loss_2k = Physics.atmospheric_loss_dB(2000, 5.0)
    sec.checks.append(_check(
        "Loss scales linearly with distance", _approx(loss_2k, 2 * loss_1k, 1e-9),
        f"1km={loss_1k:.5f} dB, 2km={loss_2k:.5f} dB"
    ))

    return sec


def _section_rician_fading() -> SectionResult:
    sec = SectionResult("Rician Fading Channel")

    # High K → magnitude approaches 1
    np.random.seed(0)
    samples = [Physics.rician_fading(30.0) for _ in range(500)]
    mean_hi_k = float(np.mean(samples))
    sec.checks.append(_check(
        "High K-factor (30 dB) mean ≈ 1.0", abs(mean_hi_k - 1.0) < 0.05,
        f"mean = {mean_hi_k:.4f}"
    ))

    # Returned value must be positive
    np.random.seed(1)
    val = Physics.rician_fading(10.0)
    sec.checks.append(_check(
        "Output is positive magnitude", val > 0,
        f"value = {val:.4f}"
    ))

    # size>1 returns array of correct length
    np.random.seed(2)
    arr = Physics.rician_fading(10.0, size=64)
    sec.checks.append(_check(
        "size=64 returns 64-element array, all positive",
        len(arr) == 64 and bool(np.all(arr > 0)),
        f"len={len(arr)}, min={np.min(arr):.4f}"
    ))

    return sec


def _section_mutual_coupling() -> SectionResult:
    sec = SectionResult("Mutual Coupling Penalty")

    cases: List[Tuple[float, float, str]] = [
        (0.3, 2.0, "spacing=0.3λ → 2.0 dB"),
        (0.5, 2.0, "spacing=0.5λ → 2.0 dB (boundary)"),
        (0.6, 1.0, "spacing=0.6λ → 1.0 dB"),
        (0.7, 1.0, "spacing=0.7λ → 1.0 dB (boundary)"),
        (1.0, 0.0, "spacing=1.0λ → 0.0 dB"),
    ]
    for spacing, expected, label in cases:
        actual = Physics.mutual_coupling_penalty(spacing)
        sec.checks.append(_check(label, _approx(actual, expected, 1e-9), f"{actual:.1f} dB"))

    # Disabled → 0
    actual_off = Physics.mutual_coupling_penalty(0.3, coupling_enabled=False)
    sec.checks.append(_check(
        "coupling_enabled=False → 0.0 dB", actual_off == 0.0, f"{actual_off:.1f} dB"
    ))

    return sec


def _section_quantization_loss_with_state() -> SectionResult:
    sec = SectionResult("Quantization Loss with State Variation")

    # Even state (idx=0) → no variation, equals base loss
    base = Physics.quantization_loss_dB(2)
    state_even = Physics.quantization_loss_with_state(2, 0.0)
    sec.checks.append(_check(
        "State 0 (even) matches base loss", _approx(state_even, base, 1e-9),
        f"state_even={state_even:.4f} dB, base={base:.4f} dB"
    ))

    # Odd state (idx=1) → base + 0.2 dB
    state_odd = Physics.quantization_loss_with_state(2, 0.25)
    sec.checks.append(_check(
        "State 1 (odd) = base + 0.2 dB", _approx(state_odd, base + 0.2, 1e-9),
        f"state_odd={state_odd:.4f} dB, expected={base+0.2:.4f} dB"
    ))

    # Result must be negative (loss)
    sec.checks.append(_check(
        "Loss value is negative (dB)", state_even < 0,
        f"{state_even:.4f} dB"
    ))

    # 0-bit: no loss
    sec.checks.append(_check(
        "0-bit returns 0.0 dB", Physics.quantization_loss_with_state(0, 0.0) == 0.0,
        "0.0 dB"
    ))

    return sec


def _section_phase_error_per_element() -> SectionResult:
    sec = SectionResult("Per-Element Phase Error Model")

    # Quantization-only: bounded by ±π/(2^bits)/2
    bits = 2
    bound = np.pi / (2 ** bits) / 2
    errors = [
        Physics.phase_error_per_element(i, 16, bits,
                                        include_manufacturing=False,
                                        include_temperature=False,
                                        seed=i)
        for i in range(8)
    ]
    all_bounded = all(abs(e) <= bound + 1e-9 for e in errors)
    sec.checks.append(_check(
        f"Quant-only error within ±{np.degrees(bound):.2f}°", all_bounded,
        f"max observed = {np.degrees(max(abs(e) for e in errors)):.3f}°"
    ))

    # No sources → zero
    err0 = Physics.phase_error_per_element(
        0, 16, 2,
        include_quantization=False,
        include_manufacturing=False,
        include_temperature=False,
        seed=0
    )
    sec.checks.append(_check(
        "All sources disabled → 0.0 rad", err0 == 0.0,
        f"{err0:.6f} rad"
    ))

    # Seeded reproducibility
    e1 = Physics.phase_error_per_element(3, 16, 2, seed=99)
    e2 = Physics.phase_error_per_element(3, 16, 2, seed=99)
    sec.checks.append(_check(
        "Same seed gives identical result", e1 == e2,
        f"{e1:.6f} rad"
    ))

    return sec


def _section_quantized_beam_angle() -> SectionResult:
    sec = SectionResult("Quantized Beam Angle Resolution")

    # 0 bits → passthrough
    angle, err = Physics.compute_quantized_beam_angle(37.5, 0, 16)
    sec.checks.append(_check(
        "0 bits → ideal angle unchanged", angle == 37.5 and err == 0.0,
        f"angle={angle:.2f}°, err={err:.4f}°"
    ))

    # Error must equal ideal - achievable
    ideal = 25.0
    angle, err = Physics.compute_quantized_beam_angle(ideal, 3, 16)
    sec.checks.append(_check(
        "Error = ideal − achievable", _approx(err, ideal - angle, 1e-9),
        f"ideal={ideal}°, achievable={angle:.4f}°, err={err:.4f}°"
    ))

    # More bits → smaller or equal error
    _, e2 = Physics.compute_quantized_beam_angle(22.5, 2, 16)
    _, e4 = Physics.compute_quantized_beam_angle(22.5, 4, 16)
    sec.checks.append(_check(
        "Higher bit count ≤ error of lower bit count", abs(e4) <= abs(e2) + 1e-9,
        f"2-bit err={abs(e2):.4f}°, 4-bit err={abs(e4):.4f}°"
    ))

    return sec


def _section_angle_loss() -> SectionResult:
    sec = SectionResult("Angle-Loss Beam Penalty")

    # Zero deviation → 0 dB
    v = Physics.angle_loss_dB(30.0, 30.0)
    sec.checks.append(_check("0° deviation → 0.0 dB", v == 0.0, f"{v:.4f} dB"))

    # ±60° → exactly −40 dB
    v = Physics.angle_loss_dB(90.0, 30.0)
    sec.checks.append(_check("60° deviation → −40.0 dB", _approx(v, -40.0, 0.01), f"{v:.4f} dB"))

    # Clamped at −60 dB
    v = Physics.angle_loss_dB(0.0, 180.0)
    sec.checks.append(_check("180° deviation clamped to −60 dB", v == -60.0, f"{v:.1f} dB"))

    # Symmetric: +θ = −θ
    loss_p = Physics.angle_loss_dB(45.0, 0.0)
    loss_m = Physics.angle_loss_dB(-45.0, 0.0)
    sec.checks.append(_check(
        "Symmetric: +45° = −45° offset", _approx(loss_p, loss_m, 1e-9),
        f"+45°={loss_p:.4f} dB, −45°={loss_m:.4f} dB"
    ))

    # Wraps through 360°
    loss_wrap = Physics.angle_loss_dB(350.0, 10.0)
    loss_direct = Physics.angle_loss_dB(-10.0, 10.0)
    sec.checks.append(_check(
        "Wraps correctly: 350° vs 10° = −10° vs 10°",
        _approx(loss_wrap, loss_direct, 1e-9),
        f"wrap={loss_wrap:.4f} dB, direct={loss_direct:.4f} dB"
    ))

    return sec


def _section_snr_evm() -> SectionResult:
    sec = SectionResult("SNR → EVM Conversion")

    cases: List[Tuple[float, float, str]] = [
        (0.0,  100.0, "SNR=0 dB  → EVM=100%"),
        (20.0,  10.0, "SNR=20 dB → EVM=10%"),
        (40.0,   1.0, "SNR=40 dB → EVM=1%"),
    ]
    for snr_dB, expected_pct, label in cases:
        actual = Physics.snr_to_evm(snr_dB)
        sec.checks.append(_check(label, _approx(actual, expected_pct, 0.001), f"{actual:.4f}%"))

    # Monotonic: higher SNR → lower EVM
    evm_low = Physics.snr_to_evm(10.0)
    evm_high = Physics.snr_to_evm(30.0)
    sec.checks.append(_check(
        "Monotonic: higher SNR → lower EVM", evm_high < evm_low,
        f"SNR=10 dB → {evm_low:.2f}%, SNR=30 dB → {evm_high:.2f}%"
    ))

    return sec


def _section_multipath_ris_gain() -> SectionResult:
    sec = SectionResult("Multipath RIS Gain")

    # All-zero phases, amplitude=1 → coherent sum → gain ≈ 0 dB
    N = 16
    phases = np.zeros(N)
    gain = Physics.multipath_ris_gain([{'amplitude': 1.0, 'phase': 0.0}], phases)
    sec.checks.append(_check(
        "Coherent zero-phases, amp=1 → gain ≈ 0 dB", abs(gain) < 0.5,
        f"{gain:.4f} dB"
    ))

    # Two identical paths → more total power than one
    gain_1 = Physics.multipath_ris_gain([{'amplitude': 1.0}], phases)
    gain_2 = Physics.multipath_ris_gain([{'amplitude': 1.0}, {'amplitude': 1.0}], phases)
    sec.checks.append(_check(
        "Two equal paths > one path (power)", gain_2 > gain_1,
        f"1 path={gain_1:.3f} dB, 2 paths={gain_2:.3f} dB"
    ))

    # Zero amplitude → near -inf dB floor
    gain_zero = Physics.multipath_ris_gain([{'amplitude': 0.0}], phases)
    sec.checks.append(_check(
        "Zero-amplitude path → very low gain", gain_zero < -90,
        f"{gain_zero:.2f} dB"
    ))

    return sec


def _section_effective_snr() -> SectionResult:
    sec = SectionResult("Effective SNR with Waveform Distortion")

    # quant_error=0, papr=8 dB, eq=0.5 dB → 30 - 1.6 - 0.5 = 27.9 dB
    result = Physics.effective_snr_with_waveform_distortion(30.0, 0.0, papr_dB=8.0,
                                                             equalization_error_dB=0.5)
    sec.checks.append(_check(
        "No quant error: 30 dB → 27.9 dB", _approx(result, 27.9, 0.01),
        f"{result:.4f} dB"
    ))

    # Effective always ≤ ideal
    eff = Physics.effective_snr_with_waveform_distortion(25.0, 15.0)
    sec.checks.append(_check(
        "Effective SNR ≤ ideal SNR", eff < 25.0,
        f"ideal=25.0 dB, effective={eff:.3f} dB"
    ))

    # Larger quant error → lower SNR
    snr_small = Physics.effective_snr_with_waveform_distortion(20.0, 5.0)
    snr_large = Physics.effective_snr_with_waveform_distortion(20.0, 30.0)
    sec.checks.append(_check(
        "Larger quant error → lower effective SNR", snr_large < snr_small,
        f"5°={snr_small:.3f} dB, 30°={snr_large:.3f} dB"
    ))

    return sec


def _section_ris_coupling_loss() -> SectionResult:
    sec = SectionResult("RIS Coupling & Mismatch Loss")

    # Simplified: N=256 (count_factor=0), spacing=0.4 → 2.0 dB
    r = Physics.ris_coupling_loss_dB(0.4, 256)
    sec.checks.append(_check(
        "Tight spacing (0.4λ), N=256 → 2.0 dB", _approx(r, 2.0, 1e-6), f"{r:.4f} dB"
    ))

    # N=64 → count_factor = 20*log10(8/16) = 20*log10(0.5) ≈ −6.02 dB
    count_factor = 20 * np.log10(np.sqrt(64) / 16)
    expected = 0.1 + count_factor
    r = Physics.ris_coupling_loss_dB(1.0, 64)
    sec.checks.append(_check(
        "Wide spacing (1.0λ), N=64 count scaling", _approx(r, expected, 1e-5),
        f"{r:.4f} dB (expected {expected:.4f} dB)"
    ))

    # Detailed model → finite number
    r_det = Physics.ris_coupling_loss_dB(0.5, 16, coupling_model='detailed')
    sec.checks.append(_check(
        "Detailed model returns finite value", np.isfinite(r_det),
        f"{r_det:.4f} dB"
    ))

    return sec


def _section_channel_capacity() -> SectionResult:
    sec = SectionResult("Shannon Channel Capacity")

    # SNR=0 dB → C = B * log2(2) = B
    bw = 20e6
    cap = Physics.compute_channel_capacity_bps(0.0, bw)
    sec.checks.append(_check(
        "SNR=0 dB → C = BW (20 Mbps)", _approx(cap, bw, 1.0),
        f"{cap/1e6:.4f} Mbps (expected {bw/1e6:.1f} Mbps)"
    ))

    # Doubling BW → doubles capacity
    c1 = Physics.compute_channel_capacity_bps(15.0, 10e6)
    c2 = Physics.compute_channel_capacity_bps(15.0, 20e6)
    sec.checks.append(_check(
        "Doubling BW doubles capacity", _approx(c2, 2 * c1, 1.0),
        f"10 MHz={c1/1e6:.3f} Mbps, 20 MHz={c2/1e6:.3f} Mbps"
    ))

    # Higher SNR → higher capacity
    c_low = Physics.compute_channel_capacity_bps(10.0, 10e6)
    c_high = Physics.compute_channel_capacity_bps(20.0, 10e6)
    sec.checks.append(_check(
        "Higher SNR → higher capacity", c_high > c_low,
        f"SNR=10 dB → {c_low/1e6:.2f} Mbps, SNR=20 dB → {c_high/1e6:.2f} Mbps"
    ))

    # Analytic spot check: SNR=30 dB
    snr_lin = 10 ** (30.0 / 10)
    expected = 1e6 * np.log2(1 + snr_lin)
    actual = Physics.compute_channel_capacity_bps(30.0, 1e6)
    sec.checks.append(_check(
        "SNR=30 dB / 1 MHz matches Shannon formula", _approx(actual, expected, 1.0),
        f"{actual/1e6:.4f} Mbps (expected {expected/1e6:.4f} Mbps)"
    ))

    return sec


def _section_validate_quantization() -> SectionResult:
    sec = SectionResult("Quantization Error Validation")

    # Valid: quantize then validate
    for bits in (1, 2, 3):
        ideal = np.linspace(0, 2 * np.pi, 2 ** bits, endpoint=False)
        quantized = Physics.quantize_phase_to_bits(ideal, bits)
        try:
            result = Physics.validate_quantization_error(ideal, quantized, bits)
            passed = result['status'] == 'valid'
            detail = f"max_err={result['max_error_deg']:.3f}°, allowed={result['max_allowed_deg']:.3f}°"
        except Exception as exc:
            passed, detail = False, str(exc)
        sec.checks.append(_check(f"{bits}-bit valid quantization passes", passed, detail))

    # Invalid: force large error → must raise
    try:
        Physics.validate_quantization_error(np.array([0.0]), np.array([np.pi]), bits=2)
        sec.checks.append(_check("Excess error raises ValueError", False, "no exception raised"))
    except ValueError:
        sec.checks.append(_check("Excess error raises ValueError", True, "ValueError raised"))

    # max_allowed matches theory: phase_step/2 in degrees
    bits = 2
    expected_max_deg = np.degrees(np.pi / (2 ** bits))
    ideal = np.zeros(4)
    result = Physics.validate_quantization_error(ideal, ideal, bits)
    sec.checks.append(_check(
        "max_allowed_deg matches theory", _approx(result['max_allowed_deg'], expected_max_deg, 1e-6),
        f"{result['max_allowed_deg']:.4f}° (expected {expected_max_deg:.4f}°)"
    ))

    return sec


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_testphysics() -> PhysicsSuiteResults:
    """Run the full physics validation suite and return structured results."""
    suite = PhysicsSuiteResults()
    suite.sections = [
        _section_path_loss(),
        _section_atmospheric_loss(),
        _section_rician_fading(),
        _section_mutual_coupling(),
        _section_quantization_loss_with_state(),
        _section_phase_error_per_element(),
        _section_quantized_beam_angle(),
        _section_angle_loss(),
        _section_snr_evm(),
        _section_multipath_ris_gain(),
        _section_effective_snr(),
        _section_ris_coupling_loss(),
        _section_channel_capacity(),
        _section_validate_quantization(),
    ]
    return suite
