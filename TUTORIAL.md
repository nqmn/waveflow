# Waveflow Tutorial

This tutorial is structured in two tiers:

- **Beginner** (Parts 1–4) — concepts, analogies, and simple examples. No prior wireless engineering knowledge required. Suitable for final-year undergraduates and researchers new to RIS.
- **Advanced** (Parts 5–17) — full API, physics models, waveform simulation, ML-guided optimization, scenario runner, and custom algorithm development. Suitable for researchers and engineers.

---

# Installation

For full installation instructions, optional extras, virtual environment setup, verification steps, and troubleshooting, see **[INSTALL.md](INSTALL.md)**.

Quick start:

```bash
# From PyPI
pip install waveflow-sim

# From source (recommended for development)
git clone https://github.com/nqmn/waveflow
cd waveflow
pip install -e ".[terminal]"   # core + waveflow ui commands
```

Verify with:

```bash
python3 - <<'PY'
from core import RISNetwork
net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 2)
net.add_ris('ris1', 5, 2, max_angle_deg=90)
net.add_ue('ue1', 10, 5)
result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print('OK — snr_dB:', round(result['snr_dB'], 2))
PY
```

```
OK — snr_dB: 29.9
```

## Engine Model

Waveflow currently exposes two official channel engines:

| Engine | Purpose | Typical workflows |
|---|---|---|
| `simris` | Published/reference stochastic channel model | reference channel evaluation, supported `H/G/D` connect scenarios |
| `lightris` | Native analytical RIS engine | sweep, tapering, feedback, fast system studies, ML data generation |

Important rules:
- `connect()` is **SimRIS-first** by default.
- If a request is outside SimRIS support, Waveflow falls back explicitly to `lightris`.
- The fallback is surfaced in both Python results and `waveflow ui` output.
- Sweep / tapering / feedback remain `LightRIS`-native by design.

---

# Beginner Tier

---

## Part 1 — Understanding the System

### 1.1 What Is Waveflow Simulating?

Imagine you are in a large building and your Wi-Fi signal from the router (Access Point) cannot reach your laptop (User Equipment) because there is a concrete wall in the way.

A **Reconfigurable Intelligent Surface (RIS)** is a flat panel covered with small programmable antenna elements — think of it as a **smart mirror for radio signals**. Instead of absorbing or randomly scattering the signal, the RIS reflects it in a specific direction that you control, guiding the signal around obstacles to reach the target device.

```
Without RIS:
  [AP] ----X---- wall ----X---- [UE]    ← signal blocked

With RIS:
  [AP] ---------> [RIS] ---------> [UE]  ← signal reflected around obstacle
```

Waveflow lets you:

**Network setup**
- Place nodes (AP, RIS, UE) in 2D or 3D space with configurable parameters
- Add walls and obstacles with per-wall attenuation
- Load and save network topologies from JSON or YAML files
- Generate random RIS-aware topologies automatically

**Signal computation**
- Compute received SNR, power, and path loss across a RIS-assisted link
- Apply realistic physics: free-space path loss, atmospheric absorption, Rician fading, mutual coupling
- Simulate waveform-level OFDM signals and measure per-subcarrier SNR
- Model phase quantization loss for 1–4 bit RIS phase shifters

**Beam control**
- Search for the best RIS beam angle using multiple sweep algorithms (linear, coarse-fine, differential evolution, ML-guided)
- Run closed-loop feedback where the UE reports SNR back to adapt the beam
- Estimate UE location from beam response measurements (localization sweep modes)

**Pathfinding**
- Find the best route through a multi-hop RIS network (Dijkstra, A\*, greedy, exhaustive)
- Compute link quality along each hop of the path

**Streaming and throughput**
- Simulate a live data stream over an active RIS link and measure per-chunk BER and throughput
- Estimate Shannon capacity with and without the RIS

**Analysis and validation**
- Compare beam search algorithms side by side
- Validate physics models against published reference values
- Train and apply ML predictors for beam angle estimation
- Optionally integrate camera-based positioning (ArUco markers, HOG detection)

### 1.2 Key Terms (Plain Language)

| Term | What It Means |
|---|---|
| **AP** (Access Point) | The transmitter — like a Wi-Fi router |
| **RIS** | The smart reflector panel |
| **UE** (User Equipment) | The receiver — like a phone or laptop |
| **SNR** (Signal-to-Noise Ratio) | Signal quality at the UE. Higher is better. Above ~20 dB is good. |
| **dB / dBm** | Logarithmic units for signal strength. 3 dB ≈ double the power. |
| **Beam angle** | The direction the RIS reflects the signal toward |
| **Beam sweep** | Searching through angles to find the one with the best SNR |
| **Phase quantization** | RIS elements can only set phases in discrete steps (1-bit = 2 steps, 2-bit = 4 steps). More bits = less error. |
| **FOV** (Field of View) | The angular range the RIS can "see". AP and UE must both fall within this cone. |
| **Path loss** | Signal weakening over distance. Doubles every time distance increases by a factor. |

### 1.3 How a Simulation Works (Step by Step)

Every Waveflow simulation follows the same flow:

```
1. Create a network
2. Add an AP (transmitter)
3. Add a RIS (reflector)
4. Add a UE (receiver)
5. Connect them → Waveflow computes the SNR
6. (Optional) Sweep beam angles to find the best one
```

---

## Part 2 — Your First Simulation

Waveflow gives you two CLI modes. They run the same underlying simulator — the difference is in how you interact with it:

| Mode | How it works | Best for |
|---|---|---|
| **Interactive shell** (`waveflow`) | Persistent session — type commands one at a time at a `waveflow>` prompt | Exploration, manual testing, building up a network step by step |
| **Terminal UI** (`waveflow ui`) | One-shot commands — each command runs and exits, output is formatted tables | Scripts, automation, SSH sessions, reproducible experiments |

Both are covered below. Start with the interactive shell if you are new; use `waveflow ui` when you want clean output you can copy or pipe.

---

### 2.1 Interactive Shell

Launch the shell:

```bash
waveflow
```

You will see a prompt: `waveflow>`

Now type these commands one by one:

```bash
# Step 1: Add an Access Point at position (0, 0)
waveflow> add ap ap1 0 0

# Step 2: Add a RIS at position (5, 0) with 16 elements and 2-bit phase resolution
#         max_angle_deg defaults to 60; set it wider via the ris command if needed
waveflow> add ris ris1 5 0 0 16 2

# Step 3: Add a User Equipment at position (10, 3)
waveflow> add ue ue1 10 3

# Step 4: Connect them and compute SNR
waveflow> connect ap1 ris1 ue1
```

You should see output like:

```
SNR: 29.9 dB   Power: -52.3 dBm   Beam angle: 16.7°
```

This means the signal arrived at UE1 with an SNR of ~30 dB — a strong connection.

### 2.2 What the Numbers Mean

| Output | Meaning |
|---|---|
| `SNR: 29.9 dB` | Good signal quality (>20 dB is generally usable) |
| `Power: -52.3 dBm` | Received power level at UE |
| `Beam angle: 16.7°` | The RIS steered the signal at 16.7° to reach UE |

### 2.3 Move the UE Further Away

```bash
waveflow> add ue ue2 20 5
waveflow> connect ap1 ris1 ue2
```

Notice the SNR drops because the signal travels farther — this is **path loss**.

### 2.4 Add a Wall

```bash
waveflow> add wall 3 -3 3 3 20
waveflow> connect ap1 ris1 ue1
```

The wall adds 20 dB of attenuation. The RIS helps maintain the connection by reflecting around the obstacle.

### 2.5 Add a Random Network Instantly

