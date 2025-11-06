# Getting Started with RISNet Node Access CLI

You now have the ability to access all nodes directly from the CLI, just like accessing devices in a network!

## Quick Start

### Launch the Interactive CLI

```bash
python3 examples/example_interactive_cli.py
```

Or directly:
```bash
python3 -c "from risnet import RISnet; from risnet_cli import RISnetCLI; cli = RISnetCLI(RISnet()); cli.cmdloop()"
```

### Create Your First Network

You can create nodes with **auto-generated names** (easiest):

```
risnet> add ap 0 0           # Creates AP1 at (0, 0)
risnet> add ris 5 0          # Creates R1 at (5, 0)
risnet> add ue 10 3          # Creates UE1 at (10, 3)
risnet> list
```

Or with **explicit custom names**:

```
risnet> add ap ap1 0 0       # Creates AP named 'ap1'
risnet> add ris ris1 5 0     # Creates RIS named 'ris1'
risnet> add ue ue1 10 3      # Creates UE named 'ue1'
risnet> list
```

Output:
```
📍 Access Points (1):
  ap1  pos=(0.0, 0.0, 0.0)  power=20.0 dBm  freq=5.8 GHz

📡 RIS Surfaces (1):
  ris1 pos=(5.0, 0.0, 0.0)  N=16x16  bits=2  angle=60°

📱 User Equipment (1):
  ue1  pos=(10.0, 3.0, 0.0)
```

### Access Nodes by Name

Now access your nodes directly by their auto-generated names:

```
# Show AP information
risnet> AP1 info
📌 Node: AP1
  Type: AccessPoint
  Position: (0.000, 0.000, 0.000) m
  Power: 20.0 dBm
  Frequency: 5.8 GHz

# Test connectivity from AP to UE
risnet> AP1 ping UE1
🔌 Ping: AP1 → UE1
  Status: ✓ Reachable
  SNR: 47.96 dB
  Hops: 2
  Path: AP1 → R1 → UE1

# Test throughput
risnet> AP1 iperf UE1
📊 iPerf: AP1 → UE1
  Throughput: 318.67 Mbps
  SNR: 47.96 dB
  Bandwidth: 20 MHz

# Find all paths to reach UE from AP
risnet> AP1 findpaths UE1
🗺️  Paths: AP1 → UE1 [DIJKSTRA]

  Path 1: AP1 → R1 → UE1
    Type: reflected
    SNR: 47.96 dB
    Hops: 2

  Path 2: AP1 → UE1
    Type: direct
    SNR: 42.90 dB
    Hops: 1

# Setup RIS-assisted connection with beam steering
risnet> AP1 connect R1 UE1
🔗 Connect: AP1 → R1 → UE1
  SNR: 34.32 dB
  Power: -56.67 dBm
  Beam Angle: 31.0°
  Status: ✓ Connected
```

## Command Reference

### Add Nodes
```
add ap <name> <x> <y>                 # Add Access Point
add ris <name> <x> <y> [N] [bits]     # Add RIS
add ue <name> <x> <y>                 # Add User Equipment
```

### Access Nodes
```
<node>                                 # Show node info
<node> info                            # Detailed info
<node> ping <target>                   # Test connectivity
<node> iperf <target>                  # Test throughput
<node> findpaths <target> [algo]       # Find paths
<ap> connect <ris> <ue>                # RIS-assisted connection
<node> position <x> <y> [z]            # Update position
```

### Network Management
```
list [type]                            # List nodes
start                                  # Start network
stop                                   # Stop network
clear                                  # Remove all nodes
help                                   # Show help
exit                                   # Exit CLI
```

## Path Finding Algorithms

- **dijkstra** (default) - Optimal, medium speed
- **astar** - Optimal, fast
- **greedy** - Suboptimal, very fast
- **exhaustive** - All paths, slow

Example:
```
risnet> ap1 findpaths ue1 dijkstra
risnet> ap1 findpaths ue1 astar
risnet> ap1 findpaths ue1 greedy
```

## Real-World Example: Multi-Hop Network

```
# Create a 4-node network with two relay points
risnet> add ap ap1 0 0
risnet> add ris ris1 4 0
risnet> add ris ris2 8 0
risnet> add ue ue1 12 0

risnet> list
📍 Access Points (1):
  ap1   pos=(0.0, 0.0, 0.0)

📡 RIS Surfaces (2):
  ris1  pos=(4.0, 0.0, 0.0)
  ris2  pos=(8.0, 0.0, 0.0)

📱 User Equipment (1):
  ue1   pos=(12.0, 0.0, 0.0)

# Find all paths - will show direct and multi-hop
risnet> ap1 findpaths ue1
🗺️  Paths: ap1 → ue1 [DIJKSTRA]
  Path 1: ap1 → ris1 → ris2 → ue1
    Type: relay
    SNR: 45.2 dB
    Hops: 3
  Path 2: ap1 → ris1 → ue1
    Type: relay
    SNR: 40.1 dB
    Hops: 2
  Path 3: ap1 → ue1
    Type: direct
    SNR: 30.5 dB
    Hops: 1

# Test which path gives best throughput
risnet> ap1 iperf ue1
```

## Advanced: Dynamic Network Adjustment

```
# Start with a network
risnet> add ap ap1 0 0
risnet> add ue ue1 20 0
risnet> ap1 ping ue1
# May have poor SNR due to distance

# Add a RIS in the middle
risnet> add ris ris1 10 0
risnet> ap1 ping ue1
# Should have better SNR now

# Adjust AP position
risnet> ap1 position 1 1
risnet> ap1 ping ue1
# Check new SNR with adjusted position

# Fine-tune RIS position
risnet> ris1 position 9.5 0.5
risnet> ap1 ping ue1
# Optimize network layout
```

## Troubleshooting

### "Node not found"
```
risnet> ap1 info
Error: Node 'ap1' not found
```
**Solution:** Use `list` to check available nodes. Make sure you spelled the name correctly.

### "No paths found"
```
risnet> ap1 findpaths ue1
  No paths found
```
**Solution:** Nodes might be too far apart (beyond propagation range). Try adding RIS nodes as relays between them.

### "Connection failed"
```
risnet> ap1 connect ris1 ue1
Error during connect: ...
```
**Solution:** Make sure all three nodes (AP, RIS, UE) exist and are properly created.

## More Information

- **Full documentation**: See `docs/CLI_NODE_ACCESS.md`
- **Quick reference**: See `docs/CLI_QUICK_REFERENCE.md`
- **Examples**: Check `examples/example_interactive_cli.py`
- **Test suite**: Run `python3 test_cli.py`

## Next Steps

Now that you can access nodes directly, you can:

1. **Build complex topologies** - Create networks with multiple APs, RIS, and UEs
2. **Analyze path diversity** - Compare different routing algorithms
3. **Optimize positions** - Dynamically adjust network layout for better performance
4. **Test scenarios** - Create realistic network conditions and test behavior
5. **Debug connectivity** - Use ping and findpaths to understand network issues

Happy networking! 🚀
