#!/usr/bin/env python3
"""
Example: Option 3 Fully Integrated with network.connect()

Shows how Option 3 feedback channels work seamlessly with network.connect():

1. When you call connect() with enable_feedback=True:
   - UE measures SNR from waveform
   - UE automatically pushes measured SNR to feedback channel
   - Controller can query measured SNR anytime

2. Process flow:
   network.connect(enable_feedback=True)
     ↓
   _run_adaptive_feedback_loop()
     ↓
   For each iteration:
     - UE measures SNR
     - UE.generate_csi_feedback(feedback_channel=...)
     - CSIReport automatically pushed to channel
     - Controller queries: get_latest_ue_snr_dB()

This is the recommended approach for real-time SNR feedback to controller.
"""

import sys
import numpy as np

sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from controller.ris_controller import RISController


def example_1_basic_integration():
    """Basic: connect() automatically pushes to feedback channel"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Integration - connect() Auto-Pushes to Feedback Channel")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Setup nodes (good geometry: RIS between AP and UE)
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, bits=3, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    # Enable controller feedback
    controller.enable_feedback_channel('UE1', 'R1')
    print("Enabled feedback channel: UE1 → R1")

    # Call connect with feedback enabled
    print("\nCalling: network.connect('AP1', 'R1', 'UE1', enable_feedback=True)")
    result = network.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,  # Skip phase computation for simple example
        enable_feedback=True,
        max_feedback_iterations=5
    )

    print(f"\nFeedback Loop Results:")
    print(f"  Converged: {result['feedback_info']['converged']}")
    print(f"  Iterations: {result['feedback_info']['num_iterations']}")
    print(f"  Final SNR: {result['feedback_info']['final_snr_dB']:.2f} dB")
    print(f"  Final Power: {result['feedback_info']['final_power_dBm']:.2f} dBm")

    # Controller now has access to measured SNR history
    print(f"\nController Queries Measured SNR:")
    latest_snr = controller.get_latest_ue_snr_dB('UE1', 'R1')
    print(f"  Latest measured SNR: {latest_snr:.2f} dB")

    history = controller.get_ue_snr_history('UE1', 'R1')
    print(f"  Measurement history:")
    for report in history:
        print(f"    Seq {report['sequence_num']}: {report['snr_dB']:.2f} dB")


def example_2_multiple_connect_calls():
    """Multiple connect() calls accumulate in feedback channel"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multiple Measurements Accumulate in Feedback Channel")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, bits=3, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    controller.enable_feedback_channel('UE1', 'R1')

    print("Simulating multiple link measurements over time:")
    print("(e.g., due to mobility, fading, or RIS reconfiguration)\n")

    for call_num in range(4):
        print(f"─" * 80)
        print(f"Connect Call #{call_num + 1}:")

        # Each call with different RIS steering
        result = network.connect(
            'AP1', 'R1', 'UE1',
            compute_phases=False,
            enable_feedback=True,
            max_feedback_iterations=3
        )

        final_snr = result['feedback_info']['final_snr_dB']
        print(f"  Measured SNR: {final_snr:.2f} dB")

    # Show accumulated history
    print(f"\n{'─' * 80}")
    print("Controller's View of All Measurements:")
    stats = controller.get_ue_feedback_statistics('UE1', 'R1')

    print(f"  Total measurements received: {stats['total_reports']}")
    print(f"  Latest SNR: {stats['latest_snr_dB']:.2f} dB")
    print(f"  Average SNR: {stats['average_snr_dB']:.2f} dB")
    print(f"  Min SNR: {stats['min_snr_dB']:.2f} dB")
    print(f"  Max SNR: {stats['max_snr_dB']:.2f} dB")
    print(f"  Trend: {stats['snr_trend']}")


