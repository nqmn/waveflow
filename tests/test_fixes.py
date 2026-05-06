#!/usr/bin/env python3
"""
Test script to validate the fixes applied to address the review comments
"""
import numpy as np
from core import RISNetwork
from core.physics import Physics

def test_rx_power_calculation():
    """Test that Rx power calculation matches the reviewed math"""
    print("\n" + "="*70)
    print("TEST 1: Rx Power Calculation Validation")
    print("="*70)

    # Create network with reviewer's expected config
    # Reviewer mentioned 55780.2 linear = 47.465 dB for RIS gain
    # This corresponds to sqrt(55780.2) ≈ 236 elements, or about 15-16 per side
    # But they said "1-bit phase shifters" with specific RIS gain of 47.5 dB
    net = RISNetwork()
    net.add_ap("ap1", 0, 0, 0, power_dBm=20.0, freq=10e9)
    # Use 4x4 = 16 elements (reviewer's implied array size)
    net.add_ris("ris1", 5.0, 0, 0, N=4, bits=1)  # 1-bit quantizer, 4x4 = 16 elements
    net.add_ue("ue1", 5.0, 5.83, 0)

    # Get nodes
    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    # Manual calculation (reviewer's math)
    print("\n[Reviewer's Expected Values]")
    print(f"  Tx Power (Pt): 20.0 dBm")
    print(f"  AP antenna gain: 3.0 dBi")
    print(f"  UE antenna gain: 3.0 dBi")
    print(f"  Frequency: 10.0 GHz")
    print(f"  Wavelength: 0.03 m")

    # Path losses
    d_ap_ris = 5.00
    d_ris_ue = 5.83
    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, 10e9)
    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, 10e9)

    print(f"\n[Path Loss Calculations]")
    print(f"  FSPL @ {d_ap_ris:.2f} m: {pl_ap_ris:.3f} dB (expected: 66.421 dB)")
    print(f"  FSPL @ {d_ris_ue:.2f} m: {pl_ris_ue:.3f} dB (expected: 67.755 dB)")

    # RIS gain
    N = 8 * 8
    ris_gain = Physics.array_gain_dBi(N)
    print(f"\n[RIS Configuration]")
    print(f"  Array size: {N} elements")
    print(f"  Theoretical gain (20*log10(N)): {20*np.log10(N):.3f} dB")
    print(f"  Array gain (with losses): {ris_gain:.3f} dB")

    # Quantization loss (1-bit)
    quant_loss = Physics.quantization_loss_dB(1)
    print(f"\n[Quantization Loss (1-bit)]")
    print(f"  Loss value: {quant_loss:.4f} dB (negative = loss)")
    print(f"  |Loss| to subtract: {abs(quant_loss):.4f} dB")

    # Full link budget
    print(f"\n[Full Link Budget]")
    print(f"  Pr = Pt + G_AP + G_UE + G_RIS - PL_AP_RIS - PL_RIS_UE - |quant_loss|")
    pr_expected = 20 + 3 + 3 + ris_gain - pl_ap_ris - pl_ris_ue - abs(quant_loss)
    print(f"  Pr = 20 + 3 + 3 + {ris_gain:.3f} - {pl_ap_ris:.3f} - {pl_ris_ue:.3f} - {abs(quant_loss):.4f}")
    print(f"  Pr = {pr_expected:.2f} dBm (calculated)")

    # Now test with the fixed connect() method
    result = net.connect("ap1", "ris1", "ue1", seed=42, use_get_snr=False)

    print(f"\n[Fixed connect() Method Results]")
    print(f"  Rx Power: {result['pwr_dBm']:.2f} dBm")
    print(f"  SNR: {result['snr_dB']:.2f} dB")

    # Verify breakdown
    if '_breakdown' in result:
        bd = result['_breakdown']
        pr_calc = bd['tx_power_dBm'] + bd['ap_gain_dBi'] + bd['ue_gain_dBi'] + bd['ris_gain_dBi'] - bd['pl_ap_ris_dB'] - bd['pl_ris_ue_dB'] - bd['quant_loss_dB']
        print(f"\n[Breakdown Verification]")
        print(f"  Tx: {bd['tx_power_dBm']:.1f} dBm")
        print(f"  AP gain: {bd['ap_gain_dBi']:.1f} dBi")
        print(f"  UE gain: {bd['ue_gain_dBi']:.1f} dBi")
        print(f"  RIS gain: {bd['ris_gain_dBi']:.3f} dBi")
        print(f"  PL AP→RIS: -{bd['pl_ap_ris_dB']:.3f} dB")
        print(f"  PL RIS→UE: -{bd['pl_ris_ue_dB']:.3f} dB")
        print(f"  Quant loss: -{bd['quant_loss_dB']:.4f} dB")
        print(f"  Calculated Pr: {pr_calc:.2f} dBm")
        print(f"  Reported Pr: {result['pwr_dBm']:.2f} dBm")

    # SNR check
    noise_floor = -88.0
    snr_calc = pr_expected - noise_floor
    print(f"\n[SNR Validation]")
    print(f"  Noise floor: {noise_floor} dBm (100 MHz BW, 6 dB NF)")
    print(f"  Expected SNR: {snr_calc:.2f} dB")
    print(f"  Reported SNR: {result['snr_dB']:.2f} dB")
    print(f"  Match: {'✓' if abs(snr_calc - result['snr_dB']) < 1.0 else '✗'}")


