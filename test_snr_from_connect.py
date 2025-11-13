#!/usr/bin/env python3
"""
Test: SNR from connect() Command

Shows exactly what happens to SNR when you use the connect() command
"""

import sys
sys.path.insert(0, '/mnt/c/Users/pc/Desktop/risnet')

from core.network import RISNetwork
from controller.ris_controller import RISController

def test_snr_from_connect():
    """Demonstrate SNR flow from connect() command"""
    print("\n" + "="*80)
    print("TEST: SNR FROM connect() COMMAND")
    print("="*80)
    
    # Setup - CORRECT GEOMETRY
    print("\n[SETUP] Creating network and nodes...")
    print("  AP at x=0 (transmitter)")
    print("  RIS at x=30 (reflector, 16 elements)")
    print("  UE at x=60 (receiver)")
    
    network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    # Check initial state
    ue = network.get('UE1')
    print(f"\nBefore connect():")
    print(f"  UE1.snr_measurement_dB = {ue.snr_measurement_dB}")
    
    # Call connect() - THIS COMPUTES SNR
    print("\n[CONNECT] Calling network.connect('AP1', 'R1', 'UE1')...")
    result = network.connect(
        ap_name='AP1',
        ris_name='R1',
        ue_name='UE1',
        beam_angle_deg=0,
        compute_phases=True,
        bandwidth_MHz=100
    )
    
    print(f"connect() completed successfully")
    print(f"  Status: {result['status']}")
    
    # Check what connect() returned
    print(f"\n[RESULT] What connect() returned:")
    print(f"  Direct SNR: {result['direct_snr_dB']:.2f} dB")
    print(f"  Path SNR (via RIS): {result['path_snr_dB']:.2f} dB")
    
    # Check what was stored in UE
    print(f"\n[UE MEASUREMENT] What was stored in UE:")
    print(f"  UE1.snr_measurement_dB = {ue.snr_measurement_dB:.2f} dB")
    print(f"  (This is what UE 'measured' after connect() computed it)")
    
    # Verify they match
    if abs(ue.snr_measurement_dB - result['path_snr_dB']) < 0.01:
        print(f"\n✓ SNR values match: Both are {ue.snr_measurement_dB:.2f} dB")
    else:
        print(f"\n✗ SNR mismatch")
    
    # Now controller can query this SNR
    print(f"\n[CONTROLLER QUERY] Controller queries SNR via messaging...")
    snr_queried = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    print(f"  Controller received: {snr_queried:.2f} dB")
    
    # All three should match
    print(f"\n[VERIFICATION] Compare all three values:")
    print(f"  1. connect() returned:  {result['path_snr_dB']:.2f} dB")
    print(f"  2. UE measurement:      {ue.snr_measurement_dB:.2f} dB")
    print(f"  3. Controller query:    {snr_queried:.2f} dB")
    
    if (abs(result['path_snr_dB'] - ue.snr_measurement_dB) < 0.01 and
        abs(ue.snr_measurement_dB - snr_queried) < 0.01):
        print(f"\n✓ PASS: All three values match!")
        print(f"   SNR flows correctly: connect() → UE.snr_measurement_dB → controller query")
    else:
        print(f"\n✗ FAIL: Values don't match.")


def test_multiple_connect_calls():
    """Test SNR with multiple connect() calls"""
    print("\n" + "="*80)
    print("TEST: SNR WITH MULTIPLE connect() CALLS")
    print("="*80)
    print("Scenario: Controller calls connect() with different UEs")
    
    network = RISNetwork(enable_messaging=True)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.add_ue('UE2', x=60, y=15)
    network.add_ue('UE3', x=60, y=-15)
    network.set_controller(controller)
    
    print(f"\n{'UE':<8} {'Position':<15} {'SNR from connect()':<20} {'Controller Query':<15}")
    print("-" * 65)
    
    for ue_name, y_pos in [('UE1', 0), ('UE2', 15), ('UE3', -15)]:
        # Call connect()
        result = network.connect('AP1', 'R1', ue_name, compute_phases=True)
        
        # Query via controller
        snr_msg = controller.get_latest_ue_snr_dB(ue_name, 'R1', use_messaging=True)
        
        pos_str = f"y={y_pos}"
        print(f"{ue_name:<8} {pos_str:<15} {result['path_snr_dB']:<20.2f} {snr_msg:<15.2f}")
    
    print("-" * 65)
    print("Each connect() call computes SNR for that UE and stores it")


def test_snr_change_with_ris():
    """Test how SNR changes when RIS configuration changes"""
    print("\n" + "="*80)
    print("TEST: SNR CHANGE WITH RIS CONFIGURATION")
    print("="*80)
    print("Scenario: RIS beamforming direction changes, SNR improves")
    
    network = RISNetwork(enable_messaging=True)
    controller = RISController(network)
    
    network.add_ap('AP1', x=0, y=0, power_dBm=20)
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
    network.add_ue('UE1', x=60, y=0)
    network.set_controller(controller)
    
    print(f"\nStep 1: Initial connect() with RIS normal at 0°")
    result1 = network.connect('AP1', 'R1', 'UE1', compute_phases=True)
    snr1 = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    print(f"  SNR: {snr1:.2f} dB")
    
    print(f"\nStep 2: Modify RIS to point at different angle")
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=10)
    result2 = network.connect('AP1', 'R1', 'UE1', compute_phases=True)
    snr2 = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    print(f"  SNR: {snr2:.2f} dB")
    
    print(f"\nStep 3: Modify RIS again")
    network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=-10)
    result3 = network.connect('AP1', 'R1', 'UE1', compute_phases=True)
    snr3 = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
    print(f"  SNR: {snr3:.2f} dB")
    
    print(f"\n[COMPARISON]")
    print(f"  Config 1 (normal=0°):   {snr1:.2f} dB")
    print(f"  Config 2 (normal=10°):  {snr2:.2f} dB")
    print(f"  Config 3 (normal=-10°): {snr3:.2f} dB")
    print(f"\nEach connect() call recomputes SNR for current RIS configuration")


if __name__ == '__main__':
    test_snr_from_connect()
    test_multiple_connect_calls()
    test_snr_change_with_ris()
    
    print("\n" + "="*80)
    print("SUMMARY: SNR WHEN USING connect() COMMAND")
    print("="*80)
    print("""
When you call network.connect():

1. connect() COMPUTES SNR
   - Calculates: path loss, gains, noise
   - Returns: SNR in result['path_snr_dB']

2. connect() STORES SNR in UE
   - Sets: ue.snr_measurement_dB
   - This becomes UE's "measurement"

3. Controller CAN QUERY this SNR
   - Via messaging: controller.get_latest_ue_snr_dB(use_messaging=True)
   - Directly: ue.snr_measurement_dB
   - Via feedback: feedback_channel.get_latest_snr_dB()

4. SNR CHANGES when:
   - Node positions change
   - RIS configuration changes
   - AP power changes
   - You call connect() again

The SNR is NOT generated by UE - it's COMPUTED by connect() and then
STORED in UE as a measurement, which the controller can then QUERY.
""")
    print("="*80 + "\n")