If you want to test without picking positions manually, `add random` generates a valid AP, RIS, and UE automatically — positions are chosen so the geometry is physically coherent (AP and UE inside RIS FOV).

```bash
waveflow> add random
```

```
ADDING RANDOM NODES TO NETWORK
Target: 1 AP(s), 1 RIS(s), 1 UE(s)
UE distance range: 5.0m - 7.0m
----------------------------------------------------------------------
✓ Added RIS R1  at (4.82, 13.34) (N=16, bits=1)
✓ Added AP AP1  at (9.69, 15.48) (RIS-aware, angle: 23.73°)
✓ Added UE UE1  at (11.56, 13.71) (RIS-aware placement)
----------------------------------------------------------------------
✓ Successfully added 3 nodes to network
```

You can also specify counts: `add random 2 1 3` adds 2 APs, 1 RIS, and 3 UEs.

### 2.6 List — View the Network Map

`list` prints an ASCII map of all nodes and their coordinates:

```bash
waveflow> list
```

```
Topology View (ASCII):
Legend: 0=AP1  1=R1  2=UE1
----------------------------------------------------
| .................................................. |
| .................................0................ |
| .................................................. |
| .............................................2.... |
| .................................................. |
| ....1............................................. |
| .................................................. |
----------------------------------------------------

Node Coordinates:
Name         Type            Position (x,y,z)
----------------------------------------------------
AP1          AccessPoint     (  9.69,  15.48,   0.00)
R1           RIS             (  4.82,  13.34,   0.00)
UE1          UE              ( 11.56,  13.71,   0.00)
```

Each node is shown as a numbered dot on the grid. Useful for visually verifying your layout before connecting.

### 2.7 Status — Full Network Summary

`status` shows node details, all pairwise distances, and active links in one view:

```bash
waveflow> status
```

```
NETWORK STATUS
======================================================================

NODES (3):
----------------------------------------------------------------------
  ap1   : AccessPoint  at (11.7, 13.5, 0.0)
      Frequency:   5.80 GHz  |  Power: 20.0 dBm  |  BW: 20.0 MHz

  ris1  : RIS          at (5.6, 10.8, 0.0)
      RIS Elements: 16  |  Phase Bits: 1

  ue1   : UE           at (13.3, 12.9, 0.0)
      Noise Figure: 6.0 dB  |  Antenna Gain: 3.0 dBi

DISTANCES:
----------------------------------------------------------------------
  ap1  ↔ ris1:     6.60 m
  ap1  ↔ ue1 :     1.70 m
  ris1 ↔ ue1 :     7.96 m

ACTIVE LINKS (1):
----------------------------------------------------------------------
  [1] ap1→ris1→ue1 (Connect)
      SNR:          17.41 dB
      Power:       -77.14 dBm
      Gain:         32.68 dBi
      Deflection:   -8.06°
      Quant Penalty: 1.67 dB

======================================================================
```

### 2.8 Links — Show Active Links Only

`links` is a focused view — it shows only the established connections, without the full node table:

```bash
waveflow> links
```

```
ACTIVE LINKS
======================================================================

ACTIVE LINKS (1):
----------------------------------------------------------------------
  [1] ap1→ris1→ue1 (Connect)
      Source:                   Connect
      SNR:                      17.41 dB
      Power:                   -77.14 dBm
      Gain:                     32.68 dBi
      Steering Angle:           -8.06°
      Quant Penalty:             1.67 dB

======================================================================
```

### 2.9 Clear — Remove Links or the Whole Network

`clear links` removes all active connections but keeps the nodes in place — useful when you want to re-run a connect with different parameters:

```bash
waveflow> clear links
```

```
✓ Cleared 1 active link(s) (nodes kept)
```

`clear` (without arguments) wipes everything — nodes and links:

```bash
waveflow> clear
```

```
✓ Cleared entire network (nodes + links)
```

### 2.10 Plot — Visualise Sweep or Connect Results

`plot` renders a chart of your most recent sweep or connect result. It requires `matplotlib` (`pip install -e ".[plot]"`). The chart is saved to a file if `--out` is specified, or displayed in a window otherwise.

```bash
# Plot the last sweep result
waveflow> plot

# Plot the last connect result
waveflow> plot --type connect

# Save to file instead of displaying
waveflow> plot --out sweep_chart.png
```

If no stored result exists yet, you will see:

```
✗ No stored sweep results found. Run and save a sweep first.
```

Run a sweep first (`sweep ap1 ris1 ue1 60 10`), then `plot` will render it.

### 2.11 Save and Load — Persist Your Network

`save` writes the current network (all nodes, walls, and links) to a JSON file so you can reload it later. Without a filename it saves to the default `.risnet_network.json`, which is also loaded automatically on the next startup.

```bash
# Save to default file (auto-loaded on next startup)
waveflow> save
```

```
✓ Network saved to .risnet_network.json
```

```bash
# Save to a named file
waveflow> save mynet.json
```

```
✓ Network saved to mynet.json
```

`load` reads a saved file back into the current session, replacing whatever is in memory. This is useful for switching between experiments without retyping all your `add` commands.

```bash
waveflow> clear
waveflow> load mynet.json
waveflow> status
```

```
✓ Network loaded from mynet.json

NETWORK STATUS
======================================================================

NODES (3):
----------------------------------------------------------------------
  ap1   : AccessPoint  at (0.2, 0.7, 0.0)   | power=20.0 dBm
  ris1  : RIS          at (14.5, 2.0, 0.0)  | N=16, bits=1
  ue1   : UE           at (20.2, -1.8, 0.0) | NF=6.0 dB

DISTANCES:
----------------------------------------------------------------------
  ap1  ↔ ris1:    14.38 m
  ap1  ↔ ue1 :    20.19 m
  ris1 ↔ ue1 :     6.88 m

✗ No active links
======================================================================
```

Loading without a filename (`load`) reads from `.risnet_network.json`. Topology files in `examples/json/` can also be loaded directly:

```bash
waveflow> load examples/json/example_1_simple.json
```

### 2.12 Viewing All Shell Commands

```bash
waveflow> help
```

Exit the shell with `quit` or Ctrl-D.

---

### 2.13 Terminal UI (`waveflow ui`)

`waveflow ui` has two operating styles:

- one-shot commands that load a topology, run, and exit
- a native interactive modern shell via `waveflow ui shell`

Both styles use Rich output. The one-shot form is suitable for scripts, CI, and reproducible runs. The shell form is better when you want persistent state across multiple commands without dropping back to the legacy shell.

See what commands are available:

```bash
waveflow ui --help
```

```
Commands:
  status        Show network status with Rich tables.
  list          List all nodes in the network.
  add           Add a node (ap, ris, or ue) to the network.
  connect       Compute a cascaded AP→RIS→UE link and display metrics.
  sweep         Run a beam sweep and display the best angle and SNR.
  save          Save current network state to disk.
  load          Load network state from disk and display it.
  clear         Clear the network (nodes + links) or active links only.
  demo-connect  Run a deterministic AP-RIS-UE demo link and print metrics.
  testall       Run the comprehensive test suite and display results.
  testphysics   Run the physics model validation suite and display results.
  shell         Open the interactive shell (access to all legacy commands).
  run           Run any legacy CLI command non-interactively.
```

Every command accepts `--help` for usage details.

Common patterns:

```bash
# One-shot from a topology file
waveflow ui status --topology examples/json/example_1_simple.json

# Native interactive shell with persistent state
waveflow ui shell
waveflow ui> load examples/json/example_1_simple.json
waveflow ui> status
waveflow ui> connect AP1 R1 UE1
```

### 2.14 Status — Inspect a Topology (`waveflow ui`)

```bash
waveflow ui status --topology examples/json/example_1_simple.json
```