def example_3_multi_ris_comparison():
    """Compare measured SNR across multiple RIS for pathfinding"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Multi-RIS Pathfinding Using Measured SNR")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Setup topology with 2 RIS (linear arrangement with good geometry)
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=25, y=0, N=16, bits=3, max_angle_deg=90, normal_angle_deg=0)
    network.add_ris('R2', x=50, y=0, N=16, bits=3, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=75, y=0)
    network.set_controller(controller)

    # Enable feedback channels for both RIS
    controller.enable_feedback_channel('UE1', 'R1')
    controller.enable_feedback_channel('UE1', 'R2')

    print("Path options:")
    print("  Path 1: AP1 → R1 → UE1")
    print("  Path 2: AP1 → R2 → UE1\n")

    # Test each path
    paths = {
        'Path 1 (R1)': ('AP1', 'R1', 'UE1'),
        'Path 2 (R2)': ('AP1', 'R2', 'UE1'),
    }

    print("Measuring each path with feedback:")
    for path_name, (ap, ris, ue) in paths.items():
        print(f"\n{path_name}:")
        result = network.connect(
            ap, ris, ue,
            compute_phases=False,
            enable_feedback=True,
            max_feedback_iterations=4
        )
        print(f"  Measured SNR: {result['feedback_info']['final_snr_dB']:.2f} dB")

    # Controller decides best path based on measured SNR
    print(f"\n{'─' * 80}")
    print("Controller Decision (based on measured SNR):")

    snr_r1 = controller.get_latest_ue_snr_dB('UE1', 'R1')
    snr_r2 = controller.get_latest_ue_snr_dB('UE1', 'R2')

    print(f"  R1 measured SNR: {snr_r1:.2f} dB")
    print(f"  R2 measured SNR: {snr_r2:.2f} dB")

    best_ris = 'R1' if snr_r1 > snr_r2 else 'R2'
    best_snr = max(snr_r1, snr_r2)

    print(f"\n  ✓ Best path: AP1 → {best_ris} → UE1")
    print(f"  ✓ Reason: Measured SNR = {best_snr:.2f} dB (highest)")


def example_4_adaptive_control_loop():
    """Real-time control loop using measured SNR feedback"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Adaptive Control Loop with Measured SNR")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0, power_dBm=15)
    network.add_ris('R1', x=50, y=0, N=16, bits=3, max_angle_deg=90)
    network.add_ue('UE1', x=100, y=0)
    network.set_controller(controller)

    controller.enable_feedback_channel('UE1', 'R1')

    print("Adaptive control: Adjust RIS configuration based on measured SNR\n")

    # Simulate different RIS configurations
    configurations = [
        {'name': 'Config A (wide beam)', 'beam_angle': 0},
        {'name': 'Config B (narrow beam)', 'beam_angle': 15},
        {'name': 'Config C (focused beam)', 'beam_angle': 30},
    ]

    best_config = None
    best_snr = -float('inf')

    print("Testing RIS configurations:")
    for config in configurations:
        print(f"\n{config['name']}:")

        result = network.connect(
            'AP1', 'R1', 'UE1',
            beam_angle_deg=config['beam_angle'],
            compute_phases=False,
            enable_feedback=True,
            max_feedback_iterations=3
        )

        measured_snr = result['feedback_info']['final_snr_dB']
        print(f"  Measured SNR: {measured_snr:.2f} dB")

        if measured_snr > best_snr:
            best_snr = measured_snr
            best_config = config['name']

    print(f"\n{'─' * 80}")
    print(f"Control Decision:")
    print(f"  ✓ Best configuration: {best_config}")
    print(f"  ✓ Measured SNR: {best_snr:.2f} dB")


def example_5_snr_trend_prediction():
    """Use SNR history to predict and adapt"""
    print("\n" + "="*80)
    print("EXAMPLE 5: SNR Trend Analysis for Predictive Control")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, bits=3, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    controller.enable_feedback_channel('UE1', 'R1')

    print("Simulating fading channel and predicting SNR trend:\n")

    for time_step in range(5):
        print(f"Time Step {time_step}:")

        # Simulate measurement
        result = network.connect(
            'AP1', 'R1', 'UE1',
            seed=time_step * 100,  # Different fading each time
            compute_phases=False,
            enable_feedback=True,
            max_feedback_iterations=2
        )

        snr = result['feedback_info']['final_snr_dB']
        print(f"  Measured SNR: {snr:.2f} dB")

        # Analyze trend
        stats = controller.get_ue_feedback_statistics('UE1', 'R1')
        trend = stats['snr_trend']
        avg_snr = stats['average_snr_dB']

        print(f"  Average SNR (history): {avg_snr:.2f} dB")
        print(f"  Trend: {trend}")

        # Adaptive action based on trend
        if trend == 'degrading':
            print(f"  → Action: Increase TX power (SNR degrading)")
        elif trend == 'improving':
            print(f"  → Action: Reduce TX power (SNR improving)")
        else:
            print(f"  → Action: Maintain current settings (stable)")

        print()


