#!/usr/bin/env python3
"""
Example: Real-World SNR Messaging Protocol

Demonstrates real-world control channel communication between:
- RIS Controller (requests SNR)
- UE/AP nodes (responds with measured SNR)

Features simulated:
1. Message serialization/deserialization
2. Control channel latency (with jitter)
3. Request/response matching
4. Timeout handling
5. Error cases
6. Round-trip time measurement

This mimics actual 5G/6G control channel behavior where:
- Controller sends SNR_REQUEST message
- UE receives and processes request
- UE sends SNR_RESPONSE message back
- Latency is incurred on both transmission and response
"""

import sys
sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from controller.ris_controller import RISController
import time


def example_1_basic_messaging():
    """Basic SNR query via control channel"""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic SNR Query via Control Channel")
    print("="*80)

    # Create network WITH messaging enabled (default)
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)

    # Setup nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    # Simulate UE measurement
    ue = network.get('UE1')
    ue.snr_measurement_dB = 15.5

    print(f"UE1 measured SNR: {ue.snr_measurement_dB:.2f} dB")
    print(f"\nController on R1 queries UE1 SNR via control channel...")
    print(f"(Base latency: 5.0ms ± 1.0ms jitter)\n")

    # Query SNR via messaging (default: use_messaging=True)
    start_time = time.time()
    snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    query_time = (time.time() - start_time) * 1000

    print(f"Results:")
    print(f"  Received SNR: {snr:.2f} dB")
    print(f"  Query execution time: {query_time:.2f} ms")
    print(f"  (Includes message transmission and processing)")

    # Show messaging statistics
    stats = network.snr_messaging.get_statistics()
    print(f"\nMessaging Channel Statistics:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Total responses: {stats['total_responses']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
    print(f"  Avg RTT: {stats['avg_rtt_ms']:.2f} ms")
    print(f"  Base latency: {stats['base_latency_ms']:.1f} ms")


def example_2_multiple_queries():
    """Multiple SNR queries over time"""
    print("\n" + "="*80)
    print("EXAMPLE 2: Multiple SNR Queries with Latency Measurement")
    print("="*80)

    network = RISNetwork(enable_messaging=True, latency_ms=10.0, jitter_ms=2.0)
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    print(f"Performing 5 SNR queries with varying measured SNR values")
    print(f"(Base latency: 10.0ms ± 2.0ms)\n")

    snr_values = [15.2, 14.8, 16.1, 15.5, 14.9]

    query_times = []

    for i, snr_val in enumerate(snr_values):
        # Update UE SNR measurement
        ue = network.get('UE1')
        ue.snr_measurement_dB = snr_val

        # Query via messaging
        start = time.time()
        snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
        elapsed = (time.time() - start) * 1000
        query_times.append(elapsed)

        print(f"Query {i+1}: UE measured {snr_val:.1f} dB "
              f"→ Controller received {snr:.1f} dB "
              f"(latency: {elapsed:.2f} ms)")

    # Statistics
    print(f"\n{'─'*80}")
    print(f"Query Latency Summary:")
    print(f"  Average latency: {sum(query_times)/len(query_times):.2f} ms")
    print(f"  Min latency: {min(query_times):.2f} ms")
    print(f"  Max latency: {max(query_times):.2f} ms")

    stats = network.snr_messaging.get_statistics()
    print(f"\nMessaging Statistics:")
    print(f"  Total queries sent: {stats['total_queries']}")
    print(f"  Total responses received: {stats['total_responses']}")
    print(f"  Avg RTT: {stats['avg_rtt_ms']:.2f} ms")


def example_3_messaging_vs_feedback_channel():
    """Compare messaging (real-world) vs feedback channel (legacy)"""
    print("\n" + "="*80)
    print("EXAMPLE 3: Messaging vs Feedback Channel (Real-World vs Legacy)")
    print("="*80)

    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    ue = network.get('UE1')
    ue.snr_measurement_dB = 16.5

    print(f"UE1 measured SNR: {ue.snr_measurement_dB:.2f} dB\n")

    # Method 1: Real-world messaging
    print(f"{'─'*80}")
    print(f"Method 1: Real-World Control Channel (use_messaging=True)")
    print(f"{'─'*80}")
    print(f"Simulates actual wireless control channel communication:")
    print(f"  1. Controller sends SNR_REQUEST message")
    print(f"  2. UE receives message (latency)")
    print(f"  3. UE measures SNR and processes")
    print(f"  4. UE sends SNR_RESPONSE message")
    print(f"  5. Controller receives response (latency)")
    print()

    start = time.time()
    snr_msg = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    msg_time = (time.time() - start) * 1000

    print(f"Result: SNR = {snr_msg:.2f} dB")
    print(f"Latency: {msg_time:.2f} ms\n")

    # Method 2: Legacy feedback channel (instant)
    print(f"{'─'*80}")
    print(f"Method 2: Feedback Channel (use_messaging=False, Legacy)")
    print(f"{'─'*80}")
    print(f"Direct memory access to feedback channel (no latency):")
    print(f"  1. Controller queries feedback channel (in-memory)")
    print(f"  2. Instant response from stored measurements")
    print()

    start = time.time()
    snr_fb = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=False)
    fb_time = (time.time() - start) * 1000

    if snr_fb is not None:
        print(f"Result: SNR = {snr_fb:.2f} dB")
    else:
        print(f"Result: SNR = None (no feedback channel data yet)")
    print(f"Latency: {fb_time:.4f} ms (essentially instant)\n")

    # Comparison
    print(f"{'─'*80}")
    print(f"Comparison:")
    print(f"  Messaging (real-world): {msg_time:.2f} ms - Includes control channel latency")
    print(f"  Feedback (legacy):      {fb_time:.4f} ms - Direct memory access")
    print(f"\nUse messaging=True for realistic simulation")
    print(f"Use messaging=False for fast prototyping")


