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
    ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
    ue = net.addUE('ue1', position=(10, 3))

    # Start network
    print("*** Starting network")
    net.start()

    # Test connectivity (like ping)
    print("\n*** Testing connectivity")
    result = net.ping(ap, ue)
    print(f"Ping {ap.name} -> {ue.name}")
    print(f"  Reachable: {result['reachable']}")
    print(f"  SNR: {result['snr_dB']:.1f} dB")
    print(f"  Hops: {result['hops']}")

    # Test throughput (like iperf)
    print("\n*** Testing throughput")
    throughput = net.iperf(ap, ue)
    print(f"iPerf {ap.name} -> {ue.name}")
    print(f"  Throughput: {throughput['throughput_Mbps']:.1f} Mbps")

    # Stop network
    print("\n*** Stopping network")
    net.stop()


if __name__ == '__main__':
    run()
