# RISNet Examples Guide

This guide shows you how to run and understand all the examples in the RISNet project.

## Quick Start - Run All Examples

```bash
python3 examples/run_all.py
```

This automatically discovers and runs all example files (7 examples total).

## Individual Examples

You can also run individual examples:

```bash
python3 examples/example_1_simple.py
python3 examples/example_2_topology.py
python3 examples/example_3_custom_topology.py
python3 examples/example_4_obstacles.py
python3 examples/example_5_context_manager.py
python3 examples/example_6_batch_testing.py
python3 examples/example_interactive_cli.py
```

## Examples Overview

### Example 1: Simple Network Creation
**File:** `example_1_simple.py`

Basic usage of RISNet with manual node creation.

```bash
python3 examples/example_1_simple.py
```

**What it does:**
- Creates a simple 3-node network (1 AP, 1 RIS, 1 UE)
- Tests connectivity with ping
- Tests throughput with iPerf
- Shows basic API usage

**Key concepts:**
```python
from risnet import RISnet

net = RISnet()
ap = net.addAP('ap1', position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue = net.addUE('ue1', position=(10, 3))

net.start()
result = net.ping(ap, ue)
net.stop()
```

---

### Example 2: Predefined Topology
**File:** `example_2_topology.py`

Uses predefined topology templates.

```bash
python3 examples/example_2_topology.py
```

**What it does:**
- Uses SingleRISTopo (1 AP, 1 RIS, multiple UEs)
- Tests connectivity to all UEs
- Demonstrates topology-based network creation

**Key concepts:**
```python
from risnet import RISnet, SingleRISTopo

topo = SingleRISTopo()
topo.build(n=3)  # 3 UEs

net = RISnet(topo=topo)
net.start()
```

---

### Example 3: Custom Topology Class
**File:** `example_3_custom_topology.py`

Creates a custom Y-shaped topology.

```bash
python3 examples/example_3_custom_topology.py
```

**What it does:**
- Defines a custom Y-topology class
- 1 AP connects to 3 RIS nodes
- Each RIS connects to 1 UE
- Tests all paths in the network

**Key concepts:**
```python
from risnet import RISnet, Topology

class YTopology(Topology):
    def build(self):
        self.addAP('ap1', position=(0, 0))
        self.addRIS('ris1', position=(2, 2))
        self.addRIS('ris2', position=(2, 0))
        self.addRIS('ris3', position=(2, -2))
        self.addUE('ue1', position=(4, 2))
        self.addUE('ue2', position=(4, 0))
        self.addUE('ue3', position=(4, -2))

topo = YTopology()
topo.build()
net = RISnet(topo=topo)
```

---

### Example 4: Network with Obstacles
**File:** `example_4_obstacles.py`

Demonstrates pathfinding with obstacles/walls.

```bash
python3 examples/example_4_obstacles.py
```

**What it does:**
- Creates network with walls/obstacles
- Adds walls to block direct paths
- Tests multiple pathfinding algorithms
- Shows how RIS enables routing around obstacles

**Key concepts:**
```python
net.addWall(start=(4, -3), end=(4, 3), attenuation_dB=30)

paths = net.findPaths(ap, ue, algorithm='dijkstra')
paths = net.findPaths(ap, ue, algorithm='astar')
paths = net.findPaths(ap, ue, algorithm='greedy')
```

---

### Example 5: Context Manager (Auto Start/Stop)
**File:** `example_5_context_manager.py`

Uses Python context managers for automatic network lifecycle.

```bash
python3 examples/example_5_context_manager.py
```

**What it does:**
- Uses `with` statement for automatic start/stop
- Network starts when entering context
- Network stops when exiting context
- Cleaner, safer code

**Key concepts:**
```python
with RISnet(topo=topo) as net:
    result = net.ping(ap, ue)
    # Network automatically stops at end
```

---

### Example 6: Batch Testing (Parameter Sweep)
**File:** `example_6_batch_testing.py`

Runs multiple experiments with different configurations.

```bash
python3 examples/example_6_batch_testing.py
```

**What it does:**
- Tests different RIS array sizes (8x8, 16x16, 32x32)
- Tests different quantization bits (1, 2, 3)
- Measures SNR for each configuration
- Compares performance across configurations

**Key concepts:**
```python
configs = [
    (8, 1),    # 8x8 array, 1-bit quantization
    (16, 2),   # 16x16 array, 2-bit quantization
    (32, 3),   # 32x32 array, 3-bit quantization
]

for N, bits in configs:
    ris = net.addRIS('ris1', position=(5, 0), N=N, bits=bits)
    result = net.ping(ap, ue)
    print(f"N={N}, bits={bits}: SNR={result['snr_dB']:.1f} dB")
```

---

### Example 7: Interactive CLI
**File:** `example_interactive_cli.py`

Launches the interactive CLI for manual network simulation.

```bash
python3 examples/example_interactive_cli.py
```

