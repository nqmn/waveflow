"""
Example 6: Batch Testing

Demonstrates testing multiple configurations in a loop.
"""

from risnet import RISnet


def run():
    """Run Example 6"""
    print("\n" + "="*60)
    print("Example 6: Batch Testing (RIS element count)")
    print("="*60)

    # Test different RIS configurations
    configs = [
        {'N': 8, 'bits': 1},
        {'N': 16, 'bits': 2},
        {'N': 32, 'bits': 3},
    ]

    results = []

    for config in configs:
        net = RISnet()

        ap = net.addAP('ap1', position=(0, 0))
        ris = net.addRIS('ris1', position=(5, 0), **config)
        ue = net.addUE('ue1', position=(10, 3))

        net.start()

        result = net.ping(ap, ue)
        results.append({
            'config': f"{config['N']}x{config['N']}, {config['bits']}-bit",
            'elements': config['N'] * config['N'],
            'snr_dB': result['snr_dB']
        })

        net.stop()

    print("\nResults:")
    print(f"{'Config':<20} {'Elements':<10} {'SNR (dB)':<10}")
    print("-" * 40)
    for r in results:
        print(f"{r['config']:<20} {r['elements']:<10} {r['snr_dB']:<10.1f}")


if __name__ == '__main__':
    run()
