"""
Example: Adaptive Link Control with CSI Feedback
Demonstrates closed-loop power control and rate adaptation
"""
import sys
import numpy as np
import json

sys.path.insert(0, '/mnt/c/Users/Intel/Desktop/risnet')

from core import RISNetwork
from controller.adaptive_controller import AdaptiveController


def simulate_noisy_snr(ap_name, ris_name, ue_name, network, base_snr=20.0,
                      noise_std=1.0):
    """Simulate SNR measurement with noise"""
    ap = network.get(ap_name)
    ue = network.get(ue_name)
    ris = network.get(ris_name)

    if ap is None or ue is None or ris is None:
        return None

    measured_snr = base_snr + np.random.normal(0, noise_std)
    measured_snr = np.clip(measured_snr, -30, 40)

    return {'snr_dB': measured_snr}


def example_power_control_only():
    """Example 1: Power control without rate adaptation"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Closed-Loop Power Control Only")
    print("="*70)

    net = RISNetwork()

    net.add_ap('AP1', 0, 0, 0, power_dBm=15.0, freq=5.8e9)
    net.add_ris('R1', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE1', 10, 0, 0)

    adapter = AdaptiveController(net)

    ap = net.get('AP1')
    print(f"\nInitial AP state:")
    print(f"  Power: {ap.power_dBm} dBm")
    print(f"  Target SNR: {ap.target_snr_dB} dB")

    adapter.enable_adaptation('AP1', power_control=True, rate_adaptation=False)

    print(f"\nRunning adaptive control loop (max 15 iterations)...\n")

    def measure_snr_callback(ap_name, ris_name, ue_name):
        ap_obj = net.get(ap_name)
        snr_offset = ap_obj.power_dBm - 15.0
        simulated_snr = 12.0 + snr_offset
        return {'snr_dB': simulated_snr + np.random.normal(0, 0.5)}

    loop_result = adapter.full_control_loop(
        'AP1', 'R1', 'UE1',
        max_iterations=15,
        measure_snr_callback=measure_snr_callback
    )

    adapter.print_summary('AP1')

    print(f"Loop Result:")
    print(f"  Converged: {loop_result['converged']}")
    print(f"  Total Time: {loop_result['total_time']:.2f}s")
    print(f"  Final Power: {loop_result['final_state']['power_dBm']:.1f} dBm")
    print(f"  Final SNR: {loop_result['final_state']['snr_dB']:.1f} dB")


def example_rate_adaptation_only():
    """Example 2: Rate adaptation without power control"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Rate Adaptation Only")
    print("="*70)

    net = RISNetwork()

    net.add_ap('AP2', 0, 0, 0, power_dBm=20.0, freq=5.8e9)
    net.add_ris('R2', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE2', 10, 0, 0)

    adapter = AdaptiveController(net)

    ap = net.get('AP2')
    print(f"\nInitial AP state:")
    print(f"  MCS: {ap.get_current_mcs()['name']}")
    print(f"  Efficiency: {ap.get_current_mcs()['efficiency_bps_hz']} bits/Hz")

    adapter.enable_adaptation('AP2', power_control=False, rate_adaptation=True)

    print(f"\nRunning rate adaptation loop (max 10 iterations)...\n")

    snr_trajectory = [8, 12, 16, 20, 24, 25, 25.5, 25.2, 25.1, 25.0]

    def measure_snr_callback_fixed(ap_name, ris_name, ue_name):
        iteration = len(adapter.control_history[ap_name])
        if iteration < len(snr_trajectory):
            return {'snr_dB': snr_trajectory[iteration]}
        return {'snr_dB': snr_trajectory[-1]}

    loop_result = adapter.full_control_loop(
        'AP2', 'R2', 'UE2',
        max_iterations=len(snr_trajectory),
        measure_snr_callback=measure_snr_callback_fixed
    )

    adapter.print_summary('AP2')

    print(f"Loop Result:")
    print(f"  Final MCS: {loop_result['final_state']['mcs']}")
    print(f"  Final Efficiency: {loop_result['final_state']['efficiency_bps_hz']} bits/Hz")
    print(f"  Final SNR: {loop_result['final_state']['snr_dB']:.1f} dB")


def example_full_adaptation():
    """Example 3: Full closed-loop with power control + rate adaptation"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Full Adaptive Control (Power + Rate)")
    print("="*70)

    net = RISNetwork()

    net.add_ap('AP3', 0, 0, 0, power_dBm=18.0, freq=5.8e9)
    net.add_ris('R3', 5, 0, 0, N=16, bits=2)
    net.add_ue('UE3', 10, 0, 0)

    adapter = AdaptiveController(net)

    ap = net.get('AP3')
    print(f"\nInitial AP state:")
    print(f"  Power: {ap.power_dBm} dBm")
    print(f"  MCS: {ap.get_current_mcs()['name']}")
    print(f"  Target SNR: {ap.target_snr_dB} dB")

    adapter.enable_adaptation('AP3', power_control=True, rate_adaptation=True,
                            target_snr_dB=18.0)

    print(f"\nRunning full adaptive control loop (max 20 iterations)...\n")

    iteration_counter = [0]

    def full_measure_callback(ap_name, ris_name, ue_name):
        base_snr = 12.0 + (net.get(ap_name).power_dBm - 18.0)
        iteration_counter[0] += 1
        noise = np.random.normal(0, 0.8)
        measured = base_snr + noise
        return {'snr_dB': np.clip(measured, 0, 40)}

    loop_result = adapter.full_control_loop(
        'AP3', 'R3', 'UE3',
        max_iterations=20,
        measure_snr_callback=full_measure_callback
    )

    adapter.print_summary('AP3')

    print(f"Loop Result:")
    print(f"  Converged: {loop_result['converged']}")
    print(f"  Total Time: {loop_result['total_time']:.2f}s")
    print(f"  Final Power: {loop_result['final_state']['power_dBm']:.1f} dBm")
    print(f"  Final MCS: {loop_result['final_state']['mcs']}")
    print(f"  Final SNR: {loop_result['final_state']['snr_dB']:.1f} dB")
    print(f"  Spectral Efficiency: {loop_result['final_state']['efficiency_bps_hz']:.1f} bits/Hz")

    history = adapter.get_history('AP3')
    if history:
        print(f"\nFirst and Last Iterations:")
        print(f"  First: SNR={history[0].get('measured_snr_dB', '-'):.1f} dB, "
              f"Power={history[0]['pre_control']['power_dBm']:.1f} dBm")
        print(f"  Last:  SNR={history[-1].get('measured_snr_dB', '-'):.1f} dB, "
              f"Power={history[-1]['post_control']['power_dBm']:.1f} dBm")


def example_csi_feedback_mechanics():
    """Example 4: CSI feedback mechanism demonstration"""
    print("\n" + "="*70)
    print("EXAMPLE 4: CSI Feedback Mechanics")
    print("="*70)

    net = RISNetwork()

    net.add_ap('AP4', 0, 0, 0, power_dBm=20.0)
    net.add_ris('R4', 5, 0, 0)
    net.add_ue('UE4', 10, 0, 0)

    ap = net.get('AP4')
    ue = net.get('UE4')

    print(f"\n1. UE measures SNR from received waveform:")
    snr_measured = ue.estimate_snr_from_waveform(
        rx_signal=np.random.randn(1000) + 1j * np.random.randn(1000),
        noise_power=0.01
    )
    print(f"   Measured SNR: {snr_measured:.2f} dB")

    print(f"\n2. UE generates CSI feedback report:")
    csi_report = ue.generate_csi_feedback(snr_dB=snr_measured)
    print(f"   CSI Report Contents:")
    for key, value in csi_report.items():
        if key != 'channel_estimate':
            print(f"     {key}: {value}")

    print(f"\n3. AP processes CSI feedback:")
    ap.power_control_enabled = True
    ap.rate_adaptation_enabled = True
    ap.target_snr_dB = 20.0

    control_result = ap.process_csi_feedback(csi_report)
    print(f"   Control Actions:")
    print(f"     Power Control: {control_result['power_control']['status']}")
    print(f"     Rate Adaptation: {control_result['rate_adaptation']['status']}")

    if control_result['power_control']['status'] == 'updated':
        pc = control_result['power_control']
        print(f"       Old Power: {pc['old_power_dBm']:.1f} dBm")
        print(f"       New Power: {pc['new_power_dBm']:.1f} dBm")

    if control_result['rate_adaptation']['status'] == 'updated':
        ra = control_result['rate_adaptation']
        print(f"       New MCS: {ra['mcs']}")

    print(f"\n4. Final AP state after feedback processing:")
    print(f"   Power: {ap.power_dBm:.1f} dBm")
    print(f"   MCS: {ap.get_current_mcs()['name']}")
    print(f"   CSI History Size: {len(ap.csi_history)}")


def main():
    """Run all examples"""
    print("\n" + "#"*70)
    print("# RISNet: Adaptive Link Control Examples")
    print("# Demonstrates CSI Feedback, Power Control, and Rate Adaptation")
    print("#"*70)

    try:
        example_power_control_only()
    except Exception as e:
        print(f"Error in Example 1: {e}")

    try:
        example_rate_adaptation_only()
    except Exception as e:
        print(f"Error in Example 2: {e}")

    try:
        example_full_adaptation()
    except Exception as e:
        print(f"Error in Example 3: {e}")

    try:
        example_csi_feedback_mechanics()
    except Exception as e:
        print(f"Error in Example 4: {e}")

    print("\n" + "#"*70)
    print("# All examples completed successfully!")
    print("#"*70 + "\n")


if __name__ == '__main__':
    main()