`status` now shows the same core information as the legacy shell, but rendered natively with Rich:

- a full node table
- pairwise distances
- active-link metrics when links exist

This makes `waveflow ui status` suitable for both quick inspection and report-friendly terminal output.

### 2.15 Connect — Compute SNR Without Entering the Shell

```bash
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json
```

`connect` now renders several Rich sections instead of a single short table:

- `Connect Context` for AP/RIS/UE names and simulation mode
- `Connect Diagnostics` for coordinates, distances, azimuths, and RIS deflection
- `Link Result` for SNR, power, gain, and beam metrics
- `RIS Recommendation` for the steering command summary

This is the same command surface used inside `waveflow ui shell`, so the one-shot and interactive experiences stay aligned.

You can also select the engine explicitly:

```bash
# Reference stochastic engine
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --channel-model simris --environment indoor --scenario 1

# Native analytical engine
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --channel-model lightris
```

When fallback happens, the output now shows:
- `Engine requested`
- `Engine used`
- `Engine fallback`

### 2.16 Connect — Full Command Reference

The `connect` command has several modes beyond the basic three-node form. All variants work in both the interactive shell and `waveflow ui`.

**Basic form — auto beam angle:**

```bash
waveflow> connect ap1 ris1 ue1
```

The RIS steering angle is computed automatically from the geometry.

**Explicit beam angle (`--beam`):**

```bash
waveflow> connect ap1 ris1 ue1 --beam 30.0
```

Forces the RIS to steer at exactly 30°. Useful when you already know the optimal angle and want to skip computation.

**Sweep during connect (`--sweep`):**

```bash
# Default: ±60° FOV, 10° step, linear algorithm
waveflow> connect ap1 ris1 ue1 --sweep

# Custom FOV and step
waveflow> connect ap1 ris1 ue1 --sweep 45 5

# Choose sweep algorithm
waveflow> connect ap1 ris1 ue1 --sweep 60 10 --algo coarse-fine
waveflow> connect ap1 ris1 ue1 --sweep 60 10 --algo de
waveflow> connect ap1 ris1 ue1 --sweep 60 10 --algo ml-guided --ml-predictor rf
```

`--sweep` alone defaults to `fov=60, step=10`. The algorithm defaults to `linear` unless `--algo` is specified.

**Available `--algo` values with `--sweep`:**

| Value | Description |
|---|---|
| `linear` | Uniform step sweep (default) |
| `coarse-fine` | Two-phase refinement |
| `de` | Differential Evolution global search |
| `ml-guided` | ML-predicted seed angles (requires trained models) |
| `hierarchical` | Multi-resolution sweep |
| `adaptive-directional` | Adaptive directional refinement |

**`--ml-predictor` values (only with `--algo ml-guided`):**

`rf`, `xgb`, `svr`, `knn`, `lgbm`, `lr` — defaults to `gmf`.

**Signal and modulation options:**

```bash
# Disable waveform-level simulation (faster, physics-only)
waveflow> connect ap1 ris1 ue1 --no-waveform

# Change modulation scheme
waveflow> connect ap1 ris1 ue1 --modulation QPSK

# Apply tapering window to RIS phase weights
waveflow> connect ap1 ris1 ue1 --tapering hamming
```

`--tapering` accepts: `uniform` (default), `hamming`, `hann`, `blackman`.

**Engine selection:**

```bash
# Default behavior: request SimRIS first
waveflow> connect ap1 ris1 ue1

# Force SimRIS explicitly
waveflow> connect ap1 ris1 ue1 --channel-model simris --environment indoor --scenario 1

# Force LightRIS explicitly
waveflow> connect ap1 ris1 ue1 --channel-model lightris
```

Notes:
- `--environment` and `--scenario` matter only for `simris`
- if a SimRIS request is unsupported, the command falls back to `lightris` with an explicit reason
- explicit beam steering, tapering-heavy connect flows, and feedback-heavy control flows are intentionally `LightRIS`-native today

**Feedback control:**

```bash
# Disable the UE→AP CSI feedback loop
waveflow> connect ap1 ris1 ue1 --no-feedback
```

Feedback is enabled by default. Use `--no-feedback` for open-loop experiments.

**Reproducibility:**

```bash
waveflow> connect ap1 ris1 ue1 --seed 42
```

Locks the random seed for fading and noise — ensures identical results across runs.

**Terminal UI equivalents:**

```bash
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --beam 30.0
waveflow ui connect AP1 R1 UE1 30 --topology examples/json/example_1_simple.json
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json --sweep 60 10 --algo coarse-fine
```

The terminal UI accepts the same legacy `connect` grammar for the main modes, including positional beam-angle forms and `--sweep` variants, but renders the result through the modern Rich layout.

### 2.17 Sweep — Find the Best Beam Angle

```bash
waveflow ui sweep AP1 R1 UE1 --topology examples/json/example_1_simple.json --fov 60 --step 10
```

A live progress bar runs during the sweep, then the results table appears:

```
╭───────────────────── Live Sweep ──────────────────────╮
│   fine ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 11/11 0:00:00 │
╰───────────────────────────────────────────────────────╯

Sweep Result (coarse-fine)
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric               ┃  Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Best angle (deg)     │  60.00 │
│ Best SNR (dB)        │ -13.81 │
│ Coarse angles tested │     13 │
│ Fine angles tested   │     11 │
└──────────────────────┴────────┘

Top 5 Sweep Measurements
┏━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Rank ┃ Phase  ┃ Angle (deg) ┃ SNR (dB) ┃
┡━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━┩
│    1 │ coarse │       60.00 │   -13.81 │
│    2 │ fine   │       60.00 │   -13.81 │
│    3 │ fine   │       59.00 │   -15.08 │
│    4 │ fine   │       58.00 │   -16.37 │
│    5 │ fine   │       57.00 │   -17.68 │
└──────┴────────┴─────────────┴──────────┘
```

### 2.18 Stream — Simulate a Live Data Stream

`stream` simulates a continuous data transmission over the active RIS link, printing per-chunk throughput as it runs. It shows how the RIS-assisted link performs as a streaming medium — think of it like running a real-time bandwidth test.

```bash
waveflow> connect ap1 ris1 ue1
waveflow> stream ap1 ris1 ue1
```

```
[Streaming over ap1→ris1→ue1]
  Chunk 01: SNR=-49.75 dB | BER=61.75% | Tput=3.06 Mbps | Time=0.036s
  Chunk 02: SNR=-50.08 dB | BER=61.79% | Tput=3.06 Mbps | Time=0.034s
  Chunk 03: SNR=-50.52 dB | BER=63.13% | Tput=2.95 Mbps | Time=0.031s
  Chunk 04: SNR=-48.55 dB | BER=56.73% | Tput=3.46 Mbps | Time=0.030s
  Chunk 05: SNR=-46.65 dB | BER=47.46% | Tput=4.20 Mbps | Time=0.031s
  Chunk 06: SNR=-46.62 dB | BER=48.78% | Tput=4.10 Mbps | Time=0.030s

Summary:
  Chunks sent:     6
  Avg throughput:  3.47 Mbps
  Payload/chunk:   8,000 bits (1,000 bytes)
```

The stream command uses waveform-level simulation (OFDM + 16QAM) rather than the simplified link budget. See Part 13 for a full streaming scenario with capacity analysis.

### 2.19 When to Use Which

Choose based on your workflow:

```
Exploring a new topology?          → waveflow           (interactive shell)
Running the same command in CI?    → waveflow ui connect (one-shot)
Demoing to someone over SSH?       → waveflow ui shell   (modern interactive shell)
Need direct Rich output from JSON? → waveflow ui status/list/connect
Need one-off legacy compatibility? → waveflow ui run <command>
```

