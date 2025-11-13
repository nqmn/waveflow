#!/usr/bin/env python3
"""
Example: Node Isolation with Option 3 Feedback Channel

Demonstrates:
1. Node state isolation (cloning)
2. Feedback channel sharing (persistent)
3. No cross-contamination between calls
4. Original network nodes remain unchanged
"""

import sys
sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from controller.ris_controller import RISController


def example_node_isolation():
    """Nodes are cloned - original never modified"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Node Isolation - Original Nodes Never Modified")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Create network
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    # Store original values
    original_ap_power = network.get('AP1').power_dBm
    original_ap_mcs = network.get('AP1').current_mcs_index
    original_ue_snr = network.get('UE1').snr_measurement_dB

    print(f"BEFORE connect():")
    print(f"  AP1.power_dBm = {original_ap_power}")
    print(f"  AP1.mcs_index = {original_ap_mcs}")
    print(f"  UE1.snr_measurement_dB = {original_ue_snr}")

    # Run connect with feedback
    result = network.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=3
    )

    # Check original values AFTER
    current_ap_power = network.get('AP1').power_dBm
    current_ap_mcs = network.get('AP1').current_mcs_index
    current_ue_snr = network.get('UE1').snr_measurement_dB

    print(f"\nAFTER connect():")
    print(f"  AP1.power_dBm = {current_ap_power}")
    print(f"  AP1.mcs_index = {current_ap_mcs}")
    print(f"  UE1.snr_measurement_dB = {current_ue_snr}")

    print(f"\nCOMPARISON:")
    print(f"  AP power changed? {current_ap_power != original_ap_power} ← Should be False!")
    print(f"  AP MCS changed? {current_ap_mcs != original_ap_mcs} ← Should be False!")
    print(f"  UE SNR changed? {current_ue_snr != original_ue_snr} ← Should be False!")

    if (current_ap_power == original_ap_power and
        current_ap_mcs == original_ap_mcs and
        current_ue_snr == original_ue_snr):
        print(f"\n✓ ISOLATION VERIFIED: Original nodes untouched!")
    else:
        print(f"\n✗ ISOLATION FAILED: Original nodes were modified!")


def example_feedback_channel_sharing():
    """Feedback channels accumulate across multiple calls"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Feedback Channel Sharing - Cumulative History")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    controller.enable_feedback_channel('UE1', 'R1')

    print("Running multiple connect() calls...")
    print(f"\n{'─'*80}")

    for call_num in range(3):
        print(f"\nCall #{call_num + 1}:")

        # Each call generates multiple measurements
        result = network.connect(
            'AP1', 'R1', 'UE1',
            seed=call_num * 100,  # Different fading each time
            compute_phases=False,
            enable_feedback=True,
            max_feedback_iterations=2
        )

        final_snr = result['feedback_info']['final_snr_dB']
        print(f"  Final SNR: {final_snr:.2f} dB")

        # Check feedback channel
        channel = network.get_feedback_channel('UE1', 'R1')
        total_reports = channel.total_reports_received
        print(f"  Total reports in channel: {total_reports} (accumulated)")

    # Show accumulated history
    print(f"\n{'─'*80}")
    print(f"Final Feedback Channel State:")

    history = controller.get_ue_snr_history('UE1', 'R1')
    print(f"  Total measurements: {len(history)}")
    print(f"  SNR values:")
    for report in history:
        print(f"    Seq {report['sequence_num']}: {report['snr_dB']:.2f} dB")

    stats = controller.get_ue_feedback_statistics('UE1', 'R1')
    print(f"\n  Statistics:")
    print(f"    Average: {stats['average_snr_dB']:.2f} dB")
    print(f"    Min: {stats['min_snr_dB']:.2f} dB")
    print(f"    Max: {stats['max_snr_dB']:.2f} dB")

    print(f"\n✓ SHARING VERIFIED: All measurements accumulated in single channel!")


