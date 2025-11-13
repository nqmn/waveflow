#!/usr/bin/env python3
"""
Test SNR Measurement and Messaging Flow

This script demonstrates:
1. How SNR is measured by the UE
2. How the controller queries for SNR via messaging
3. How to verify the measurements are correct
"""

import sys
sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from controller.ris_controller import RISController
import time

def test_1_basic_snr_measurement():
    """Test 1: Basic SNR measurement and query"""
    print("\n" + "="*80)
    print("TEST 1: Basic SNR Measurement and Query")
    print("="*80)
    
    # Create network with messaging
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    # Setup nodes
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    # STEP 1: UE measures SNR
    print("\n[STEP 1] UE measures signal quality")
    ue = network.get('UE1')
    ue.snr_measurement_dB = 15.5
    print(f"  UE1 measured SNR from received signal: {ue.snr_measurement_dB} dB")
    print(f"  (This is what UE measured from the radio signal it received)")
    
    # STEP 2: Controller queries the UE for SNR via messaging
    print("\n[STEP 2] Controller on R1 queries UE1 for SNR via messaging")
    print(f"  Controller sends: SNR_REQUEST message to UE1")
    
    start = time.time()
    snr_response = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    elapsed = (time.time() - start) * 1000
    
    print(f"  Controller receives: SNR_RESPONSE with snr_dB={snr_response}")
    print(f"  Message round-trip time: {elapsed:.2f} ms")
    
    # STEP 3: Verify the measurement
    print("\n[STEP 3] Verify measurement")
    if snr_response == ue.snr_measurement_dB:
        print(f"  ✓ PASS: Controller received correct SNR value")
        print(f"    UE measured: {ue.snr_measurement_dB} dB")
        print(f"    Controller received: {snr_response} dB")
    else:
        print(f"  ✗ FAIL: SNR mismatch!")
        print(f"    UE measured: {ue.snr_measurement_dB} dB")
        print(f"    Controller received: {snr_response} dB")


def test_2_multiple_measurements():
    """Test 2: Multiple measurements over time"""
    print("\n" + "="*80)
    print("TEST 2: Multiple SNR Measurements (SNR Changes Over Time)")
    print("="*80)
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    print("\nScenario: UE channel quality varies over time")
    print("(Simulating fading channel or UE movement)\n")
    
    # Simulate SNR changing over time (fading channel)
    snr_measurements = [15.5, 14.2, 16.8, 13.9, 17.1]
    
    for iteration, measured_snr in enumerate(snr_measurements, 1):
        # Step 1: UE measures SNR
        ue = network.get('UE1')
        ue.snr_measurement_dB = measured_snr
        
        # Step 2: Controller queries
        queried_snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
        
        # Step 3: Verify
        match = "✓" if queried_snr == measured_snr else "✗"
        print(f"  Iteration {iteration}: UE measured {measured_snr:5.1f} dB → "
              f"Controller received {queried_snr:5.1f} dB {match}")
    
    # Show messaging statistics
    stats = network.snr_messaging.get_statistics()
    print(f"\nMessaging Statistics:")
    print(f"  Total queries sent: {stats['total_queries']}")
    print(f"  Total responses received: {stats['total_responses']}")
    print(f"  Success rate: {stats['success_rate']*100:.1f}%")


def test_3_multi_ue_scenario():
    """Test 3: Multiple UEs with different SNR measurements"""
    print("\n" + "="*80)
    print("TEST 3: Multiple UEs with Different SNR Measurements")
    print("="*80)
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.add_ue('UE2', x=60, y=15)
    network.add_ue('UE3', x=60, y=-15)
    network.set_controller(controller)
    
    print("\nScenario: Three UEs at different locations")
    print("Each UE measures different SNR based on position and channel\n")
    
    # Different SNR for each UE (due to different positions)
    ue_snrs = {
        'UE1': 15.5,   # Best position
        'UE2': 12.3,   # Farther away
        'UE3': 18.7    # Best angle
    }
    
    print(f"{'UE':<6} {'Measured SNR':<15} {'Queried SNR':<15} {'Match':<10}")
    print("-" * 50)
    
    for ue_name, measured_snr in ue_snrs.items():
        # Step 1: UE measures SNR
        ue = network.get(ue_name)
        ue.snr_measurement_dB = measured_snr
        
        # Step 2: Controller queries
        queried_snr = controller.get_latest_ue_snr_dB(ue_name, 'R1', use_messaging=True)
        
        # Step 3: Verify
        match = "✓ PASS" if queried_snr == measured_snr else "✗ FAIL"
        print(f"{ue_name:<6} {measured_snr:>6.1f} dB         "
              f"{queried_snr:>6.1f} dB         {match:<10}")
    
    # Show which UE has best SNR
    print("\n" + "-" * 50)
    best_ue = max(ue_snrs.items(), key=lambda x: x[1])
    print(f"Best UE: {best_ue[0]} with SNR = {best_ue[1]} dB")


