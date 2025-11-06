"""
Example 3: Custom Topology Class

Demonstrates how to create your own topology.
"""

from risnet import RISnet, Topology


def run():
    """Run Example 3"""
    print("\n" + "="*60)
    print("Example 3: Custom Topology Class")
    print("="*60)

    class MyTopo(Topology):
        """Custom Y-shaped topology"""

        def build(self):
            # Center AP
            self.addAP('ap1', position=(0, 0))

            # Three RIS branches
            self.addRIS('ris1', position=(5, 5), N=16, bits=2)
            self.addRIS('ris2', position=(5, 0), N=16, bits=2)
            self.addRIS('ris3', position=(5, -5), N=16, bits=2)

            # Three UEs
            self.addUE('ue1', position=(10, 5))
            self.addUE('ue2', position=(10, 0))
            self.addUE('ue3', position=(10, -5))

    # Build and test
    topo = MyTopo()
    topo.build()

    net = RISnet(topo=topo)
    net.start()

    print("\n*** Testing Y-topology")
    ap = net.aps['ap1']

    for i in range(1, 4):
        ue = net.ues[f'ue{i}']
        ris = net.riss[f'ris{i}']

        # Connect through specific RIS
        result = net.connect(ap, ris, ue)
        print(f"ap1 -> ris{i} -> ue{i}: SNR = {result['snr_dB']:.1f} dB")

    net.stop()


if __name__ == '__main__':
    run()