Engine choice rule of thumb:

```text
Need literature-style reference channel behavior?  → simris
Need fast control / sweep / feedback workflows?    → lightris
Need no special choice?                            → omit channel_model and let connect() choose
```

---

## Part 3 — Finding the Best Beam Angle

### 3.1 What Is Beam Sweeping?

The RIS does not automatically know the best angle to reflect toward the UE. **Beam sweeping** is the process of testing multiple angles and picking the one with the highest SNR — like turning a flashlight until you find the brightest spot on a wall.

```bash
# Search ±60° around the specular direction in 10° steps
waveflow> sweep ap1 ris1 ue1 60 10
```

Output shows each angle tested and the SNR. The best angle is highlighted.

### 3.2 Comparing Sweep Algorithms

Different algorithms find the best angle in different ways:

```bash
# Slow but thorough — tests every angle uniformly
waveflow> sweep ap1 ris1 ue1 60 10 --algo linear

# Faster — starts near the predicted specular angle
waveflow> sweep ap1 ris1 ue1 60 10 --algo coarse-fine

# Global search — good when there are multiple good angles
waveflow> sweep ap1 ris1 ue1 60 10 --algo de
```

| Algorithm | Speed | Best For |
|---|---|---|
| `linear` | Slow | Thorough baseline comparison |
| `coarse-fine` | Fast | General use (default) |
| `de` | Medium | Complex environments with multiple paths |
| `ml-guided` | Fastest (once trained) | Repeated deployments with similar geometry |

### 3.3 Viewing All Commands

```bash
waveflow> help
```

---

## Part 4 — Python API for Beginners

### 4.1 Simple Script

You can run simulations from a Python script instead of the CLI:

```python
from waveflow import RISnet

# Create the network
net = RISnet()

# Add nodes
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))

# Start the simulator
net.start()

# Check connectivity and SNR (like a ping test)
result = net.ping(ap, ue)
print(f"Reachable: {result['reachable']}")
print(f"SNR:       {result['snr_dB']:.1f} dB")
print(f"Hops:      {result['hops']}")

# Estimate throughput (like iperf)
throughput = net.iperf(ap, ue)
print(f"Throughput: {throughput['throughput_Mbps']:.1f} Mbps")

net.stop()
```

### 4.2 RIS Field of View (FOV)

The RIS has a limited field of view — both the AP and UE must fall within its angular cone. The default FOV is ±60°. If either node is outside, the connection will be rejected.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)  # ±90° FOV
net.add_ue('ue1', 10, 3)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"SNR: {result['snr_dB']:.1f} dB")
```

Setting `max_angle_deg=90` gives the RIS a ±90° cone, which comfortably covers
collinear AP→RIS→UE layouts where AP is behind the RIS.

### 4.3 Comparing Two Configurations

```python
from core import RISNetwork

configs = [
    {'N': 16, 'bits': 1},
    {'N': 16, 'bits': 2},
    {'N': 32, 'bits': 2},
]

for cfg in configs:
    net = RISNetwork(enable_messaging=False)
    net.add_ap('ap1', 0, 0)
    net.add_ris('ris1', 5, 0, max_angle_deg=90, **cfg)
    net.add_ue('ue1', 10, 3)
    result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
    print(f"N={cfg['N']:2d}, bits={cfg['bits']}: SNR={result['snr_dB']:.1f} dB")
```

Expected output:
```
N=16, bits=1: SNR=26.1 dB
N=16, bits=2: SNR=29.9 dB
N=32, bits=2: SNR=35.9 dB
```

More elements → higher array gain → better SNR. More bits → less quantization loss.

---

# Advanced Tier

---

## Part 5 — Low-Level API and Node Parameters

### 5.1 Full connect() API

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)

net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)

print(f"SNR:        {result['snr_dB']:.1f} dB")
print(f"Power:      {result['pwr_dBm']:.1f} dBm")
print(f"Beam angle: {result['beam_angle']:.1f}°")
print(f"Array gain: {result['gain_dBi']:.1f} dBi")
print(f"Quant loss: {result['quant_loss_dB']:.2f} dB")
```

**`connect()` result keys** (selected):

| Key | Meaning |
|---|---|
| `snr_dB` | Received SNR at UE |
| `pwr_dBm` | Received power at UE |
| `rssi_dBm` | RSSI at UE |
| `gain_dBi` | RIS array gain |
| `quant_loss_dB` | Phase quantization loss |
| `beam_angle` | Best beam steering angle (degrees, absolute) |
| `current_phases` | Continuous phase values per element |
| `quantized_phases` | Quantized phase values per element |

### 5.2 Full Node Parameters

```python
net.add_ap(
    name='ap1',
    x=0, y=0, z=0.0,
    power_dBm=20.0,       # transmit power
    freq=5.8e9,           # carrier frequency (Hz)
)

net.add_ris(
    name='ris1',
    x=5, y=0, z=0.0,
    N=32,                 # number of elements per side
    bits=2,               # phase shifter resolution (1–4 bits)
    max_angle_deg=90,     # half-angle FOV (±degrees from boresight)
    normal_angle_deg=0.0, # boresight direction (0° = +X axis)
)

net.add_ue(
    name='ue1',
    x=10, y=3, z=0.0,
    antenna_gain_dBi=3.0,
    noise_figure_dB=6.0,
)
```

---

## Part 6 — Environment and Obstacles

### 6.1 Adding Walls

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# Wall from (3,-3) to (3,3) with 20 dB attenuation
net.add_wall([3, -3], [3, 3], attenuation_dB=20)

result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"SNR with wall: {result['snr_dB']:.1f} dB")
```

### 6.2 Line-of-Sight Check

```python
env = net.environment
has_los, _ = env.check_line_of_sight([0, 0, 0], [10, 0, 0])
blocking = env.get_blocked_paths([0, 0, 0], [10, 0, 0])

print(f"LOS clear: {has_los}")
print(f"Blocking walls: {len(blocking)}")
```

---

## Part 7 — Pathfinding

### 7.1 Finding Paths

```python
from waveflow import RISnet

net = RISnet()
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))
net.start()

for algo in ['dijkstra', 'astar', 'greedy']:
    paths = net.findPaths(ap, ue, algorithm=algo)
    if paths:
        best = paths[0]
        print(f"{algo:12s}: {' → '.join(best['path'])}  "
              f"SNR={best['snr_dB']:.1f} dB  "
              f"loss={best['total_loss_dB']:.1f} dB")

net.stop()
```

### 7.2 Algorithm Comparison

| Algorithm | Optimal? | Speed | Use case |
|---|---|---|---|
| `dijkstra` | Yes | Fast | Default; maximum SNR path |
| `astar` | Yes | Fast | Same quality as Dijkstra, heuristic-accelerated |
| `greedy` | No | Fastest | Real-time, approximate |
| `exhaustive` | Yes | Slow | Small networks only; enumerate all paths |

### 7.3 Low-Level Pathfinding API

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

paths = net.find_paths('ap1', 'ue1', algorithm='dijkstra')
for p in paths:
    print(f"  {p['path']}  SNR={p.get('snr_dB', 'N/A')}")
```

---

## Part 8 — Beam Sweeping (Advanced)

### 8.1 Sweep API

`best_local_fine` is the offset angle (relative to the specular direction) that maximises SNR.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

result = net.sweep('ap1', 'ris1', 'ue1', fov=90, step=15)

print(f"Best local deflection: {result['best_local_fine']:.1f}°")
print(f"Best SNR:              {result['best_snr_fine']:.1f} dB")

for angle, snr in zip(result['local_coarse'], result['snr_coarse']):
    print(f"  {angle:+6.1f}°  {snr:.1f} dB")