def test_4_messaging_vs_feedback():
    """Test 4: Compare messaging (realistic) vs feedback (instant)"""
    print("\n" + "="*80)
    print("TEST 4: Messaging Mode vs Feedback Mode Performance")
    print("="*80)
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    ue = network.get('UE1')
    ue.snr_measurement_dB = 15.5
    
    print("\nMode 1: MESSAGING (Realistic - with simulated control channel latency)")
    print("-" * 80)
    start = time.time()
    snr_msg = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    msg_time = (time.time() - start) * 1000
    print(f"  SNR received: {snr_msg} dB")
    print(f"  Query time: {msg_time:.2f} ms")
    print(f"  (Includes message serialization and handler processing)")
    
    print("\nMode 2: FEEDBACK CHANNEL (Legacy - instant, no latency)")
    print("-" * 80)
    # Create feedback channel first
    network.create_feedback_channel('UE1', 'R1')
    
    start = time.time()
    snr_fb = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=False)
    fb_time = (time.time() - start) * 1000
    print(f"  SNR received: {snr_fb}")
    print(f"  Query time: {fb_time:.4f} ms")
    print(f"  (Direct memory access - no latency)")
    
    print("\n" + "="*80)
    print(f"Comparison:")
    print(f"  Messaging: {msg_time:.2f} ms - Realistic (includes control channel delay)")
    print(f"  Feedback:  {fb_time:.4f} ms - Fast (for prototyping)")
    print(f"  Speed ratio: Feedback is {msg_time/fb_time:.0f}x faster")


def test_5_verify_snr_values():
    """Test 5: Verify SNR values are preserved through messaging"""
    print("\n" + "="*80)
    print("TEST 5: SNR Value Integrity Through Messaging")
    print("="*80)
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    print("\nTesting various SNR values:\n")
    
    test_snr_values = [-5.0, 0.0, 5.5, 10.2, 15.7, 20.0, 25.3]
    all_pass = True
    
    print(f"{'SNR Value':<15} {'Query Result':<15} {'Status':<10}")
    print("-" * 40)
    
    for snr_val in test_snr_values:
        ue = network.get('UE1')
        ue.snr_measurement_dB = snr_val
        
        queried = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
        
        # Check if values match (with floating point tolerance)
        match = abs(queried - snr_val) < 0.0001
        status = "✓ PASS" if match else "✗ FAIL"
        
        if not match:
            all_pass = False
        
        print(f"{snr_val:>6.1f} dB       {queried:>6.1f} dB       {status:<10}")
    
    print("-" * 40)
    if all_pass:
        print("✓ All SNR values preserved correctly through messaging")
    else:
        print("✗ Some SNR values corrupted during messaging")


def test_6_message_history():
    """Test 6: Verify message history tracking"""
    print("\n" + "="*80)
    print("TEST 6: Message History and Statistics")
    print("="*80)
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    ue = network.get('UE1')
    
    print("\nMaking 5 SNR queries and tracking messages:\n")
    
    for i in range(5):
        ue.snr_measurement_dB = 15.0 + i
        snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
        print(f"  Query {i+1}: SNR = {snr} dB")
    
    # Get statistics
    stats = network.snr_messaging.get_statistics()
    
    print("\n" + "-" * 80)
    print("Messaging Statistics:")
    print(f"  Total queries sent:      {stats['total_queries']}")
    print(f"  Total responses received: {stats['total_responses']}")
    print(f"  Success rate:            {stats['success_rate']*100:.1f}%")
    print(f"  Avg RTT:                 {stats['avg_rtt_ms']:.4f} ms")
    print(f"  Min RTT:                 {stats['min_rtt_ms']:.4f} ms")
    print(f"  Max RTT:                 {stats['max_rtt_ms']:.4f} ms")
    print(f"  Base latency config:     {stats['base_latency_ms']:.1f} ms")
    print(f"  Jitter config:           {stats['jitter_ms']:.1f} ms")
    
    # Get message history
    history = network.snr_messaging.get_message_history()
    
    print("\n" + "-" * 80)
    print("Message History:")
    print(f"  Total messages:          {len(history)}")
    
    query_count = sum(1 for m in history if m['type'] == 'query')
    response_count = sum(1 for m in history if m['type'] == 'response')
    
    print(f"  Queries:                 {query_count}")
    print(f"  Responses:               {response_count}")


if __name__ == '__main__':
    print("\n" + "="*80)
    print("SNR MEASUREMENT AND MESSAGING SYSTEM TESTS")
    print("="*80)
    print("\nThis test suite demonstrates how SNR is measured by UEs")
    print("and queried by the RIS controller via messaging protocol")
    
    test_1_basic_snr_measurement()
    test_2_multiple_measurements()
    test_3_multi_ue_scenario()
    test_4_messaging_vs_feedback()
    test_5_verify_snr_values()
    test_6_message_history()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\nKey Takeaways:")
    print("  1. UE measures SNR from received signal (snr_measurement_dB)")
    print("  2. Controller queries UE via SNR_REQUEST message")
    print("  3. UE responds with SNR_RESPONSE containing measured value")
    print("  4. Controller receives SNR and can use it for decisions")
    print("  5. Messaging includes simulated latency (realistic)")
    print("  6. Feedback channel provides instant access (for prototyping)")
    print("="*80 + "\n")
