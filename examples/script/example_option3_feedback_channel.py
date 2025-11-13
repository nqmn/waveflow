#!/usr/bin/env python3
"""
Example: Option 3 - Feedback Channel (UE → RIS Controller SNR)

Demonstrates how the RIS controller receives real measured SNR from UE
via a feedback channel system. This enables:

1. Real SNR measurements (not just predictions)
2. Closed-loop controller adaptation
3. Multi-link feedback aggregation
4. SNR history and trend analysis

Flow:
  UE measures SNR from received waveform
    ↓
  UE generates CSI report and pushes to feedback channel
    ↓
  RIS controller queries feedback channel for measured SNR
    ↓
  Controller makes decisions based on real measurements
"""

import sys
import numpy as np

# Add parent directory to path
sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from core.feedback_channel import CSIReport
from controller.ris_controller import RISController


def example_basic_feedback_channel():
    """Basic feedback channel setup and SNR reporting"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Feedback Channel Setup")
    print("="*80)

    # Create network
    network = RISNetwork()

    # Add nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=50, y=50, N=16, bits=3)
    network.add_ue('UE1', x=100, y=100)

    # Create feedback channel from UE1 to RIS R1
    channel = network.create_feedback_channel('UE1', 'R1', history_size=50)
    print(f"Created feedback channel: UE1 → R1")

    # Simulate UE measuring SNR and sending feedback
    for iteration in range(5):
        # Simulate SNR measurement from waveform
        measured_snr_dB = 15.0 + np.random.normal(0, 1)  # 15 dB ±1 dB noise

        # Get UE and generate CSI with feedback
        ue = network.get('UE1')
        ue.snr_measurement_dB = measured_snr_dB
        csi = ue.generate_csi_feedback(snr_dB=measured_snr_dB, feedback_channel=channel)

        print(f"\nIteration {iteration}: UE1 measured SNR = {measured_snr_dB:.2f} dB")
        print(f"  CSI pushed to feedback channel")
        print(f"  Channel total reports: {channel.total_reports_received}")

    # Query feedback channel
    print(f"\n{'─'*80}")
    print("Feedback Channel Statistics:")
    stats = channel.get_statistics()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")

    # Get SNR history
    history = channel.get_history()
    print(f"\nSNR History (last 3):")
    for report in history[-3:]:
        print(f"  Seq {report.sequence_num}: {report.snr_dB:.2f} dB @ {report.timestamp:.2f}")


def example_controller_with_feedback():
    """RIS controller using feedback channel for SNR queries"""
    print("\n" + "="*80)
    print("EXAMPLE 2: RIS Controller Using Feedback Channel")
    print("="*80)

    # Create network with controller
    network = RISNetwork()
    controller = RISController(network)

    # Add nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=50, y=50, N=16, bits=3)
    network.add_ue('UE1', x=100, y=100)
    network.set_controller(controller)

    # Enable feedback channel on controller
    channel = controller.enable_feedback_channel('UE1', 'R1')
    print(f"Controller enabled feedback channel: UE1 → R1")

    # Simulate measurements
    print(f"\n{'─'*80}")
    print("Simulating UE measurements and controller queries:")

    for iteration in range(8):
        # Simulate SNR that varies over time
        base_snr = 15.0
        trend = iteration * 0.5  # SNR improving over time
        measured_snr = base_snr + trend + np.random.normal(0, 0.5)

        # UE sends CSI to feedback channel
        ue = network.get('UE1')
        ue.snr_measurement_dB = measured_snr
        ue.generate_csi_feedback(snr_dB=measured_snr, feedback_channel=channel)

        # Controller queries latest SNR from feedback
        latest_snr = controller.get_latest_ue_snr_dB('UE1', 'R1')
        avg_snr = controller.get_average_ue_snr_dB('UE1', 'R1', window=3)

        print(f"\nIteration {iteration}:")
        print(f"  UE measured: {measured_snr:.2f} dB")
        print(f"  Controller queried latest: {latest_snr:.2f} dB")
        print(f"  Controller avg (last 3): {avg_snr:.2f} dB" if avg_snr else "  No history yet")

    # Get controller's view of feedback statistics
    print(f"\n{'─'*80}")
    print("Controller's Feedback Channel View:")
    stats = controller.get_ue_feedback_statistics('UE1', 'R1')
    print(f"  Total reports received: {stats['total_reports']}")
    print(f"  Latest SNR: {stats['latest_snr_dB']:.2f} dB")
    print(f"  Average SNR: {stats['average_snr_dB']:.2f} dB")
    print(f"  Min SNR: {stats['min_snr_dB']:.2f} dB")
    print(f"  Max SNR: {stats['max_snr_dB']:.2f} dB")
    print(f"  SNR Trend: {stats['snr_trend']}")


def example_multiple_links_feedback():
    """Multiple UE feedback channels to same RIS controller"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Multiple UEs with Feedback to Same RIS")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Add nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=50, y=50, N=16, bits=3)
    network.add_ue('UE1', x=100, y=100)
    network.add_ue('UE2', x=80, y=120)
    network.add_ue('UE3', x=120, y=80)

    # Enable feedback channels for all UEs
    print(f"\n{'─'*80}")
    print("Creating feedback channels:")
    channels = {}
    for ue_num in range(1, 4):
        ue_name = f'UE{ue_num}'
        channel = controller.enable_feedback_channel(ue_name, 'R1')
        channels[ue_name] = channel
        print(f"  {ue_name} → R1")

    # Simulate measurements from all UEs
    print(f"\n{'─'*80}")
    print("Simulating measurements from multiple UEs:")

    # Generate SNR patterns for each UE
    snr_patterns = {
        'UE1': {'base': 15.0, 'trend': 0.3},   # UE1 SNR improving
        'UE2': {'base': 12.0, 'trend': -0.2},  # UE2 SNR degrading
        'UE3': {'base': 18.0, 'trend': 0.0},   # UE3 SNR stable
    }

    for iteration in range(6):
        print(f"\nIteration {iteration}:")

        for ue_name, pattern in snr_patterns.items():
            # Calculate SNR for this UE
            base_snr = pattern['base']
            trend = pattern['trend'] * iteration
            measured_snr = base_snr + trend + np.random.normal(0, 0.3)

            # UE sends feedback
            ue = network.get(ue_name)
            ue.snr_measurement_dB = measured_snr
            ue.generate_csi_feedback(snr_dB=measured_snr, feedback_channel=channels[ue_name])

            # Controller queries
            latest = controller.get_latest_ue_snr_dB(ue_name, 'R1')
            trend_status = channels[ue_name].get_snr_trend(window=3)

            print(f"  {ue_name}: SNR={measured_snr:.2f} dB, Latest={latest:.2f} dB, Trend={trend_status}")

    # Summary statistics
    print(f"\n{'─'*80}")
    print("Controller's View of All Feedback Channels:")
    all_stats = controller.get_all_feedback_statistics()

    for channel_key, channel_stats in all_stats.items():
        print(f"\n  Channel: {channel_key}")
        print(f"    Latest SNR: {channel_stats['latest_snr_dB']:.2f} dB")
        print(f"    Average SNR: {channel_stats['average_snr_dB']:.2f} dB")
        print(f"    Status: {channel_stats['status']}")