```

### 8.2 Selecting an Algorithm Programmatically

```python
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

loader = SweepAlgorithmLoader(net)
print(loader.list_algorithms())

algo = loader.get_algorithm('coarse-fine')
result = algo.sweep('ap1', 'ris1', 'ue1', fov=60, step=10)
print(f"Best SNR: {result['best_snr_fine']:.1f} dB")
```

### 8.3 Differential Evolution Sweep

DE performs global search over the phase space — useful when the SNR surface has multiple local maxima.

```python
algo = loader.get_algorithm('de')
result = algo.sweep(
    'ap1', 'ris1', 'ue1',
    fov=60, step=10,
    M=32,              # population size
    target_snr_db=25,  # optional early stop
)
print(f"DE best SNR: {result['best_snr_fine']:.1f} dB")
```

---

## Part 9 — Physics and Link Budget

### 9.1 Manual Link Budget

```python
from core.physics import Physics

freq_GHz = 5.8
distance_m = 11.4  # AP-RIS + RIS-UE total path

path_loss  = Physics.path_loss_dB(distance_m, freq_GHz * 1e9)
atm_loss   = Physics.atmospheric_loss_dB(distance_m, freq_GHz)
array_gain = Physics.array_gain_dBi(16)
quant_loss = Physics.quantization_loss_dB(2)

snr = Physics.compute_snr_dB(
    tx_power_dBm=20.0,
    total_loss_dB=path_loss + atm_loss + quant_loss,
    array_gain_dBi=array_gain,
    bandwidth_MHz=20.0,
    noise_figure_dB=10.0,
)
print(f"SNR: {snr:.1f} dB")
```

### 9.2 Effect of Quantization Bits

```python
from core.physics import Physics

for bits in [1, 2, 3, 4]:
    loss = Physics.quantization_loss_dB(bits)
    print(f"  {bits}-bit: {loss:.2f} dB loss")
```

Output:
```
  1-bit: -3.92 dB loss
  2-bit: -0.91 dB loss
  3-bit: -0.23 dB loss
  4-bit: -0.06 dB loss
```

### 9.3 Effect of Array Size

```python
for N in [4, 8, 16, 32, 64, 128]:
    gain = Physics.array_gain_dBi(N)
    print(f"  N={N:3d}: {gain:.1f} dBi")
```

### 9.4 Rician Fading

```python
import numpy as np
from core.physics import Physics

np.random.seed(42)
fading = Physics.rician_fading(K_factor_dB=10)
print(f"Fading coefficient: {fading:.4f}")
```

### 9.5 Physics Validation Suite

Run all 14 physics validation sections (53 checks) against analytically
derived reference values:

```bash
# Terminal UI — coloured pass/fail per check
waveflow ui testphysics

# Interactive CLI
waveflow
> testphysics

# pytest — 66 individual test cases
pytest tests/test_physics_core.py -v
```

Sections covered: FSPL, atmospheric absorption, Rician fading, mutual
coupling, quantization-with-state loss, per-element phase error, quantized
beam angle, angle-loss penalty, SNR→EVM, multipath RIS gain, effective SNR
with waveform distortion, RIS coupling loss, Shannon capacity, and
quantization error validation.

---

## Part 10 — Feedback and Adaptive Control

### 10.1 Creating a Feedback Channel

Waveflow models the UE→AP feedback path for closed-loop beam adaptation.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

net.create_feedback_channel(
    ue_name='ue1',
    ris_name='ris1',
    feedback_interval=0.1,
    snr_threshold_dB=15.0,
)

result = net.connect(
    'ap1', 'ris1', 'ue1',
    use_get_snr=False,
    enable_feedback=True,
)
print(f"SNR after adaptation: {result['snr_dB']:.1f} dB")
```

### 10.2 Feedback Statistics

```python
stats = net.get_feedback_statistics()
for ue_ris, s in stats.items():
    print(f"{ue_ris}: {s}")
```

---

## Part 11 — Waveform-Level Simulation

System-level simulation uses a link budget formula. Waveform-level simulation runs a full OFDM signal through the channel and measures per-subcarrier SNR — closer to real hardware behaviour.

### 11.1 OFDM Signal

```python
import numpy as np
from core.waveform import OFDMConfig, OFDMSignal, calculate_papr

config = OFDMConfig(
    bandwidth=100e6,
    num_subcarriers=256,
    center_frequency=10e9,
)

ofdm = OFDMSignal(config, num_symbols=20)
tx_signal = ofdm.generate(seed=42)

power = np.mean(np.abs(tx_signal)**2)
papr  = calculate_papr(tx_signal)
print(f"Signal power: {power:.4f}")
print(f"PAPR:         {papr:.2f} dB")
```

### 11.2 System-Level vs Waveform-Level SNR

```python
import random
import numpy as np
from core import RISNetwork
from controller.waveform_controller import WaveformController

def set_deterministic_seeds(seed=42):
    np.random.seed(seed)
    random.seed(seed)

set_deterministic_seeds(42)

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

sys_result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"System-level SNR:      {sys_result['snr_dB']:.2f} dB")

wc = WaveformController(net)
wav_result = wc.compute_waveform_snr('ap1', 'ris1', 'ue1', num_symbols=20)
print(f"Waveform RIS SNR:      {wav_result['snr_ris_dB']:.2f} dB")
print(f"Waveform effective SNR:{wav_result['snr_effective_dB']:.2f} dB")
```

Both approaches should produce consistent results within a few dB for the same topology and seed.

---

## Part 12 — ML-Guided Beam Sweeping

ML predictors learn a mapping from network geometry to optimal beam angle, then seed the sweep with predicted candidates — reducing the number of angles to test.

### 12.1 Using a Pre-Trained Predictor

```python
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

loader = SweepAlgorithmLoader(net)
algo = loader.get_algorithm('ml-guided')

result = algo.sweep(
    'ap1', 'ris1', 'ue1',
    fov=60, step=10,
    ml_predictor='rf',   # 'rf', 'xgb', 'svr', 'knn', 'lgbm'
)
print(f"Best angle: {result['best_local_fine']:.1f}°")
print(f"Best SNR:   {result['best_snr_fine']:.1f} dB")
```

Requires pre-trained model files in `controller/beamsweeping/ml/models/`.

### 12.2 Training Your Own Model

```bash
# 1. Generate a dataset
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/dataset_builder.py

# 2. Train predictors
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_rf.py
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_xgb.py
```

### 12.3 Localization-Oriented Sweep Algorithms

Waveflow also includes sweep modes that do more than maximize SNR. Some
algorithms use beam measurements to estimate UE location or refine a prior
position estimate while sweeping.

Available directions in the repository include:

- `prime` / `anm-localization` for localization-oriented estimation
- `de-localization` for blind UE localization via differential evolution
- standard sweep algorithms for pure beam optimization baselines

Programmatic example:

```python
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

loader = SweepAlgorithmLoader(net)
algo = loader.get_algorithm('prime')

result = algo.sweep('ap1', 'ris1', 'ue1', fov=60, step=10)
print(f"Best SNR: {result.get('best_snr_fine', float('nan')):.1f} dB")
print("Estimated location:", result.get('location'))
```

When available, inspect:

- estimated UE location
- localization error against ground truth
- measurement consistency across beams
- recommended steering angle after estimation

CLI discovery example:

```bash
waveflow ui run sweep ap1 ris1 ue1 60 10 --algo prime
waveflow ui run sweep ap1 ris1 ue1 60 10 --algo de-localization
```

Use these modes when the research question is not only "which beam is best?"
but also "what does the beam response tell us about UE position?"

### 12.4 Vision-Assisted Workflows

