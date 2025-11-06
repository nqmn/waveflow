"""
Run all examples

Automatically discovers and runs all example_*.py files.
"""

import importlib
import pkgutil
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def discover_examples():
    """Discover all example modules"""
    import examples

    example_modules = []

    for importer, modname, ispkg in pkgutil.iter_modules(examples.__path__):
        if modname.startswith('example_') and not ispkg:
            example_modules.append(modname)

    return sorted(example_modules)


def run_all():
    """Run all discovered examples"""
    print("\n" + "="*60)
    print("RISnet Examples - Running All")
    print("="*60)

    examples = discover_examples()

    print(f"\nFound {len(examples)} examples:")
    for ex in examples:
        print(f"  - {ex}")

    print("\n" + "="*60)
    print("Starting examples...")
    print("="*60)

    for example_name in examples:
        try:
            # Import module
            module = importlib.import_module(f'examples.{example_name}')

            # Run example
            if hasattr(module, 'run'):
                module.run()
            else:
                print(f"\nWarning: {example_name} has no run() function")

        except Exception as e:
            print(f"\n*** Error in {example_name}: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60 + "\n")


if __name__ == '__main__':
    run_all()