def example_4_multiple_ues():
    """Query multiple UEs from same RIS controller"""
    print("\n" + "="*80)
    print("EXAMPLE 4: Multi-UE SNR Queries from Single RIS Controller")
    print("="*80)

    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)

    # Multiple UEs
    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.add_ue('UE2', x=60, y=20)
    network.add_ue('UE3', x=60, y=-20)
    network.set_controller(controller)

    # Set different SNR for each UE
    network.get('UE1').snr_measurement_dB = 15.5
    network.get('UE2').snr_measurement_dB = 12.3
    network.get('UE3').snr_measurement_dB = 18.7

    print(f"R1 Controller querying SNR from multiple UEs:\n")

    for ue_num in range(1, 4):
        ue_name = f'UE{ue_num}'
        measured = network.get(ue_name).snr_measurement_dB

        start = time.time()
        snr = controller.get_latest_ue_snr_dB(ue_name, 'R1', use_messaging=True)
        latency = (time.time() - start) * 1000

        print(f"{ue_name}:")
        print(f"  Actual measurement: {measured:.2f} dB")
        print(f"  Received via messaging: {snr:.2f} dB")
        print(f"  Latency: {latency:.2f} ms")

    # Network-wide statistics
    stats = network.snr_messaging.get_statistics()
    print(f"\n{'─'*80}")
    print(f"Network-Wide Messaging Statistics:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Total responses: {stats['total_responses']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")
    print(f"  Average RTT: {stats['avg_rtt_ms']:.2f} ms")


def example_5_message_history():
    """View detailed message transmission history"""
    print("\n" + "="*80)
    print("EXAMPLE 5: Message Transmission History")
    print("="*80)

    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)

    network.add_ap('AP1', x=0, y=0)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)

    network.get('UE1').snr_measurement_dB = 15.5

    print(f"Making 3 SNR queries and tracking message transmission\n")

    for i in range(3):
        snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
        print(f"Query {i+1}: SNR = {snr:.2f} dB")

    # Show message history
    print(f"\n{'─'*80}")
    print(f"Message Transmission History:")
    print(f"{'─'*80}")

    history = network.snr_messaging.get_message_history()
    for msg in history:
        if msg['type'] == 'query':
            print(f"[{msg['status'].upper()}] Query request (ID: {msg['request_id']})")
            print(f"  Timestamp: {msg['timestamp']:.2f}")
            print(f"  Latency: {msg.get('latency_ms', 'N/A'):.2f}ms")
        elif msg['type'] == 'response':
            print(f"[{msg['status'].upper()}] Response received (ID: {msg['request_id']})")
            print(f"  SNR: {msg.get('snr_dB', 'N/A'):.2f} dB")
            print(f"  RTT: {msg.get('rtt_ms', 'N/A'):.2f}ms")

    # Show channel statistics one more time
    stats = network.snr_messaging.get_statistics()
    print(f"\n{'─'*80}")
    print(f"Final Channel Statistics:")
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Total responses: {stats['total_responses']}")
    print(f"  Min RTT: {stats['min_rtt_ms']:.2f} ms")
    print(f"  Max RTT: {stats['max_rtt_ms']:.2f} ms")
    print(f"  Avg RTT: {stats['avg_rtt_ms']:.2f} ms")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("REAL-WORLD SNR MESSAGING PROTOCOL")
    print("Control Channel Communication between RIS Controller and UE/AP")
    print("="*80)

    example_1_basic_messaging()
    example_2_multiple_queries()
    example_3_messaging_vs_feedback_channel()
    example_4_multiple_ues()
    example_5_message_history()

    print("\n" + "="*80)
    print("SNR MESSAGING SUMMARY")
    print("="*80)
    print("""
REAL-WORLD PROTOCOL:
  Controller on RIS needs SNR from UE
    ↓
  1. Controller sends SNR_REQUEST message
  2. Message transmitted over control channel (latency)
  3. UE receives and processes request
  4. UE measures SNR
  5. UE sends SNR_RESPONSE message
  6. Message transmitted back (latency)
  7. Controller receives and processes response

LATENCY SOURCES:
  • Control channel propagation (typical 5-10 ms in 5G)
  • Message serialization/deserialization (< 1 ms)
  • UE processing time (1-5 ms)
  • Jitter and variability (0.5-2 ms)
  • Total RTT: Typically 10-30 ms

FEATURES IMPLEMENTED:
  ✓ Message serialization (SNRQueryMessage, SNRResponseMessage)
  ✓ Control channel simulation (SNRMessagingChannel)
  ✓ Latency and jitter modeling
  ✓ Request/response matching
  ✓ Error handling and timeout
  ✓ Round-trip time measurement
  ✓ Message transmission history
  ✓ Network-wide statistics

USAGE:
  # Real-world simulation (with latency)
  snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)

  # Legacy mode (instant feedback channel)
  snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=False)

NETWORK CONFIGURATION:
  # With messaging (default)
  network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)

  # Without messaging (faster for prototyping)
  network = RISNetwork(enable_messaging=False)
    """)
    print("="*80 + "\n")
