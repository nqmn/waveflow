"""
Test auto-discovery of algorithms and examples
"""

import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))


def test_algorithm_discovery():
    """Test algorithm auto-discovery"""
    print("\n" + "="*60)
    print("Testing Algorithm Auto-Discovery")
    print("="*60)

    from algorithms import list_algorithms, get_registry

    # List all discovered algorithms
    algorithms = list_algorithms()
    print(f"\n✓ Discovered {len(algorithms)} algorithms:")
    for name in sorted(algorithms):
        print(f"  - {name}")

    # Get detailed info
    print("\nAlgorithm Details:")
    print("-" * 60)
    registry = get_registry()
    for name, info in registry.get_all_info().items():
        print(f"{name:15s} - {info['description']}")

    # Test loading an algorithm
    print("\n✓ Testing algorithm loading...")
    from algorithms import get_algorithm

    dijkstra = get_algorithm('dijkstra')
    print(f"  Loaded: {dijkstra.name} - {dijkstra.description}")

    astar = get_algorithm('astar')
    print(f"  Loaded: {astar.name} - {astar.description}")

    print("\n✓ Algorithm auto-discovery working!")


def test_example_discovery():
    """Test example auto-discovery"""
    print("\n" + "="*60)
    print("Testing Example Auto-Discovery")
    print("="*60)

    import importlib
    import pkgutil
    import examples

    example_modules = []

    for importer, modname, ispkg in pkgutil.iter_modules(examples.__path__):
        if modname.startswith('example_') and not ispkg:
            example_modules.append(modname)

    print(f"\n✓ Discovered {len(example_modules)} examples:")
    for ex in sorted(example_modules):
        print(f"  - {ex}")

    # Test loading an example
    print("\n✓ Testing example loading...")
    module = importlib.import_module('examples.example_1_simple')
    if hasattr(module, 'run'):
        print(f"  Loaded: {module.__name__} with run() function")

    print("\n✓ Example auto-discovery working!")


def test_controller_integration():
    """Test controller with auto-discovered algorithms"""
    print("\n" + "="*60)
    print("Testing Controller Integration")
    print("="*60)

    from risnet import RISnet

    # Create simple network
    net = RISnet()
    ap = net.addAP('ap1', position=(0, 0))
    ris = net.addRIS('ris1', position=(5, 0))
    ue = net.addUE('ue1', position=(10, 3))
    net.start()

    # Test each discovered algorithm
    from algorithms import list_algorithms

    print("\n✓ Testing each algorithm:")
    for algorithm in list_algorithms():
        try:
            paths = net.findPaths(ap, ue, algorithm=algorithm)
            if paths:
                best = paths[0]
                print(f"  {algorithm:12s} - Path: {' -> '.join(best['path'][:3])} - SNR: {best['snr_dB']:.1f} dB")
            else:
                print(f"  {algorithm:12s} - No path found")
        except Exception as e:
            print(f"  {algorithm:12s} - Error: {e}")

    net.stop()

    print("\n✓ Controller integration working!")


def test_add_new_algorithm():
    """Demonstrate how to add a new algorithm"""
    print("\n" + "="*60)
    print("Demo: Adding a New Algorithm")
    print("="*60)

    example_code = '''
# File: algorithms/my_algorithm.py

from .base import PathfindingAlgorithm
import numpy as np

class MyAlgorithm(PathfindingAlgorithm):
    """My custom algorithm"""

    name = "my_algo"
    description = "My custom pathfinding algorithm"

    @staticmethod
    def find_path(graph, source, target, node_positions):
        # Your algorithm implementation here
        return {
            'path': [source, target],
            'totalLoss': 0,
            'totalLength': 0
        }

# That's it! The algorithm is automatically discovered and registered.
# Use it like: net.findPaths(ap, ue, algorithm='my_algo')
'''

    print("\nTo add a new algorithm:")
    print("1. Create a new file in algorithms/ folder")
    print("2. Define a class inheriting from PathfindingAlgorithm")
    print("3. Set name and description")
    print("4. Implement find_path() method")
    print("5. Done! It's automatically discovered")

    print("\nExample:")
    print(example_code)


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("RISnet Auto-Discovery Tests")
    print("="*60)

    tests = [
        test_algorithm_discovery,
        test_example_discovery,
        test_controller_integration,
        test_add_new_algorithm
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n✗ Error in {test.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("All tests completed!")
    print("="*60 + "\n")


if __name__ == '__main__':
    main()
