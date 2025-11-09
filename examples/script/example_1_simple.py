"""
Example 1: Simple Network Creation

Demonstrates basic RISnet usage with manual node creation.
"""

from _bootstrap import ensure_project_root

ensure_project_root()

from risnet import RISnet


def run():
    """Run Example 1"""
    print("\n" + "="*60)
    print("Example 1: Simple Network Creation")
    print("="*60)

    # Create network
    net = RISnet()

    # Add nodes
    print("\n*** Adding nodes")
    ap = net.addAP('ap1', position=(0, 0))
    ris = net.addRIS('ris1', position=(5, 0), N=16, bits=1)
    ue = net.addUE('ue1', position=(10, 3))

    # Start network
    print("*** Starting network")
    net.start()

    # Test connectivity (like ping)
    print("\n*** Testing connectivity")
    result = net.ping(ap, ue, verbose=True)
    print(f"Ping {ap.name} -> {ue.name}")
    print(f"  Reachable: {result['reachable']}")
    print(f"  SNR: {result['snr_dB']:.1f} dB")
    print(f"  Hops: {result['hops']}")

    # Test throughput with RIS-assisted path
    print("\n*** Testing throughput: RIS-assisted path")
    print("\n  [Test 1] RIS-assisted path (AP → RIS → UE)")
    throughput_ris = net.iperf(ap, ue, verbose=True)
    print(f"  iPerf {ap.name} -> {ue.name} (via RIS)")
    print(f"    Throughput: {throughput_ris['throughput_Mbps']:.1f} Mbps")

    # Calculate theoretical direct path (without RIS reflection loss)
    print("\n  [Test 2] Theoretical direct path (AP → UE, no RIS)")
    from core.physics import Physics
    ap_pos = ap.pos
    ue_pos = ue.pos
    import numpy as np
    distance_direct = np.linalg.norm(np.array(ue_pos) - np.array(ap_pos))
    freq = ap.freq
    path_loss_direct = Physics.path_loss_dB(distance_direct, freq)
    atm_loss_direct = Physics.atmospheric_loss_dB(distance_direct, freq / 1e9)
    tx_power_dBm = ap.power_dBm
    snr_direct_dB = Physics.compute_snr_dB(tx_power_dBm, path_loss_direct + atm_loss_direct, 0, 20, 10)
    snr_direct_linear = 10 ** (snr_direct_dB / 10)
    bandwidth_MHz = net.config.get('environment.bandwidth_MHz', 20)
    throughput_direct_Mbps = bandwidth_MHz * np.log2(1 + snr_direct_linear)

    print(f"    Distance: {distance_direct:.2f} m")
    print(f"    Path loss: {path_loss_direct:.2f} dB")
    print(f"    Atm loss: {atm_loss_direct:.2f} dB")
    print(f"    SNR: {snr_direct_dB:.2f} dB")
    print(f"    Throughput: {throughput_direct_Mbps:.1f} Mbps")

    # Calculate RIS benefit
    print("\n  [Comparison]")
    snr_diff_dB = throughput_ris['snr_dB'] - snr_direct_dB
    throughput_diff = throughput_ris['throughput_Mbps'] - throughput_direct_Mbps
    throughput_improvement = (throughput_ris['throughput_Mbps'] / throughput_direct_Mbps - 1) * 100 if throughput_direct_Mbps > 0 else 0
    print(f"    RIS path SNR: {throughput_ris['snr_dB']:.2f} dB vs Direct: {snr_direct_dB:.2f} dB (diff: {snr_diff_dB:+.2f} dB)")
    print(f"    RIS path throughput: {throughput_ris['throughput_Mbps']:.1f} Mbps vs Direct: {throughput_direct_Mbps:.1f} Mbps")
    print(f"    RIS improvement: {throughput_improvement:+.1f}%")
    print()

    # Stop network
    print("\n*** Stopping network")
    net.stop()


if __name__ == '__main__':
    run()