def test_quantization_loss_convention():
    """Test that quantization loss uses consistent sign convention"""
    print("\n" + "="*70)
    print("TEST 2: Quantization Loss Sign Convention")
    print("="*70)

    print("\n[Testing Sign Convention]")
    print("  Quantization loss should be NEGATIVE (e.g., -1.67 dB for 1-bit)")
    print("  This indicates it reduces the RIS gain\n")

    for bits in [1, 2, 3]:
        loss = Physics.quantization_loss_dB(bits)
        print(f"  {bits}-bit: {loss:.4f} dB", end="")
        if loss < 0:
            print(f" (loss of {abs(loss):.4f} dB) ✓")
        else:
            print(f" ✗ SHOULD BE NEGATIVE")


def test_rms_phase_error():
    """Test RMS phase error with angle wrapping"""
    print("\n" + "="*70)
    print("TEST 3: RMS Phase Error with Angle Wrapping")
    print("="*70)

    print("\n[Testing Angle Wrapping]")
    print("  For 1-bit quantization (0° or 180°)")
    print("  Maximum unwrapped error would be 180°")
    print("  But with wrapping to [-180°, 180°], should wrap properly\n")

    # Simulate 1-bit quantization errors
    ideal_phases = np.array([10.0, 100.0, 200.0, 350.0])  # degrees
    quantized_phases = np.array([0.0, 90.0, 180.0, 0.0])  # 1-bit quantized

    # Convert to radians
    ideal_rad = np.radians(ideal_phases)
    quant_rad = np.radians(quantized_phases)

    # Compute error with wrapping
    error_raw = ideal_rad - quant_rad
    error_wrapped = np.angle(np.exp(1j * error_raw))

    error_deg_wrapped = np.degrees(error_wrapped)
    rms_error = np.degrees(np.sqrt(np.mean(error_wrapped**2)))

    print(f"  Ideal phases: {ideal_phases}")
    print(f"  Quantized phases: {quantized_phases}")
    print(f"  Wrapped errors (deg): {np.degrees(error_wrapped)}")
    print(f"  RMS error: {rms_error:.2f}°")
    print(f"  Expected range: 20-90° for 1-bit ✓" if 20 < rms_error < 100 else "  Unexpected RMS value ✗")


if __name__ == "__main__":
    test_rx_power_calculation()
    test_quantization_loss_convention()
    test_rms_phase_error()

    print("\n" + "="*70)
    print("All tests completed. Check results above for any ✗ marks.")
    print("="*70 + "\n")
