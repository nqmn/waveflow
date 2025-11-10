#!/usr/bin/env python3
"""
Example: Full Waveform Integration with UE Receiver Pipeline

Demonstrates the fully integrated waveform-level RIS network simulation where:
1. AP generates OFDM signal
2. AP → RIS propagation with multipath
3. RIS reflects with phase quantization and coupling
4. RIS → UE propagation
5. UE runs full receiver pipeline (OFDM demod, channel est, equalization)
6. UE generates CSI feedback
7. AP adapts power/MCS based on feedback (closed-loop)

This replaces the manual/separate waveform simulation with a unified integrated flow.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
from core import RISNetwork
from controller.waveform_controller import WaveformController


def example_full_cascade_basic():
    """Example 1: Basic full cascade simulation"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Full Cascade Waveform Simulation (No Feedback)")
    print("="*80)

    # Setup network
    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=20, freq=10e9, bandwidth_MHz=100)
    net.add_ris('R1', 5, 0, 0, N=8, bits=2, freq=10e9)
    net.add_ue('UE1', 10, 0, 0)

    print("\nNetwork Configuration:")
    print(f"  AP1: (0, 0, 0) - TX power: 20 dBm")
    print(f"  R1:  (5, 0, 0) - 8×8 grid, 2-bit phase shifters")
    print(f"  UE1: (10, 0, 0) - Receiver")

    # Create waveform controller
    controller = WaveformController(net, net.environment)
    controller.set_ofdm_config(
        bandwidth=100e6,  # 100 MHz
        num_subcarriers=256,
        center_freq=10e9
    )

    print("\nOFDM Configuration:")
    print(f"  Bandwidth: 100 MHz")
    print(f"  Subcarriers: 256")
    print(f"  Symbols: 10")

    # Run full cascade (no feedback)
    print("\n" + "-"*80)
    print("Running Full Cascade Simulation...")
    print("-"*80)

    result = controller.simulate_full_cascade(
        'AP1', 'R1', 'UE1',
        num_symbols=10,
        enable_feedback=False
    )

    # Display results
    print(f"\n[STEP 1] AP generates OFDM signal with PAPR: {result['papr_dB']:.2f} dB")
    print(f"[STEP 2] AP → RIS propagation (multipath)")
    print(f"[STEP 3] RIS reflection:")
    print(f"         Ideal phases: {len(result['ris_ideal_phases'])} elements")
    print(f"         Quantized phases: {len(result['ris_quantized_phases'])} elements")
    print(f"         Phase error RMS: {result['ris_phase_error_rms_deg']:.2f}°")
    print(f"[STEP 4] RIS → UE propagation (multipath)")
    print(f"[STEP 5] UE receiver pipeline:")
    print(f"         - CP removal & FFT")
    print(f"         - Channel estimation from {len(result['pilot_indices'])} pilots")
    print(f"         - Zero-forcing equalization")
    print(f"         - SNR measurement from equalized symbols")
    print(f"\nReceived SNR: {result['snr_dB']:.2f} dB")

    # CSI feedback details
    csi = result['csi_feedback']
    print(f"\nCSI Feedback Generated:")
    print(f"  UE: {csi['ue_name']}")
    print(f"  Measured SNR: {csi['snr_dB']:.2f} dB")
    print(f"  Pilot reliability: {csi.get('pilot_reliability', 0):.2%}")
    print(f"  Channel estimate shape: {csi['channel_estimate'].shape}")

    return net, result


