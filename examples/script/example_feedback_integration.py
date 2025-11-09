"""
Example: Automatic Feedback Integration in connect()
Demonstrates integrated AP-UE feedback loop (Option 3)
This mimics real hardware AP behavior exactly
"""
import sys
import json
import numpy as np

sys.path.insert(0, '/mnt/c/Users/Intel/Desktop/risnet')

from core import RISNetwork


def _to_float(value):
    """Safely convert scalars/arrays to float without numpy deprecation warnings."""
    arr = np.asarray(value)
    if arr.size == 0:
        raise ValueError("Cannot convert empty array to float")
    return float(arr.reshape(-1)[0].item())


def example_basic_without_feedback():
    """Example 1: Traditional connect() without feedback"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Traditional Connect (No Feedback)")
    print("="*70)

    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=18.0)
    net.add_ris('R1', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE1', 10, 0, 0)

    result = net.connect('AP1', 'R1', 'UE1')

    print(f"\nSingle transmission result:")
    print(f"  AP Power: {result['pwr_dBm']:.1f} dBm")
    print(f"  SNR: {result['snr_dB']:.1f} dB")
    print(f"  RIS Gain: {result['gain_dBi']:.1f} dBi")

    ap = net.get('AP1')
    print(f"\nAP State After (no adaptation):")
    print(f"  Power: {ap.power_dBm} dBm (unchanged)")
    print(f"  MCS: {ap.get_current_mcs()['name']} (unchanged)")


def example_with_automatic_feedback():
    """Example 2: Connect with automatic feedback (real hardware behavior)"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Connect with Automatic Feedback Loop")
    print("="*70)
    print("This mimics REAL HARDWARE AP behavior:")
    print("1. AP transmits")
    print("2. UE measures SNR")
    print("3. UE sends feedback to AP")
    print("4. AP adapts power & modulation")
    print("5. Repeat until convergence\n")

    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=15.0)
    net.add_ris('R1', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE1', 10, 0, 0)

    ap = net.get('AP1')
    print(f"Initial AP State:")
    print(f"  Power: {ap.power_dBm} dBm")
    print(f"  Target SNR: {ap.target_snr_dB} dB")
    print(f"  MCS: {ap.get_current_mcs()['name']}\n")

    result = net.connect('AP1', 'R1', 'UE1', enable_feedback=True, max_feedback_iterations=15)

    print(f"Feedback Loop Completed!\n")
    print(f"{'='*70}")
    print(f"FEEDBACK LOOP SUMMARY")
    print(f"{'='*70}\n")

    feedback_info = result.get('feedback_info', {})
    iterations = feedback_info.get('iterations', [])

    if iterations:
        print(f"{'Iter':<5} {'SNR(dB)':<12} {'Power(dBm)':<12} {'MCS':<18} {'Error(dB)':<10} {'Status':<12}")
        print("-" * 80)

        for it in iterations:
            snr = _to_float(it['measured_snr_dB'])
            power = _to_float(it['ap_power_dBm'])
            mcs = it['ap_mcs']
            error = _to_float(it['snr_error_dB'])
            status = "CONVERGED" if it['converged'] else "adapting"

            print(f"{it['iteration']:<5} {snr:>10.1f}  {power:>10.1f}  {mcs:<18} {error:>8.1f}  {status:<12}")

    print(f"\n{'='*70}")
    print(f"Final State After Feedback Loop:")
    print(f"  Converged: {feedback_info.get('converged')}")
    print(f"  Iterations: {feedback_info.get('num_iterations')}")
    final_power_dBm = _to_float(feedback_info.get('final_power_dBm', 0))
    final_snr_dB = _to_float(feedback_info.get('final_snr_dB', 0))
    print(f"  Final Power: {final_power_dBm:.1f} dBm")
    print(f"  Final MCS: {feedback_info.get('final_mcs')}")
    print(f"  Final SNR: {final_snr_dB:.1f} dB")

    efficiency = ap.get_current_mcs()['efficiency_bps_hz']
    print(f"  Spectral Efficiency: {efficiency:.1f} bits/Hz")

    print(f"\nTransmission Details:")
    initial_snr = _to_float(iterations[0]['measured_snr_dB'])
    final_power = _to_float(iterations[-1]['ap_power_dBm'])
    print(f"  Initial SNR: {initial_snr:.1f} dB")
    print(f"  Power Adjustment: {final_power - 15.0:.1f} dB")
    print(f"  MCS Improvement: {iterations[-1]['ap_mcs']} (from QPSK-3/4)")


def example_power_only():
    """Example 3: Power control only (rate adaptation disabled)"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Power Control Only (Feedback)")
    print("="*70)

    net = RISNetwork()
    net.add_ap('AP2', 0, 0, 0, power_dBm=16.0)
    net.add_ris('R2', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE2', 10, 0, 0)

    ap = net.get('AP2')
    ap.power_control_enabled = True
    ap.rate_adaptation_enabled = False

    print(f"Configuration:")
    print(f"  Power Control: Enabled")
    print(f"  Rate Adaptation: Disabled\n")

    result = net.connect('AP2', 'R2', 'UE2', enable_feedback=True, max_feedback_iterations=15)

    feedback_info = result.get('feedback_info', {})
    final_power_3 = _to_float(feedback_info.get('final_power_dBm', 0))
    print(f"Result:")
    print(f"  Converged: {feedback_info.get('converged')}")
    print(f"  Iterations: {feedback_info.get('num_iterations')}")
    print(f"  Power: {final_power_3:.1f} dBm")
    print(f"  MCS: {feedback_info.get('final_mcs')} (unchanged)")


def example_rate_only():
    """Example 4: Rate adaptation only (power control disabled)"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Rate Adaptation Only (Feedback)")
    print("="*70)

    net = RISNetwork()
    net.add_ap('AP3', 0, 0, 0, power_dBm=20.0)
    net.add_ris('R3', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE3', 10, 0, 0)

    ap = net.get('AP3')
    ap.power_control_enabled = False
    ap.rate_adaptation_enabled = True

    print(f"Configuration:")
    print(f"  Power Control: Disabled")
    print(f"  Rate Adaptation: Enabled\n")

    result = net.connect('AP3', 'R3', 'UE3', enable_feedback=True, max_feedback_iterations=15)

    feedback_info = result.get('feedback_info', {})
    final_power = _to_float(feedback_info.get('final_power_dBm', 0))
    print(f"Result:")
    print(f"  Converged: {feedback_info.get('converged')}")
    print(f"  Iterations: {feedback_info.get('num_iterations')}")
    print(f"  Power: {final_power:.1f} dBm (fixed)")
    print(f"  MCS: {feedback_info.get('final_mcs')}")


def main():
    """Run all examples"""
    print("\n" + "#"*70)
    print("# RISNet: Automatic Feedback Integration (Option 3)")
    print("# Mimics REAL HARDWARE AP behavior")
    print("#"*70)

    try:
        example_basic_without_feedback()
    except Exception as e:
        print(f"Error in Example 1: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_with_automatic_feedback()
    except Exception as e:
        print(f"Error in Example 2: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_power_only()
    except Exception as e:
        print(f"Error in Example 3: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_rate_only()
    except Exception as e:
        print(f"Error in Example 4: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "#"*70)
    print("# All examples completed!")
    print("#"*70 + "\n")


if __name__ == '__main__':
    main()