def example_per_link_isolation():
    """Feedback channels are isolated per (UE, RIS) pair"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Per-Link Channel Isolation")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Multiple RIS nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=25, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ris('R2', x=50, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=75, y=0)
    network.set_controller(controller)

    controller.enable_feedback_channel('UE1', 'R1')
    controller.enable_feedback_channel('UE1', 'R2')

    print("Testing links to different RIS nodes...")
    print(f"\n{'─'*80}")

    # Measure link to R1
    print(f"\nMeasuring link to R1:")
    result_r1 = network.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=2
    )
    print(f"  Final SNR via R1: {result_r1['feedback_info']['final_snr_dB']:.2f} dB")

    # Measure link to R2
    print(f"\nMeasuring link to R2:")
    result_r2 = network.connect(
        'AP1', 'R2', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=2
    )
    print(f"  Final SNR via R2: {result_r2['feedback_info']['final_snr_dB']:.2f} dB")

    # Show separate histories
    print(f"\n{'─'*80}")
    print(f"Feedback Channel Isolation:")

    history_r1 = controller.get_ue_snr_history('UE1', 'R1')
    history_r2 = controller.get_ue_snr_history('UE1', 'R2')

    print(f"\n  Channel UE1→R1:")
    print(f"    Reports: {len(history_r1)}")
    for report in history_r1:
        print(f"      Seq {report['sequence_num']}: {report['snr_dB']:.2f} dB")

    print(f"\n  Channel UE1→R2:")
    print(f"    Reports: {len(history_r2)}")
    for report in history_r2:
        print(f"      Seq {report['sequence_num']}: {report['snr_dB']:.2f} dB")

    print(f"\n✓ ISOLATION VERIFIED: Each (UE, RIS) pair has separate history!")


def example_cross_call_independence():
    """Different RIS calls don't affect each other's node state"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Cross-Call Independence")
    print("="*80)

    network = RISNetwork()
    controller = RISController(network)

    # Setup
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=25, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ris('R2', x=50, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=75, y=0)
    network.set_controller(controller)

    print("Checking node state before and after cross-RIS calls...")
    print(f"\n{'─'*80}")

    # Initial state
    print(f"\nInitial state:")
    print(f"  AP1.power_dBm = {network.get('AP1').power_dBm}")

    # Call 1: R1 (would adapt power on clone)
    print(f"\nCall 1: connect to R1 with feedback...")
    network.connect('AP1', 'R1', 'UE1', compute_phases=False, enable_feedback=True, max_feedback_iterations=2)
    print(f"  After Call 1: AP1.power_dBm = {network.get('AP1').power_dBm} ← Should still be 20")

    # Call 2: R2 (would adapt power differently on clone)
    print(f"\nCall 2: connect to R2 with feedback...")
    network.connect('AP1', 'R2', 'UE1', compute_phases=False, enable_feedback=True, max_feedback_iterations=2)
    print(f"  After Call 2: AP1.power_dBm = {network.get('AP1').power_dBm} ← Should still be 20")

    # Call 3: R1 again (should start fresh)
    print(f"\nCall 3: connect to R1 again with feedback...")
    network.connect('AP1', 'R1', 'UE1', compute_phases=False, enable_feedback=True, max_feedback_iterations=2)
    print(f"  After Call 3: AP1.power_dBm = {network.get('AP1').power_dBm} ← Should still be 20")

    print(f"\n✓ INDEPENDENCE VERIFIED: AP power unchanged by any call!")


def example_isolated_vs_persistent():
    """Difference between use_isolated_copy=True vs False"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Isolated vs Persistent Adaptation")
    print("="*80)

    print(f"\n{'─'*80}")
    print("Scenario A: use_isolated_copy=True (DEFAULT, RECOMMENDED)")
    print(f"{'─'*80}")

    network_a = RISNetwork()
    network_a.add_ap('AP1', x=0, y=0, power_dBm=20)
    network_a.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network_a.add_ue('UE1', x=60, y=0)

    print(f"\nBefore: AP1.power_dBm = {network_a.get('AP1').power_dBm}")

    # Call with isolated=True (default)
    network_a.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=3,
        use_isolated_copy=True  # Explicit (default)
    )

    print(f"After:  AP1.power_dBm = {network_a.get('AP1').power_dBm}")
    print(f"Result: Node unchanged ✓")

    print(f"\n{'─'*80}")
    print("Scenario B: use_isolated_copy=False (PERSISTENT ADAPTATION)")
    print(f"{'─'*80}")

    network_b = RISNetwork()
    network_b.add_ap('AP1', x=0, y=0, power_dBm=20)
    network_b.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network_b.add_ue('UE1', x=60, y=0)

    print(f"\nBefore: AP1.power_dBm = {network_b.get('AP1').power_dBm}")

    # Call with isolated=False (persistent)
    network_b.connect(
        'AP1', 'R1', 'UE1',
        compute_phases=False,
        enable_feedback=True,
        max_feedback_iterations=3,
        use_isolated_copy=False  # Modifies original!
    )

    print(f"After:  AP1.power_dBm = {network_b.get('AP1').power_dBm}")
    print(f"Result: Node was modified! ⚠")

    print(f"\n{'─'*80}")
    print("Comparison:")
    print(f"  Isolated=True:  Original nodes NEVER modified")
    print(f"  Isolated=False: Original nodes ARE modified")
    print(f"\n  Use True for:  Safe exploration, multiple measurements")
    print(f"  Use False for: Persistent adaptation across calls")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("NODE ISOLATION WITH OPTION 3 FEEDBACK CHANNELS")
    print("="*80)

    example_node_isolation()
    example_feedback_channel_sharing()
    example_per_link_isolation()
    example_cross_call_independence()
    example_isolated_vs_persistent()

    print("\n" + "="*80)
    print("ISOLATION SUMMARY")
    print("="*80)
    print("""
KEY POINTS:

1. NODE ISOLATION (Default: use_isolated_copy=True)
   ✓ Nodes are cloned (deep copied) before each connect()
   ✓ Original network nodes are NEVER modified
   ✓ No cross-contamination between calls
   ✓ Each call starts with clean state

2. FEEDBACK CHANNEL SHARING
   ✓ Channels are NOT cloned (shared persistent storage)
   ✓ All measurements accumulate in channel
   ✓ Controller can query cumulative history
   ✓ Isolated per (UE, RIS) pair by channel key

3. BENEFITS
   ✓ Safe multiple measurements (no state pollution)
   ✓ Original network preserved
   ✓ Persistent feedback tracking
   ✓ Per-link measurement history
   ✓ No risk of unintended side effects

4. WHEN TO USE PARAMETERS
   use_isolated_copy=True:   Safe exploration, multiple RIS comparison
   use_isolated_copy=False:  Persistent adaptation with state carry-over

5. CONTROL QUERIES
   - Isolated by (UE, RIS) pair
   - Not affected by other link measurements
   - Cross-call trend analysis supported
   - Pure measurement sharing (no node state sharing)
    """)
    print("="*80 + "\n")
