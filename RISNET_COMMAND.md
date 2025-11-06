# RISNet Command-Line Interface

The `risnet` command provides a unified interface to run examples, launch the interactive CLI, and access all RISNet features.

## Installation

### Option 1: Install with pip (After Installing Package)

```bash
pip install -e .
```

Then use `risnet` anywhere:
```bash
risnet --help
risnet example_1
```

### Option 2: Run Locally (No Installation)

```bash
python3 risnet --help
python3 risnet example_1
```

## Quick Start

```bash
# Show help
risnet --help

# Show version
risnet --version

# Launch interactive CLI
risnet cli

# Run example 1
risnet example_1

# Run all examples
risnet examples
```

## Command Reference

### Help & Version

```bash
risnet --help              # Show this help message
risnet -h                  # Short form
risnet help                # Alternative

risnet --version           # Show version
risnet -v                  # Short form
risnet version             # Alternative
```

### Interactive CLI

```bash
risnet cli                 # Launch interactive CLI
```

Then you can:
```
risnet> add ap 0 0
risnet> add ris 5 0
risnet> add ue 10 3
risnet> AP1 ping UE1
risnet> AP1 rename wifi_ap
risnet> exit
```

### Run Examples

#### Run Individual Examples

```bash
risnet example_1           # Simple network creation
risnet example_2           # Predefined topology
risnet example_3           # Custom topology
risnet example_4           # Network with obstacles
risnet example_5           # Context manager pattern
risnet example_6           # Batch testing (parameter sweep)
risnet example_7           # Interactive CLI launcher
```

#### Run All Examples

```bash
risnet examples            # Run all examples (1-6)
```

## Example Usage

### Example 1: Simple Network

```bash
$ risnet example_1

============================================================
Example 1: Simple Network Creation
============================================================

*** Adding nodes
*** Starting network
Ping ap1 -> ue1
  Reachable: True
  SNR: 48.0 dB
  Hops: 2
```

### Example 2: Topology

```bash
$ risnet example_2

============================================================
Example 2: Predefined Topology
============================================================

*** Testing all UEs
ap1 -> ue1: SNR = 49.3 dB
ap1 -> ue2: SNR = 49.3 dB
ap1 -> ue3: SNR = 49.3 dB
```

### Example 3: Custom Topology

```bash
$ risnet example_3

============================================================
Example 3: Custom Topology Class
============================================================

*** Testing Y-topology
ap1 -> ris1 -> ue1: SNR = 29.0 dB
ap1 -> ris2 -> ue2: SNR = 33.4 dB
ap1 -> ris3 -> ue3: SNR = 28.8 dB
```

### Run All Examples

```bash
$ risnet examples

============================================================
RISNet - Running All Examples
============================================================

Found 6 examples:
  - example_1_simple
  - example_2_topology
  - example_3_custom_topology
  - example_4_obstacles
  - example_5_context_manager
  - example_6_batch_testing

============================================================
Starting examples...
============================================================

[Runs all 6 examples in sequence]

============================================================
Completed: 6/6 examples successful
============================================================
```

### Interactive CLI

```bash
$ risnet cli

╔════════════════════════════════════════════════════════════╗
║     RISNet v2.0 - Interactive CLI - Node Access Example   ║
╚════════════════════════════════════════════════════════════╝

This CLI allows you to create nodes and access them directly
by name, just like accessing physical devices in a network.

risnet> add ap 0 0
✓ Added AP 'AP1' at (0.0, 0.0, 0.0)

risnet> add ris 5 0
✓ Added RIS 'R1' at (5.0, 0.0, 0.0) [N=16, bits=2]

risnet> add ue 10 3
✓ Added UE 'UE1' at (10.0, 3.0, 0.0)

risnet> AP1 ping UE1
🔌 Ping: AP1 → UE1
  Status: ✓ Reachable
  SNR: 47.96 dB
  Hops: 2
  Path: AP1 → R1 → UE1

risnet> exit
```

## Examples Overview

| # | Command | Description | Features |
|---|---------|-------------|----------|
| 1 | `risnet example_1` | Simple 3-node network | Basic ping & iPerf |
| 2 | `risnet example_2` | Predefined topologies | Multiple UEs, template-based |
| 3 | `risnet example_3` | Custom Y-topology | Define custom topologies |
| 4 | `risnet example_4` | Obstacles & walls | Multiple pathfinding algorithms |
| 5 | `risnet example_5` | Context manager | Auto start/stop pattern |
| 6 | `risnet example_6` | Batch testing | Parameter sweeps, comparisons |
| 7 | `risnet cli` | Interactive CLI | Manual testing & exploration |

## Common Use Cases

### 1. Learn RISNet Basics

```bash
# Run simple example first
risnet example_1

# Then try interactive CLI
risnet cli
```

### 2. Test Network Configurations

```bash
# Run all examples to see different configurations
risnet examples
```

### 3. Interactive Experimentation

```bash
# Launch CLI for hands-on testing
risnet cli

# Create and test nodes
risnet> add ap 0 0
risnet> add ris 5 0
risnet> add ue 10 3
risnet> AP1 ping UE1
```

### 4. Parameter Sweeping

```bash
# Run batch testing example
risnet example_6
```

### 5. Custom Testing

```bash
# Modify examples for your needs
nano examples/example_1_simple.py

# Run modified version
risnet example_1
```

## Installation for System-Wide Use

To install RISNet globally so you can use `risnet` command from anywhere:

```bash
cd /mnt/c/Users/pc/Desktop/risnet
pip install -e .
```

Then you can use:
```bash
risnet --help
risnet example_1
risnet cli
```

From any directory!

## Troubleshooting

### Command Not Found

```bash
# Use python3 prefix
python3 risnet example_1

# Or install with pip
pip install -e .
```

### Import Error

Make sure you're in the project directory:
```bash
cd /mnt/c/Users/pc/Desktop/risnet
python3 risnet example_1
```

### Example Not Found

Check available examples:
```bash
risnet --help
```

Valid examples: 1, 2, 3, 4, 5, 6, 7, examples

## Advanced Usage

### Run Example and Save Output

```bash
python3 risnet example_1 > output.txt 2>&1
```

### Run All Examples and Save Results

```bash
python3 risnet examples > all_results.txt 2>&1
```

### Time Example Execution

```bash
time python3 risnet example_1
```

### Debug Example

```bash
python3 -u risnet example_1
```

## Creating Custom Examples

1. Create a new file in `examples/` directory:
   ```python
   # examples/example_custom.py
   def run():
       from risnet import RISnet
       # Your code here

   if __name__ == '__main__':
       run()
   ```

2. Run it:
   ```bash
   python3 examples/example_custom.py
   ```

Note: To use with `risnet` command, file must be named `example_*.py` with a `run()` function.

## Environment Variables

Set working directory if needed:
```bash
cd /path/to/risnet
python3 risnet example_1
```

## Summary

| Task | Command |
|------|---------|
| Show help | `risnet --help` |
| Show version | `risnet --version` |
| Interactive CLI | `risnet cli` |
| Run example 1 | `risnet example_1` |
| Run example 2 | `risnet example_2` |
| ... | `risnet example_3` through `example_6` |
| Run all examples | `risnet examples` |
| Install globally | `pip install -e .` |

Everything you need to explore and experiment with RISNet!