Vision support exists as an optional workflow for experiments where the UE or
target is derived from camera observations instead of being entered manually.
This is especially useful for ArUco-assisted positioning and HOG-based human
detection demos.

Install the optional extra first:

```bash
pip install -e ".[vision]"
```

ArUco marker generation example:

```bash
PYTHONPATH=. python3 examples/script/example_18_aruco_markers.py
```

Expected output includes generated marker files under `aruco_markers/`.

HOG-based detection example:

```bash
PYTHONPATH=. python3 examples/script/example_19_hog_human_detection.py
```

Notes:

- example 18 is offline and suitable for setup validation
- example 19 is interactive and may require a webcam
- camera-assisted workflows are optional, not part of the base install
- vision is currently example-driven rather than a complete end-to-end CLI
  product surface

If you are evaluating vision integration, focus on whether detection output can
be turned into stable sweep inputs such as target angle, target position, or
tracked candidate identities.

---

## Part 13 — Headless Scenario Runner

The scenario runner lets you execute simulations from a topology file without the
interactive shell or Flask. This is suitable for automated pipelines, batch jobs,
and testing.

### 13.1 Run a Connect from Code

```python
from risnet import ScenarioRunner

runner = ScenarioRunner()

# Auto-resolves first AP, RIS, UE in the topology
result = runner.run_connect(
    'examples/json/example_1_simple.json',
    use_get_snr=False,
)
print(f"SNR: {result.result['snr_dB']:.1f} dB")
print(f"AP: {result.ap_name}, RIS: {result.ris_name}, UE: {result.ue_name}")
```

### 13.2 Run a Sweep from Code

```python
sweep_result = runner.run_sweep(
    'examples/json/example_1_simple.json',
    fov=60,
    step=10,
)
print(f"Best SNR: {sweep_result.result['best_snr_fine']:.1f} dB")
```

### 13.3 Declarative Scenario via Dict

```python
from risnet import ScenarioRunner, ScenarioRequest

request = ScenarioRequest.from_dict({
    "topology_path": "examples/json/example_1_simple.json",
    "connect": {
        "ap_name": "ap1",
        "ris_name": "ris1",
        "ue_name": "ue1",
    }
})

runner = ScenarioRunner()
result = runner.run(request)
print(f"SNR: {result.result['snr_dB']:.1f} dB")
```

### 13.4 Declarative Scenario via YAML File

Create `scenario.yaml`:

```yaml
topology_path: examples/json/example_1_simple.json
connect:
  ap_name: ap1
  ris_name: ris1
  ue_name: ue1
```

Run it:

```python
from risnet import ScenarioRunner, ScenarioRequest

request = ScenarioRequest.from_file('scenario.yaml')
runner = ScenarioRunner()
result = runner.run(request)
print(f"SNR: {result.result['snr_dB']:.1f} dB")
```

### 13.5 Multi-Action Scenario

Run a connect followed by a sweep in a single topology load:

```python
from risnet import ScenarioRunner, ScenarioRequest

request = ScenarioRequest.from_dict({
    "topology_path": "examples/json/example_1_simple.json",
    "actions": [
        {"type": "connect", "ap_name": "ap1", "ris_name": "ris1", "ue_name": "ue1"},
        {"type": "sweep",   "ap_name": "ap1", "ris_name": "ris1", "ue_name": "ue1",
         "kwargs": {"fov": 60, "step": 10}},
    ]
})

runner = ScenarioRunner()
seq = runner.run(request)
for step in seq.steps:
    print(f"{step.action}: {step.result.get('snr_dB') or step.result.get('best_snr_fine'):.1f} dB")
```

---

## Part 14 — Adding a Custom Beam Sweep Algorithm

### 14.1 Why Write a Custom Algorithm?

Waveflow ships with several built-in sweep algorithms (`linear`, `coarse-fine`, `de`, `ml-guided`). But sometimes you need your own strategy — for example, a domain-specific search based on prior measurements, a reinforcement-learning agent, or a sweep that logs extra diagnostics.

Waveflow uses a **registry pattern**: you write a class, decorate it with `@register_algorithm`, and it becomes available by name in both Python and the CLI — no changes to the core codebase needed.

### 14.2 The Four Things Every Algorithm Must Do

1. Inherit from `SweepAlgorithmBase`
2. Define `name` and `description` properties
3. Implement a `sweep()` method that tests angles and returns SNR results
4. Return a dictionary with the standard result keys

### 14.3 Algorithm Template

Create `controller/beamsweeping/algorithms/my_sweep.py`:

```python
from ..base import SweepAlgorithmBase
from ..registry import register_algorithm
import numpy as np

@register_algorithm("my-sweep", aliases=("my-alias",))
class MySweep(SweepAlgorithmBase):

    @property
    def name(self):
        return "My Sweep"

    @property
    def description(self):
        return "Custom beam sweep algorithm"

    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, **kwargs):
        # Generate candidate angles within ±fov degrees
        angles = np.arange(-fov, fov + step, step)
        snrs, powers = [], []

        for angle in angles:
            # Test each angle by calling connect() with a fixed beam direction
            result = self.network.connect(
                ap_name, ris_name, ue_name,
                beam_angle_deg=float(angle),
                use_get_snr=False,
            )
            snrs.append(result['snr_dB'])
            powers.append(result['pwr_dBm'])

        best_idx = int(np.argmax(snrs))

        # All sweep algorithms must return these keys
        return {
            'local_coarse':    list(angles),
            'snr_coarse':      snrs,
            'pwr_coarse':      powers,
            'local_fine':      list(angles),
            'snr_fine':        snrs,
            'best_local_fine': float(angles[best_idx]),
            'best_snr_fine':   float(snrs[best_idx]),
        }
```

Then register it by adding an import to `controller/beamsweeping/algorithms/__init__.py`:

```python
from . import my_sweep   # add this line
```

### 14.4 Using Your Algorithm

```python
import controller.beamsweeping.algorithms.my_sweep  # triggers registration

from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

algo = SweepAlgorithmLoader.get_algorithm('my-sweep', net)
result = algo.sweep('ap1', 'ris1', 'ue1', fov=45, step=5)

print(f"Best SNR:      {result['best_snr_fine']:.1f} dB")
print(f"Best angle:    {result['best_local_fine']:.1f}°")
print(f"Angles tested: {len(result['local_coarse'])}")
```

Expected output:

```
Best SNR:      29.9 dB
Best angle:    30.0°
Angles tested: 19
```

From the CLI (once registered via `__init__.py`):

```bash
waveflow> sweep ap1 ris1 ue1 45 5 --algo my-sweep
```

### 14.5 Standard Return Dictionary

All sweep algorithms must return exactly these keys so that the CLI, terminal UI, and post-processing tools work correctly:

| Key | Type | Meaning |
|---|---|---|
| `local_coarse` | list[float] | Angles tested in the coarse phase (degrees, offset from boresight) |
| `snr_coarse` | list[float] | SNR at each coarse angle (dB) |
| `pwr_coarse` | list[float] | Received power at each coarse angle (dBm) |
| `local_fine` | list[float] | Angles tested in the fine phase |
| `snr_fine` | list[float] | SNR at each fine angle (dB) |
| `best_local_fine` | float | Best offset angle found (degrees) |
| `best_snr_fine` | float | SNR at the best angle (dB) |

For simple algorithms where there is no coarse/fine distinction, return the same lists for both phases (as shown in the template above).

### 14.6 Debugging Your Algorithm

```python
# List all currently registered algorithm names
from controller.beamsweeping import list_registered_algorithms
print(list_registered_algorithms())
# ['linear', 'coarse-fine', 'de', 'ml', ..., 'my-sweep']

# Inspect per-angle SNR from your sweep
for angle, snr in zip(result['local_coarse'], result['snr_coarse']):
    print(f"  {angle:+6.1f}°  {snr:.2f} dB")
```