**What it does:**
- Starts the interactive RISNet CLI
- Allows manual node creation and manipulation
- Supports all CLI commands (ping, iperf, findpaths, etc.)
- Supports rename command for nodes

**Key commands in CLI:**
```
risnet> add ap 0 0
risnet> add ris 5 0
risnet> add ue 10 3
risnet> AP1 ping UE1
risnet> AP1 iperf UE1
risnet> AP1 rename wifi_ap
risnet> exit
```

---

## Running Examples in Batch

### Run All Examples at Once
```bash
python3 examples/run_all.py
```

### Run Specific Examples
```bash
# Run only simple example
python3 examples/example_1_simple.py

# Run topology examples
python3 examples/example_2_topology.py
python3 examples/example_3_custom_topology.py
```

### Capture Output to File
```bash
python3 examples/run_all.py > results.txt 2>&1
```

## Example Output Files

All examples produce structured output showing:
- Network configuration
- Node information
- Connectivity results
- Path information
- Performance metrics

Example output:
```
============================================================
Example 1: Simple Network Creation
============================================================

*** Adding nodes
*** Starting network
*** Testing connectivity
Ping ap1 -> ue1
  Reachable: True
  SNR: 48.0 dB
  Hops: 2
```

## Common Patterns

### Pattern 1: Create, Test, Stop
```python
from risnet import RISnet

net = RISnet()
net.addAP('ap1', position=(0, 0))
net.addRIS('ris1', position=(5, 0))
net.addUE('ue1', position=(10, 3))

net.start()
result = net.ping(net.aps['ap1'], net.ues['ue1'])
print(f"SNR: {result['snr_dB']:.1f} dB")
net.stop()
```

### Pattern 2: Topology-Based
```python
from risnet import RISnet, SingleRISTopo

topo = SingleRISTopo()
topo.build(n=3)  # 3 UEs

with RISnet(topo=topo) as net:
    ap = net.aps['ap1']
    for ue_name in ['ue1', 'ue2', 'ue3']:
        result = net.ping(ap, net.ues[ue_name])
```

### Pattern 3: Batch Parameter Sweep
```python
for param in [8, 16, 32]:
    net = RISnet()
    net.addRIS('ris1', N=param)
    net.start()
    # Test...
    net.stop()
```

## CLI Examples

### Start Interactive CLI
```bash
python3 examples/example_interactive_cli.py
```

### Typical CLI Session
```
risnet> add ap 0 0
✓ Added AP 'AP1'

risnet> add ris 5 0
✓ Added RIS 'R1'

risnet> add ue 10 3
✓ Added UE 'UE1'

risnet> AP1 rename wifi_ap
✓ Renamed AP 'AP1' to 'wifi_ap'

risnet> wifi_ap ping UE1
🔌 Ping: wifi_ap → UE1
  Status: ✓ Reachable
  SNR: 48.0 dB

risnet> wifi_ap rename access_point
✓ Renamed AP 'wifi_ap' to 'access_point'

risnet> exit
```

## Tips and Tricks

### Run Examples Silently (No Output)
```bash
python3 examples/example_1_simple.py > /dev/null 2>&1
```

### Time Examples
```bash
time python3 examples/run_all.py
```

### Debug Single Example
```bash
python3 -u examples/example_3_custom_topology.py
```

### Modify and Run Example
```bash
# Edit example file
nano examples/example_1_simple.py

# Run modified version
python3 examples/example_1_simple.py
```

## Creating Your Own Example

Create a new file `examples/example_custom.py`:

```python
"""
My Custom Example
"""

from risnet import RISnet

def run():
    """Run my example"""
    print("\n" + "="*60)
    print("My Custom Example")
    print("="*60)

    net = RISnet()

    # Your code here
    ap = net.addAP('ap1', position=(0, 0))
    ris = net.addRIS('ris1', position=(5, 0))
    ue = net.addUE('ue1', position=(10, 3))

    net.start()
    result = net.ping(ap, ue)
    print(f"Result: {result}")
    net.stop()

if __name__ == '__main__':
    run()
```

Then run it:
```bash
python3 examples/example_custom.py
```

Or add it to run_all.py by naming it `example_*.py` - it will be auto-discovered!

## Troubleshooting

### Import Error
```
ImportError: No module named 'risnet'
```
**Solution:** Make sure you're in the project root directory:
```bash
cd /mnt/c/Users/pc/Desktop/risnet
python3 examples/example_1_simple.py
```

### Examples Slow
- Exhaustive pathfinding is slow for large networks
- Use dijkstra or astar for faster results
- Reduce network size for quicker runs

### All Examples Completed?
Look for: "All examples completed!" message at the end of `run_all.py`

## Summary

- **Run all:** `python3 examples/run_all.py`
- **Run one:** `python3 examples/example_1_simple.py`
- **Interactive CLI:** `python3 examples/example_interactive_cli.py`
- **Create custom:** Add new `example_*.py` file

Each example demonstrates different aspects of RISNet from simple usage to advanced features!