def example_6_direct_controller_query():
    """Direct controller queries without explicit enable"""
    print("\n" + "="*80)
    print("EXAMPLE 6: Controller Queries Work Automatically After connect()")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=50, y=0, N=16, max_angle_deg=90)
    network.add_ue('UE1', x=100, y=0)
    network.set_controller(controller)

    print("Note: You don't need to explicitly enable feedback first!")
    print("connect() will auto-create feedback channel if needed.\n")

    # Just call connect with feedback
    print("Calling: network.connect('AP1', 'R1', 'UE1', enable_feedback=True)")
    result = network.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=4
    )

    print(f"\nWithout any prior setup, controller can now query:")

    # These work immediately after connect()
    latest = controller.get_latest_ue_snr_dB('UE1', 'R1')
    print(f"  Latest SNR: {latest:.2f} dB")

    avg = controller.get_average_ue_snr_dB('UE1', 'R1', window=2)
    print(f"  Average SNR (last 2): {avg:.2f} dB")

    history = controller.get_ue_snr_history('UE1', 'R1', last_n=2)
    print(f"  History count: {len(history)}")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("OPTION 3: FULLY INTEGRATED FEEDBACK CHANNEL SYSTEM")
    print("connect() ↔ Feedback Channel ↔ Controller")
    print("="*80)

    example_1_basic_integration()
    example_2_multiple_connect_calls()
    example_3_multi_ris_comparison()
    example_4_adaptive_control_loop()
    example_5_snr_trend_prediction()
    example_6_direct_controller_query()

    print("\n" + "="*80)
    print("OPTION 3 INTEGRATION SUMMARY")
    print("="*80)
    print("""
KEY CHANGES:
  1. network.connect(enable_feedback=True) now automatically:
     - Gets or creates feedback channel for UE→RIS
     - Pushes each measured SNR to channel as CSIReport
     - Makes all measurements available to controller

  2. Controller can query measured SNR anytime:
     - controller.get_latest_ue_snr_dB('UE1', 'R1')
     - controller.get_average_ue_snr_dB('UE1', 'R1', window=5)
     - controller.get_ue_snr_history('UE1', 'R1', last_n=10)
     - controller.get_ue_feedback_statistics('UE1', 'R1')

  3. NO EXTRA WORK NEEDED:
     - Just use connect() with enable_feedback=True
     - Channel auto-creates if needed
     - Measured SNR automatically available to controller

PROCESS FLOW:
  network.connect('AP1', 'R1', 'UE1', enable_feedback=True)
    │
    ├─ _run_adaptive_feedback_loop()
    │  │
    │  ├─ Get/Create feedback channel for UE1→R1
    │  │
    │  ├─ For each iteration:
    │  │  ├─ UE measures SNR from waveform
    │  │  ├─ ue.generate_csi_feedback(feedback_channel=...)
    │  │  ├─ CSIReport pushed to channel
    │  │  └─ AP adapts power/modulation
    │  │
    │  └─ Return final SNR and convergence info
    │
    └─ Measured SNR now accessible to controller:
       └─ controller.get_latest_ue_snr_dB('UE1', 'R1')

USE CASES:
  ✓ Pathfinding: Choose best RIS based on measured SNR
  ✓ Link selection: Pick best link from multiple options
  ✓ Predictive control: Adapt based on SNR trends
  ✓ Performance monitoring: Track SNR over time
  ✓ Closed-loop adaptation: Feedback drives RIS configuration
    """)
    print("="*80 + "\n")