def example_full_cascade_with_feedback():
    """Example 2: Full cascade with closed-loop feedback"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Full Cascade with Closed-Loop Feedback")
    print("="*80)

    # Setup network
    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=20, freq=10e9, bandwidth_MHz=100)
    net.add_ris('R1', 5, 1, 0, N=8, bits=2, freq=10e9)
    net.add_ue('UE1', 10, 2, 0)

    print("\nNetwork Configuration:")
    print(f"  AP1: (0, 0, 0) - TX power: 20 dBm, target SNR: 20 dB")
    print(f"  R1:  (5, 1, 0) - 8×8 grid, 2-bit phase shifters")
    print(f"  UE1: (10, 2, 0) - Receiver with feedback capability")

    # Create controller
    controller = WaveformController(net, net.environment)
    controller.set_ofdm_config(bandwidth=100e6, num_subcarriers=256, center_freq=10e9)

    print("\n" + "-"*80)
    print("Running Full Cascade with Feedback...")
    print("-"*80)

    # Run with feedback enabled
    result = controller.simulate_full_cascade(
        'AP1', 'R1', 'UE1',
        num_symbols=5,  # Faster with fewer symbols
        enable_feedback=True,
        max_feedback_iterations=3
    )

    # Display cascade result
    print(f"\n[INITIAL TRANSMISSION]")
    print(f"  Measured SNR: {result['snr_dB']:.2f} dB")
    print(f"  Phase error: {result['ris_phase_error_rms_deg']:.2f}°")

    # Display feedback loop
    if 'feedback_info' in result:
        fb = result['feedback_info']
        print(f"\n[CLOSED-LOOP FEEDBACK]")
        print(f"  Iterations: {fb['num_iterations']}")
        print(f"  Converged: {fb['converged']}")

        for i, iter_info in enumerate(fb['iterations']):
            print(f"\n  Iteration {i}:")
            print(f"    Measured SNR: {iter_info['measured_snr_dB']:.2f} dB")
            print(f"    AP power: {iter_info['ap_power_dBm']:.1f} dBm")
            print(f"    AP MCS: {iter_info['ap_mcs']}")
            print(f"    SNR error: {iter_info['snr_error_dB']:.2f} dB")

            if iter_info['control_action'].get('status') == 'updated':
                ca = iter_info['control_action']
                print(f"    → Power adjusted: {ca['old_power_dBm']:.1f} → {ca['new_power_dBm']:.1f} dBm")

        print(f"\n  Final state:")
        print(f"    SNR: {fb['final_snr_dB']:.2f} dB")
        print(f"    Power: {fb['final_power_dBm']:.1f} dBm")
        print(f"    MCS: {fb['final_mcs']}")

    return net, result


def example_system_vs_full_waveform():
    """Example 3: Compare system-level vs full waveform simulation"""
    print("\n" + "="*80)
    print("EXAMPLE 3: System-Level vs Full Waveform Comparison")
    print("="*80)

    # Setup network
    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=20, freq=10e9, bandwidth_MHz=100)
    net.add_ris('R1', 5, 0, 0, N=8, bits=2, freq=10e9)
    net.add_ue('UE1', 10, 0, 0)

    print("\nNetwork Configuration:")
    print(f"  AP1: (0, 0, 0)")
    print(f"  R1:  (5, 0, 0)")
    print(f"  UE1: (10, 0, 0)")

    # System-level simulation (fast)
    print("\n" + "-"*80)
    print("SYSTEM-LEVEL SIMULATION (Fast physics-based)")
    print("-"*80)
    system_result = net.connect('AP1', 'R1', 'UE1')
    print(f"  SNR: {system_result['snr_dB']:.2f} dB")
    print(f"  Power: {system_result['pwr_dBm']:.2f} dBm")
    print(f"  Gain: {system_result['gain_dBi']:.2f} dBi")

    # Full waveform simulation
    print("\n" + "-"*80)
    print("FULL WAVEFORM SIMULATION (Detailed OFDM)")
    print("-"*80)
    controller = WaveformController(net, net.environment)
    controller.set_ofdm_config(bandwidth=100e6, num_subcarriers=256, center_freq=10e9)

    waveform_result = controller.simulate_full_cascade(
        'AP1', 'R1', 'UE1',
        num_symbols=10,
        enable_feedback=False
    )

    print(f"  SNR: {waveform_result['snr_dB']:.2f} dB")
    print(f"  PAPR: {waveform_result['papr_dB']:.2f} dB")
    print(f"  Phase error RMS: {waveform_result['ris_phase_error_rms_deg']:.2f}°")

    # Comparison
    print("\n" + "-"*80)
    print("COMPARISON")
    print("-"*80)
    snr_diff = waveform_result['snr_dB'] - system_result['snr_dB']
    print(f"  SNR difference (waveform - system): {snr_diff:+.2f} dB")
    print(f"  Waveform overhead: {waveform_result['papr_dB']:.2f} dB PAPR")
    print(f"  RIS quantization loss: {waveform_result['ris_phase_error_rms_deg']:.2f}° phase error")
    print(f"\n  Interpretation:")
    print(f"  - System-level provides fast estimates")
    print(f"  - Waveform-level accounts for:")
    print(f"    • OFDM signal characteristics (PAPR)")
    print(f"    • RIS element coupling")
    print(f"    • Phase quantization error")
    print(f"    • Channel estimation imperfections")

    return net, system_result, waveform_result


def example_varying_ris_bits():
    """Example 4: Impact of RIS phase quantization bits"""
    print("\n" + "="*80)
    print("EXAMPLE 4: RIS Phase Quantization Impact")
    print("="*80)

    print("\nVarying RIS bits (1, 2, 4, 8) to see phase error reduction")
    print("="*80)

    # Setup network
    net = RISNetwork()
    net.add_ap('AP1', 0, 0, 0, power_dBm=20, freq=10e9)
    net.add_ue('UE1', 10, 0, 0)

    controller = WaveformController(net, net.environment)
    controller.set_ofdm_config(bandwidth=100e6, num_subcarriers=256, center_freq=10e9)

    results_by_bits = {}

    for bits in [1, 2, 4, 8]:
        # Create RIS with specific bit resolution
        ris_name = f'R_{bits}bit'
        net.add_ris(ris_name, 5, 0, 0, N=8, bits=bits, freq=10e9)

        # Simulate
        result = controller.simulate_full_cascade(
            'AP1', ris_name, 'UE1',
            num_symbols=5,
            enable_feedback=False
        )

        results_by_bits[bits] = result
        print(f"\n{bits}-bit RIS:")
        print(f"  Phase error RMS: {result['ris_phase_error_rms_deg']:7.2f}°")
        print(f"  Measured SNR:    {result['snr_dB']:7.2f} dB")

    # Analysis
    print("\n" + "-"*80)
    print("ANALYSIS")
    print("-"*80)
    print("Phase Error (RMS degrees):")
    for bits in [1, 2, 4, 8]:
        error = results_by_bits[bits]['ris_phase_error_rms_deg']
        print(f"  {bits}-bit: {error:6.2f}°  → ", end="")
        # Theoretical max error for N-bit: (360/(2^N)) / sqrt(12)
        theory = 360 / (2 ** bits * np.sqrt(12))
        print(f"Theory: {theory:6.2f}°")

    return net, results_by_bits


def main():
    """Run all integration examples"""
    print("\n" + "="*80)
    print("RISNet v2.0 - Full Waveform Integration Examples")
    print("="*80)
    print("Demonstrating fully integrated waveform-level simulation")
    print("with UE receiver pipeline and closed-loop feedback")

    # Run examples
    try:
        net1, result1 = example_full_cascade_basic()
        net2, result2 = example_full_cascade_with_feedback()
        net3, sys_result, wave_result = example_system_vs_full_waveform()
        net4, bits_results = example_varying_ris_bits()

        print("\n" + "="*80)
        print("All integration examples completed successfully!")
        print("="*80)
        print("\nKey Achievements:")
        print("✓ Full cascade simulation: AP TX → RIS → UE RX")
        print("✓ Integrated UE receiver pipeline (OFDM demod, channel est, equalization)")
        print("✓ CSI feedback generation from UE measurements")
        print("✓ Closed-loop AP adaptation (power control + MCS)")
        print("✓ Comparison with system-level simulation")
        print("✓ Quantization analysis across RIS bit resolutions")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n✗ Error during integration examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