def example_pathfinding_with_measured_snr():
    """Pathfinding using measured SNR from feedback channels"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Pathfinding Using Measured SNR from Feedback")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Create simple topology
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=50, y=50, N=16, bits=3)
    network.add_ris('R2', x=100, y=0, N=16, bits=3)
    network.add_ue('UE1', x=150, y=50)
    network.set_controller(controller)

    # Setup feedback channels for both RIS nodes
    channel_r1 = controller.enable_feedback_channel('UE1', 'R1')
    channel_r2 = controller.enable_feedback_channel('UE1', 'R2')

    # Simulate different SNR characteristics for each RIS
    print(f"\n{'─'*80}")
    print("Simulating RIS performance from measured SNR:")

    # R1 has good signal
    r1_snr = 18.0 + np.random.normal(0, 0.5)
    ue = network.get('UE1')
    ue.snr_measurement_dB = r1_snr
    ue.generate_csi_feedback(snr_dB=r1_snr, feedback_channel=channel_r1)

    # R2 has poor signal
    r2_snr = 8.0 + np.random.normal(0, 0.5)
    ue.snr_measurement_dB = r2_snr
    ue.generate_csi_feedback(snr_dB=r2_snr, feedback_channel=channel_r2)

    print(f"\nMeasured SNR via feedback channels:")
    print(f"  R1: {controller.get_latest_ue_snr_dB('UE1', 'R1'):.2f} dB")
    print(f"  R2: {controller.get_latest_ue_snr_dB('UE1', 'R2'):.2f} dB")

    # Controller uses measured SNR for pathfinding decision
    snr_r1 = controller.get_latest_ue_snr_dB('UE1', 'R1')
    snr_r2 = controller.get_latest_ue_snr_dB('UE1', 'R2')

    best_ris = 'R1' if snr_r1 > snr_r2 else 'R2'
    print(f"\nController Decision:")
    print(f"  Best RIS: {best_ris} (SNR: {max(snr_r1, snr_r2):.2f} dB)")
    print(f"  Reason: Measured SNR {best_ris} ({max(snr_r1, snr_r2):.2f}) > "
          f"{('R2' if best_ris == 'R1' else 'R1')} ({min(snr_r1, snr_r2):.2f})")


def example_snr_history_analysis():
    """Analyze SNR history and trends from feedback channel"""
    print("\n" + "="*80)
    print("EXAMPLE 5: SNR History and Trend Analysis")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=50, y=50, N=16)
    network.add_ue('UE1', x=100, y=100)

    channel = controller.enable_feedback_channel('UE1', 'R1')

    # Simulate SNR variation (representing fading/mobility)
    print(f"\n{'─'*80}")
    print("Simulating SNR variation and tracking trends:")

    snr_values = [
        12.0, 13.5, 15.2, 14.8, 16.1, 17.5, 18.2, 19.0, 18.5, 17.8
    ]

    for i, snr in enumerate(snr_values):
        ue = network.get('UE1')
        ue.snr_measurement_dB = snr
        ue.generate_csi_feedback(snr_dB=snr, feedback_channel=channel)

        # Analyze trend every 3 measurements
        if i >= 2:
            trend = channel.get_snr_trend(window=3)
            avg = channel.get_average_snr_dB(window=3)
            print(f"  Step {i}: SNR={snr:.1f} dB → Avg(3)={avg:.1f} dB, Trend: {trend}")

    # Final analysis
    print(f"\n{'─'*80}")
    print("Final SNR Analysis:")
    stats = channel.get_statistics()
    print(f"  First SNR: {snr_values[0]:.1f} dB")
    print(f"  Final SNR: {snr_values[-1]:.1f} dB")
    print(f"  Change: {snr_values[-1] - snr_values[0]:+.1f} dB")
    print(f"  Overall Trend: {stats['snr_trend']}")
    print(f"  Average: {stats['average_snr_dB']:.2f} dB")
    print(f"  Min: {stats['min_snr_dB']:.2f} dB")
    print(f"  Max: {stats['max_snr_dB']:.2f} dB")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("OPTION 3: FEEDBACK CHANNEL SYSTEM")
    print("UE → Controller SNR Communication")
    print("="*80)

    # Run all examples
    example_basic_feedback_channel()
    example_controller_with_feedback()
    example_multiple_links_feedback()
    example_pathfinding_with_measured_snr()
    example_snr_history_analysis()

    print("\n" + "="*80)
    print("Option 3 Implementation Summary:")
    print("="*80)
    print("""