See `controller/beamsweeping/ALGORITHM_TEMPLATE.md` for the full annotated template with optional features (early stopping, ML integration, localization output).

---

## Part 15 — Batch Parameter Study

### 15.1 What Is a Batch Study?

In research, you rarely test just one configuration. You want to know: **does adding more RIS elements help? Does using more phase-resolution bits matter?** A batch study runs the same simulation many times, varying one parameter at a time, and collects results into a table.

Think of it like testing different camera lenses — you want to measure sharpness at different focal lengths, not just pick one and hope for the best.

### 15.2 Sweeping Array Size and Quantization Bits

```python
from core import RISNetwork

results = []

for N in [8, 16, 32, 64]:        # number of RIS elements
    for bits in [1, 2, 3]:       # phase resolution
        net = RISNetwork(enable_messaging=False)
        net.add_ap('ap1',  0, 0)
        net.add_ris('ris1', 5, 0, N=N, bits=bits, max_angle_deg=90)
        net.add_ue('ue1', 10, 3)

        r = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
        results.append({
            'N': N, 'bits': bits,
            'snr_dB': r['snr_dB'],
            'gain_dBi': r['gain_dBi'],
            'quant_loss_dB': r['quant_loss_dB'],
        })

print(f"{'N':>4}  {'bits':>4}  {'SNR (dB)':>10}  {'Gain (dBi)':>10}  {'Q-loss (dB)':>12}")
for r in results:
    print(f"{r['N']:>4}  {r['bits']:>4}  "
          f"{r['snr_dB']:>10.2f}  {r['gain_dBi']:>10.2f}  "
          f"{r['quant_loss_dB']:>12.3f}")
```

Expected output:

```
   N  bits    SNR (dB)  Gain (dBi)   Q-loss (dB)
   8     1       16.91       26.66        -1.671
   8     2       16.28       27.59        -0.745
   8     3       18.09       27.81        -0.520
  16     1       22.94       32.68        -1.671
  16     2       23.88       33.61        -0.745
  16     3       19.70       33.83        -0.520
  32     1       28.02       38.70        -1.671
  32     2       29.90       39.63        -0.745
  32     3       29.65       39.85        -0.520
  64     1       35.00       44.72        -1.671
  64     2       35.55       45.65        -0.745
  64     3       36.15       45.88        -0.520
```

### 15.3 Reading the Table

| Column | What It Tells You |
|---|---|
| `N` | Number of RIS elements. Doubling N adds ~6 dBi of array gain. |
| `bits` | Phase resolution. 1-bit loses ~1.67 dB; 2-bit loses ~0.75 dB; 3-bit loses ~0.52 dB. |
| `SNR (dB)` | Final received signal quality — higher is better. |
| `Gain (dBi)` | Raw array gain before quantization losses. |
| `Q-loss (dB)` | How much SNR is lost due to phase rounding. Negative means a penalty. |

**Key insight**: Going from N=8 to N=64 gains ~18 dB of SNR. Going from 1-bit to 3-bit at N=64 adds ~1.15 dB — less impactful at this scale but still measurable.

### 15.4 Running the Prebuilt Example

```bash
PYTHONPATH=. python3 examples/script/example_6_batch_testing.py
```

This script runs a broader study across more configurations and prints a formatted comparison table.

---

## Part 16 — Loading Topologies from JSON

### 16.1 What Is a Topology File?

Instead of defining nodes in Python code every time, you can describe your network layout in a **JSON file** — a plain text format that both humans and programs can read easily.

Think of it like a blueprint. You draw the building once (the JSON file), then load it whenever you need to simulate inside it.

### 16.2 JSON File Structure

A topology file lists all nodes (AP, RIS, UE) and optional walls. Here is what `examples/json/example_1_simple.json` looks like:

```json
{
  "name": "Example 1: Simple Network",
  "description": "Basic network with 1 AP, 1 RIS, and 1 UE",
  "nodes": [
    {"name": "AP1", "type": "AccessPoint", "pos": [0.0, 2.0, 0.0]},
    {"name": "R1",  "type": "RIS",         "pos": [5.0, 2.0, 0.0], "N": 16, "bits": 1},
    {"name": "UE1", "type": "UE",          "pos": [8.0, 8.0, 0.0]}
  ]
}
```

Each node entry needs a `name`, `type`, and `pos` (x, y, z coordinates). RIS nodes also carry `N` (elements) and `bits`.

### 16.3 Loading and Using a Topology in Python

```python
import json
from core import RISNetwork

# Load the JSON file
with open('examples/json/example_1_simple.json') as f:
    topo = json.load(f)

net = RISNetwork(enable_messaging=False)

# Register every node
for node in topo['nodes']:
    name = node['name']
    x, y = node['pos'][0], node['pos'][1]
    if node['type'] == 'AccessPoint':
        net.add_ap(name, x, y, power_dBm=node.get('power_dBm', 20))
    elif node['type'] == 'RIS':
        net.add_ris(name, x, y, N=node.get('N', 16), bits=node.get('bits', 2))
    elif node['type'] == 'UE':
        net.add_ue(name, x, y)

# Register walls if present
for wall in topo.get('walls', []):
    net.add_wall(wall['start'], wall['end'],
                 attenuation_dB=wall.get('attenuation_dB', 20))

print("Nodes loaded:", list(net.nodes.keys()))

# Now connect and run
result = net.connect('AP1', 'R1', 'UE1', use_get_snr=False)
print(f"SNR: {result['snr_dB']:.1f} dB")
```

Expected output:

```
Nodes loaded: ['AP1', 'R1', 'UE1']
SNR: 29.9 dB
```

### 16.4 Using the ScenarioRunner (Simpler)

If you just want to load a topology and run a connect or sweep without writing the loop above, use `ScenarioRunner` from Part 13:

```python
from risnet import ScenarioRunner

runner = ScenarioRunner()
result = runner.run_connect('examples/json/example_1_simple.json', use_get_snr=False)
print(f"SNR: {result.result['snr_dB']:.1f} dB")
print(f"Nodes: {result.ap_name} → {result.ris_name} → {result.ue_name}")
```

Expected output:

```
SNR: 29.9 dB
Nodes: AP1 → R1 → UE1
```

`ScenarioRunner` auto-detects the first AP, RIS, and UE in the file — no need to name them manually.

### 16.5 Bundled Topology Files

| File | Contents |
|---|---|
| `example_1_simple.json` | 1 AP, 1 RIS, 1 UE — basic test |
| `example_2_predefined_topology.json` | Multi-hop network |
| `example_3_custom_topology.json` | Custom geometry with multiple RIS |
| `example_4_obstacles.json` | Walls and attenuation |
| `example_5_grid_topology.json` | Grid of nodes |
| `example_7_complex_network.json` | Dense multi-node scenario |

---

## Part 17 — Example Scripts Reference

### 17.1 What Are the Example Scripts?

The `examples/script/` directory contains standalone Python scripts — each one demonstrates a specific capability end-to-end. They are the fastest way to see Waveflow in action without writing code from scratch.

### 17.2 Running an Example

```bash
# With pip install -e . (recommended)
python3 examples/script/example_1_simple.py

# Without installing (development mode)
PYTHONPATH=. python3 examples/script/example_1_simple.py
```

To run a batch of non-interactive examples in sequence:

```bash
for f in examples/script/example_{1,2,3,4,5,6,8,10,12,13,14,15,16,17,18}_*.py; do
    echo "--- $f ---"
    PYTHONPATH=. python3 "$f"
done
```

### 17.3 Script Catalogue

