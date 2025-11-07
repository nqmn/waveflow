"""
Example 4: Network with Obstacles

Demonstrates pathfinding around walls and obstacles.
"""

from _bootstrap import ensure_project_root

ensure_project_root()

from risnet import RISnet, topos


def run():
    """Run Example 4"""
    print("\n" + "="*60)
    print("Example 4: Network with Obstacles")
    print("="*60)

    # Use obstacle topology
    topo = topos['obstacle']()
    topo.build()

    net = RISnet(topo=topo)
    net.start()

    print("\n*** Testing pathfinding around obstacles")
    ap = net.aps['ap1']
    ue = net.ues['ue1']

    # Try different algorithms
    for algorithm in ['dijkstra', 'astar', 'greedy']:
        paths = net.findPaths(ap, ue, algorithm=algorithm)

        if paths:
            best = paths[0]
            print(f"\n{algorithm.upper()}:")
            print(f"  Path: {' -> '.join(best['path'])}")
            print(f"  SNR: {best['snr_dB']:.1f} dB")
            print(f"  Type: {best['type']}")

    net.stop()


if __name__ == '__main__':
    run()