Key Features:
  ✓ Real measured SNR from UE (not predictions)
  ✓ In-memory feedback channels (fast, no latency)
  ✓ Historical tracking and trend analysis
  ✓ Multi-link feedback aggregation
  ✓ Controller can query measured SNR anytime

Architecture:
  UE Node
    └─ measure_snr_from_waveform()
    └─ generate_csi_feedback(feedback_channel=...)
         └─ pushes CSIReport to channel

  FeedbackChannel
    ├─ push_report(csi_report)
    ├─ get_latest_snr_dB()
    ├─ get_average_snr_dB(window)
    ├─ get_history()
    └─ get_snr_trend()

  RISController
    ├─ enable_feedback_channel(ue_name, ris_name)
    ├─ get_latest_ue_snr_dB()
    ├─ get_average_ue_snr_dB()
    ├─ get_ue_snr_history()
    └─ get_ue_feedback_statistics()

Usage:
  # Setup
  channel = network.create_feedback_channel('UE1', 'R1')
  controller.enable_feedback_channel('UE1', 'R1')

  # UE sends feedback
  ue.generate_csi_feedback(snr_dB=15.5, feedback_channel=channel)

  # Controller queries
  snr = controller.get_latest_ue_snr_dB('UE1', 'R1')
  history = controller.get_ue_snr_history('UE1', 'R1', last_n=10)
    """)
    print("="*80 + "\n")