| Script | Level | Extra deps | What it shows | Key output |
|---|---|---|---|---|
| `example_1_simple.py` | Beginner | — | Basic AP→RIS→UE connect | `SNR: 73.3 dB` |
| `example_2_topology.py` | Beginner | — | Multi-UE topology from JSON | `ap1 -> ue3: SNR = 71.5 dB` |
| `example_3_custom_topology.py` | Beginner | — | User-defined geometry | SNR table per path |
| `example_4_obstacles.py` | Beginner | — | Walls and attenuation | `SNR: 70.7 dB` |
| `example_5_context_manager.py` | Beginner | — | `with RISnet()` context manager | `Network auto-stopped` |
| `example_6_batch_testing.py` | Intermediate | — | SNR across N and bits configs | Formatted result table |
| `example_8_sdr_validation.py` | Intermediate | — | SDR hardware-matched validation | `RIS assisted: SNR=59.75 dB` |
| `example_9_interactive_cli.py` | Beginner | — | Launches interactive shell | `waveflow>` prompt |
| `example_10_waveform_level.py` | Advanced | — | OFDM waveform through RIS channel | `All examples completed!` |
| `example_11_ml_beam_prior.py` | Advanced | `[ml]` | ML predictor for beam angle | Prediction accuracy table |
| `example_12_feedback_integration.py` | Advanced | — | Closed-loop UE→AP feedback | `All examples completed!` |
| `example_13_adaptive_control.py` | Advanced | — | Adaptive beam tracking | `All examples completed successfully!` |
| `example_14_full_integration.py` | Advanced | — | Combined waveform + feedback + sweep | `All integration examples completed successfully!` |
| `example_15_video_streaming.py` | Advanced | — | RIS-assisted streaming link budget | Throughput and capacity summary |
| `example_16_quantization_codebook.py` | Advanced | — | 1-bit codebook analytics vs paper | Codebook SNR table |
| `example_17_beam_sweeping_trials.py` | Advanced | — | Algorithm comparison across scenarios | AoA estimation results |
| `example_18_aruco_markers.py` | Advanced | `[vision]` | ArUco marker generation | `✓ Successfully saved: aruco_markers/aruco_id_0.png` |
| `example_19_hog_human_detection.py` | Advanced | `[vision]` + webcam | HOG human detection (live camera) | Interactive menu |

### 17.4 What to Expect from Key Examples

**example_15** — Video streaming simulation. Shows how RIS improves a 28 GHz mmWave link for a streaming scenario:

```
[0] Direct AP→UE baseline (no RIS)
    Distance=90.6 m | SNR (direct, ideal receiver)=23.48 dB | Capacity=780.49 Mbps

[1] System-level connect (AP→RIS→UE)
    SNR=-39.96 dB, Gain=32.68 dBi, Beam angle (absolute)=11.31°

[3] Waveform baseline
    RIS SNR (pre-combiner)=49.45 dB | Effective SNR=45.94 dB
    (Δ +22.46 dB vs direct) | Capacity=1.221 Gbps (1.6× of direct)

Summary:
  Chunks sent:        6
  Avg throughput:     3.47 Mbps
  Capacity gain:      1.56× | +56.4% vs direct
```

**example_16** — Quantization codebook analytics. Validates 1-bit phase quantization against published results:

```
[Random prephasing validation (Fig. 2)] φ_out=120.0°
  Measured quant beam (standard 1-bit) : 39.825°
  Reported (paper) quant beam          : 39.833° (Δ = -0.0080°)

Elements  PathLoss  Two-bit  1-bit  Random  MapFusion
      64     -10.0  13.176  9.364   8.960     10.836
     128     -10.0  17.564  13.165  13.141     14.944
     256     -10.0  22.237  17.565  17.677     19.510
```

**example_17** — Beam sweeping trials. Runs outdoor and indoor scenarios to compare beam direction accuracy:

```
Outdoor field trial (Tx=-15°, Rx 0→60°):
  Actual Rx=10.0° -> best beam @ 10.0° (Δ power = 49.42 dB span)
  Actual Rx=30.0° -> best beam @ 30.0° (Δ power = 33.66 dB span)
  Actual Rx=45.0° -> best beam @ 45.0° (Δ power = 38.56 dB span)
```

**example_18** — ArUco marker generation (requires `pip install -e ".[vision]"`):

```
EXAMPLE 1: Generate and Save a Single Marker
  ✓ Successfully saved: aruco_markers/aruco_id_0.png

EXAMPLE 2: Generate Multiple Markers in Batch
  Generated 5 markers:
    ID 0: aruco_markers/batch/aruco_id_0.png

EXAMPLE 6: Dictionary Information
  Dictionary       Max ID   Total   Bits
  DICT_4X4_50        49      50      16
  DICT_5X5_100       99     100      25
```

### 17.5 Dependency Notes

- **Core examples** (1–10, 12–17): work with base `pip install -e .`; no extras needed.
- **`[ml]` extra** (`example_11`): `pip install -e ".[ml]"` — requires scikit-learn and PyTorch.
- **`[vision]` extra** (`example_18`, `example_19`): `pip install -e ".[vision]"` — requires opencv-python. Example 19 also requires a connected webcam.
- **`example_15`**: expects `streaming/video.mp4`; the demo runs with simulated throughput if the file is absent.
- **`example_9`**: opens an interactive shell — exit with `quit` or Ctrl-D.

### 17.6 TUTORIAL Cross-Reference

| TUTORIAL Part | Relevant examples |
|---|---|
| Part 2 — Interactive CLI | `example_9` |
| Part 4 — Python API | `example_1`, `example_2`, `example_3`, `example_5` |
| Part 6 — Obstacles | `example_4` |
| Part 8 — Beam Sweeping | `example_17` |
| Part 9 — Physics | `example_16` |
| Part 10 — Feedback | `example_12`, `example_13` |
| Part 11 — Waveform | `example_8`, `example_10`, `example_14` |
| Part 12 — ML | `example_11` |
| Part 12.3 — Localization | `prime`, `anm-localization`, `de-localization` algorithms |
| Part 12.4 — Vision | `example_18`, `example_19` |
| Part 2 — Terminal UI | `waveflow ui`, `example_17` |
| Part 13 — Streaming | `example_15` |
| Part 15 — Batch study | `example_6` |

### 17.7 MATLAB Examples

Standalone MATLAB scripts live in `examples/matlab/`:

| Script | What It Shows |
|---|---|
| `example_1_beam_pattern_3d.m` | 3D far-field beam pattern, 1D/polar cuts, phase heatmap |
| `example_2_compare_steering_angles.m` | Side-by-side beam patterns for 6 steering angles |
| `example_3_ris_phase_farfield.m` | Phase maps + 3D far-field (Python-matched parameters) |
| `example_4_ris_phase_farfield_cst_style.m` | CST-style annotated 3D pattern with source/beam arrows |

Run from MATLAB command window (from the `examples/matlab/` directory):

```matlab
>> cd examples/matlab
>> example_1_beam_pattern_3d        % standalone, no Python needed
>> example_3_ris_phase_farfield     % default params, or pass arguments:
>> example_3_ris_phase_farfield(0, 5.8e9, 0.45, 0, 45, 0, 16, 16)
```

The `matlab_integration/scripts/` functions (`compute_beam_pattern`, `plot_ris_geometry`, etc.) are library functions called by the Python `MatlabBridge` — they are not intended to be run directly.

---

## Next Steps

- Run example scripts in `examples/script/` for complete end-to-end demonstrations
- See `FUTURE.md` for the v3 architecture roadmap — spatial channels, AI-native runtime, phased arrays
- See `INSTALL.md` for dependency management and troubleshooting
- Open an issue at https://github.com/nqmn/waveflow/issues for questions or bug reports
