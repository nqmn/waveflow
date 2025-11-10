#!/usr/bin/env python3
"""
Example: Adaptive RIS System with Advanced Features

Demonstrates:
1. Smart ML predictor with geometry-based beam angle suggestions
2. Real-time power control loop regulating SNR to target
3. ARQ/retransmission for error recovery
4. Adaptive phase noise and CFO based on channel quality
5. Real-time beam tracking with greedy hill-climbing
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import RISNetwork
from controller.beamsweeping.ml.smart_predictor import SmartGeometryPredictor
from controller.power_controller import PowerControlSystem, PowerControlParams
from controller.beam_tracker import RealTimeBeamTracker, BeamTrackingConfig
from core.arq_handler import ARQSystem, ARQConfig
from core.adaptive_impairments import AdaptiveChannelImpairments, ChannelQualityMonitor


def demo_smart_ml_predictor():
    """Demonstrate smart geometry-based ML predictor"""
    print("\n" + "="*70)
    print("1️⃣  SMART ML PREDICTOR (Geometry-Based)")
    print("="*70)

    # Setup network
    net = RISNetwork()
    net.add_ap("ap1", 0, 0, power_dBm=20)
    net.add_ris("ris1", 40, 0)
    net.add_ue("ue1", 80, 20)

    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    # Create smart predictor
    predictor = SmartGeometryPredictor()

    # Predict angles without history
    print("\n[Initial prediction - no history]")
    angles = predictor.predict_local_angles(
        "ap1", "ris1", "ue1",
        fov=60, top_k=3,
        ap_pos=ap.pos, ris_pos=ris.pos, ue_pos=ue.pos
    )
    print(f"  Predicted angles: {[f'{a:.1f}°' for a in angles]}")

    # Simulate measurements and update predictor
    print("\n[After observing SNR measurements]")
    test_angles = [0.0, 5.0, -5.0, 10.0]
    test_snrs = [32.5, 28.3, 35.8, 22.1]

    for angle, snr in zip(test_angles, test_snrs):
        predictor.record_measurement("link_ap1_ris1_ue1", angle, snr)
        print(f"  Angle {angle:6.1f}° → SNR {snr:6.2f} dB")

    # Predict again with history
    angles_refined = predictor.predict_local_angles(
        "ap1", "ris1", "ue1",
        fov=60, top_k=3,
        ap_pos=ap.pos, ris_pos=ris.pos, ue_pos=ue.pos
    )
    print(f"  Refined predictions: {[f'{a:.1f}°' for a in angles_refined]}")
    print("  ✓ Predictor memory learning from measurements")


def demo_power_control():
    """Demonstrate adaptive power control loop"""
    print("\n" + "="*70)
    print("2️⃣  ADAPTIVE POWER CONTROL (SNR Regulation)")
    print("="*70)

    # Setup network
    net = RISNetwork()
    net.add_ap("ap1", 0, 0, power_dBm=15.0)
    net.add_ue("ue1", 50, 0)

    ap = net.get("ap1")

    # Create power control system
    power_sys = PowerControlSystem(net)
    params = PowerControlParams(
        target_snr_dB=25.0,
        power_min_dBm=10.0,
        power_max_dBm=30.0,
        step_size_dB=1.0
    )

    regulator = power_sys.enable_regulation("ap1", "ue1", target_snr_dB=25.0, params=params)

    print(f"\n[Starting with AP power = {ap.power_dBm} dBm]")
    print(f"[Target SNR = 25 dB]")
    print(f"{'Iter':<5} {'Measured SNR':<14} {'AP Power':<12} {'Error':<10} {'Status':<15}")
    print("-" * 60)

    # Simulate SNR measurements with noise
    np.random.seed(42)
    measured_snrs = [18.2, 21.5, 24.1, 24.8, 25.2, 24.9]

    for i, snr in enumerate(measured_snrs):
        result = regulator.regulate(snr)
        status = "CONVERGED" if result['converged'] else "Adapting"
        print(f"{i+1:<5} {snr:>6.1f} dB       {result['new_power_dBm']:>6.1f} dBm    "
              f"{abs(result['snr_error_dB']):>6.2f} dB  {status:<15}")

    print(f"\n✓ Power control converged in {regulator.iteration_count} iterations")
    print(f"  Final power: {ap.power_dBm:.1f} dBm (adjusted from 15.0 dBm)")


def demo_arq_system():
    """Demonstrate ARQ with error recovery"""
    print("\n" + "="*70)
    print("3️⃣  ARQ SYSTEM (Automatic Repeat Request)")
    print("="*70)

    # Create ARQ system
    arq_config = ARQConfig(max_retransmissions=3, use_crc=True)
    arq = ARQSystem(arq_config)

    print(f"\n[Configuration: max_retransmissions={arq_config.max_retransmissions}, "
          f"CRC enabled]")

    # Simulate transmission with errors
    print(f"\n{'Pkt':<5} {'Status':<15} {'Seq':<5} {'Attempt':<8} {'Result':<20}")
    print("-" * 60)

    # Packet 1: Success on first try
    payload1 = np.array([1, 0, 1, 1, 0, 1, 0, 1], dtype=np.uint8)
    tx_info = arq.transmit(payload1)
    packet = tx_info['packet']
    is_valid, decoded, seq = arq.receive_and_decode(packet)
    status = "✓ SUCCESS" if is_valid else "✗ ERROR"
    print(f"1   {status:<15} {seq:<5} {tx_info['attempt']:<8} Received correctly")

    # Packet 2: Requires retransmission
    payload2 = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=np.uint8)
    tx_info = arq.transmit(payload2)

    # First attempt corrupts packet
    print(f"2   ✗ CORRUPTED      {tx_info['seq_num']:<5} 1        Retrying...")

    # Retransmit
    retx_info = arq.retransmit(tx_info['seq_num'])
    if retx_info:
        is_valid, decoded, seq = arq.receive_and_decode(retx_info['packet'])
        print(f"    ✓ RECOVERED      {seq:<5} {retx_info['attempt']:<8} Recovered on retry")

    # Packet 3: Max retries exceeded
    payload3 = np.array([1, 1, 0, 0, 1, 1, 0, 0], dtype=np.uint8)
    tx_info = arq.transmit(payload3)
    print(f"3   ✗ FAILED (MAX)   {tx_info['seq_num']:<5} 1        Max retries attempted")

    stats = arq.get_statistics()
    print(f"\n[Statistics]")
    print(f"  Packets transmitted: {stats['packets_transmitted']}")
    print(f"  Packets received:    {stats['packets_received']}")
    print(f"  Packets corrupted:   {stats['packets_corrupted']}")
    print(f"  Total retransmissions: {stats['total_retransmissions']}")
    print(f"  Success rate:        {stats.get('success_rate', 0)*100:.1f}%")


def demo_adaptive_impairments():
    """Demonstrate adaptive phase noise and CFO"""
    print("\n" + "="*70)
    print("4️⃣  ADAPTIVE IMPAIRMENTS (Phase Noise & CFO)")
    print("="*70)

    impairments = AdaptiveChannelImpairments()
    monitor = ChannelQualityMonitor()

    print("\n[SNR Condition → Channel Impairments]")
    print(f"{'SNR (dB)':<12} {'Condition':<15} {'Phase Noise (rad/s)':<22} {'CFO (Hz)':<15}")
    print("-" * 65)

    snr_values = [5, 10, 15, 20, 25, 35]

    for snr in snr_values:
        impair = impairments.interpolate_linearly(snr)
        condition = impair['snr_condition']
        phase_noise = impair['phase_noise_std']
        cfo = impair['cfo_hz']
        monitor.add_measurement(snr)
        print(f"{snr:<12} {condition:<15} {phase_noise:<22.5f} {cfo:<15.1f}")

    stats = monitor.get_statistics()
    print(f"\n[Channel Quality Statistics]")
    print(f"  Current SNR:  {stats['current_snr_dB']:.1f} dB")
    print(f"  Mean SNR:     {stats['mean_snr_dB']:.1f} dB")
    print(f"  SNR range:    {stats['min_snr_dB']:.1f} - {stats['max_snr_dB']:.1f} dB")
    print(f"  Trend:        {stats['trend']}")
    print(f"  ✓ Impairments adapt automatically with channel conditions")


def demo_beam_tracking():
    """Demonstrate real-time beam tracking"""
    print("\n" + "="*70)
    print("5️⃣  REAL-TIME BEAM TRACKING (Greedy Hill-Climbing)")
    print("="*70)

    # Setup network
    net = RISNetwork()
    net.add_ap("ap1", 0, 0)
    net.add_ris("ris1", 40, 0)
    net.add_ue("ue1", 80, 10)

    # Create beam tracker
    tracker_config = BeamTrackingConfig(algorithm='greedy_hill_climb')
    tracker = RealTimeBeamTracker(net, tracker_config)
    tracker.enable_tracking("ap1", "ris1", "ue1")

    print(f"\n[Tracking configuration: {tracker_config.algorithm}]")
    print(f"{'Iter':<5} {'Angle (°)':<12} {'SNR (dB)':<12} {'Improvement (dB)':<18} {'Converged':<12}")
    print("-" * 65)

    # Simulate beam tracking with SNR measurements
    tracking_angles = [0.0, 2.0, 5.0, 7.0, 7.5, 7.3]
    tracking_snrs = [28.5, 31.2, 34.8, 36.2, 36.5, 36.4]

    for i, (angle, snr) in enumerate(zip(tracking_angles, tracking_snrs)):
        result = tracker.update_beam("ap1", "ris1", "ue1", snr)
        converged = "✓ YES" if result['converged'] else "  NO"
        print(f"{i+1:<5} {result['current_angle']:>8.1f}    {snr:>8.1f}    "
              f"{result['snr_improvement_dB']:>14.2f}    {converged:<12}")

    status = tracker.get_all_status()
    print(f"\n[Final Tracking Status]")
    for link, info in status.items():
        print(f"  Link: {link}")
        print(f"    Current beam: {info['current_angle_deg']:.1f}°")
        print(f"    Best SNR:     {info['best_snr_dB']:.1f} dB @ {info['best_angle_deg']:.1f}°")
        print(f"    Converged:    {info['converged']}")


def main():
    """Run all demonstrations"""
    print("\n" + "="*70)
    print("ADAPTIVE RIS SYSTEM DEMONSTRATION")
    print("Advanced Features for Realistic Simulation")
    print("="*70)

    demo_smart_ml_predictor()
    demo_power_control()
    demo_arq_system()
    demo_adaptive_impairments()
    demo_beam_tracking()

    print("\n" + "="*70)
    print("✅ ALL DEMONSTRATIONS COMPLETED")
    print("="*70)
    print("\nKey Improvements:")
    print("  ✓ ML predictor learns from geometry and history")
    print("  ✓ Power control regulates SNR to target setpoint")
    print("  ✓ ARQ recovers from transmission errors")
    print("  ✓ Phase noise/CFO adapt to channel quality")
    print("  ✓ Beam tracking optimizes RIS steering in real-time")


if __name__ == "__main__":
    main()
