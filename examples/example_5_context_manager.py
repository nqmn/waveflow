"""
Example 5: Context Manager Usage

Demonstrates automatic start/stop with context manager.
"""

from risnet import RISnet


def run():
    """Run Example 5"""
    print("\n" + "="*60)
    print("Example 5: Context Manager (auto start/stop)")
    print("="*60)

    # Context manager automatically starts and stops network
    with RISnet() as net:
        print("\n*** Network auto-started")

        # Add nodes
        ap = net.addAP('ap1', position=(0, 0))
        ris = net.addRIS('ris1', position=(5, 0))
        ue = net.addUE('ue1', position=(10, 3))

        # Run test
        result = net.ping(ap, ue)
        print(f"Ping result: SNR = {result['snr_dB']:.1f} dB")

    print("*** Network auto-stopped")


if __name__ == '__main__':
    run()
