"""
Example 2: Using Predefined Topology

Demonstrates how to use built-in topology classes.
"""

from _bootstrap import ensure_project_root

ensure_project_root()

from risnet import RISnet, topos


def run():
    """Run Example 2"""
    print("\n" + "="*60)
    print("Example 2: Predefined Topology")
    print("="*60)

    # Create topology
    print("\n*** Creating topology")
    topo = topos['single']()
    topo.build(n=3)  # 3 UEs

    # Create network with topology
    net = RISnet(topo=topo)

    print("*** Starting network")
    net.start()

    # Test all UEs
    print("\n*** Testing all UEs")
    ap = net.aps['ap1']

    for ue_name in ['ue1', 'ue2', 'ue3']:
        ue = net.ues[ue_name]
        result = net.ping(ap, ue)
        print(f"{ap.name} -> {ue.name}: SNR = {result['snr_dB']:.1f} dB")

    net.stop()


if __name__ == '__main__':
    run()
