# Waveflow Tutorial

This tutorial is structured in two tiers:

- **Beginner** (Parts 1–4) — concepts, analogies, and simple examples. No prior wireless engineering knowledge required. Suitable for final-year undergraduates and researchers new to RIS.
- **Advanced** (Parts 5–15) — full API, physics models, waveform simulation, ML-guided optimization, scenario runner, and custom algorithm development. Suitable for researchers and engineers.

Prerequisites: completed installation per [INSTALL.md](INSTALL.md).

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
- Place nodes (AP, RIS, UE) in a 2D space
- Add walls and obstacles
- Compute how well the signal reaches the UE (measured as SNR)
- Optimize the RIS reflection angle (beam sweeping)
- Compare different beam search algorithms

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

### 2.1 Using the Interactive CLI

The easiest way to start is the command-line interface. Launch it:

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

## Part 14 — Modern Terminal UI (`waveflow ui`)

`waveflow ui` provides a Typer/Rich terminal surface with structured commands and
`--help` on every command. It covers all common operations without entering the
interactive shell.

```bash
# All available commands
waveflow ui --help

# Network status
waveflow ui status --topology examples/json/example_1_simple.json

# Connect nodes from a topology
waveflow ui connect AP1 R1 UE1 --topology examples/json/example_1_simple.json

# Beam sweep
waveflow ui sweep AP1 R1 UE1 --fov 60 --step 10

# Add a node (operates on an in-memory network; combine with save/load for persistence)
waveflow ui add ris R2 --x 8 --y 2 --n 32 --bits 2

# Save and load topology
waveflow ui save mynet.json
waveflow ui load mynet.json

# Run the comprehensive test suite
waveflow ui testall

# Run physics model validation suite (FSPL, atmospheric loss, Rician fading,
# mutual coupling, quantization, SNR/EVM, Shannon capacity, and more)
waveflow ui testphysics

# Run any legacy CLI command non-interactively
waveflow ui run signal AP1 R1 UE1 --breakdown
waveflow ui run plot --type sweep
waveflow ui run ap AP1 show

# Open the interactive shell
waveflow ui shell
```

Each command has a `--help` flag:

```bash
waveflow ui connect --help
waveflow ui sweep --help
```

---

## Part 15 — Adding a Custom Beam Sweep Algorithm

### 15.1 Algorithm Template

```python
# File: controller/beamsweeping/algorithms/my_sweep.py
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
        angles = np.arange(-fov, fov + step, step)
        snrs, powers = [], []

        for angle in angles:
            result = self.network.connect(
                ap_name, ris_name, ue_name,
                beam_angle_deg=float(angle),
                use_get_snr=False,
            )
            snrs.append(result['snr_dB'])
            powers.append(result['pwr_dBm'])

        best_idx = int(np.argmax(snrs))
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

### 15.2 Using Your Algorithm

```python
import controller.beamsweeping.algorithms.my_sweep  # triggers registration

from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

loader = SweepAlgorithmLoader(net)
algo = loader.get_algorithm('my-sweep')
result = algo.sweep('ap1', 'ris1', 'ue1', fov=45, step=5)
print(f"Best SNR: {result['best_snr_fine']:.1f} dB")
```

From the CLI:
```bash
waveflow> sweep ap1 ris1 ue1 45 5 --algo my-sweep
```

---

## Part 16 — Batch Parameter Study

Useful for research — sweep across RIS configurations and collect results:

```python
import numpy as np
from core import RISNetwork

results = []

for N in [8, 16, 32, 64]:
    for bits in [1, 2, 3]:
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

---

## Part 17 — Loading Topologies from JSON

```python
import json
from core import RISNetwork

with open('examples/json/example_1_simple.json') as f:
    topo = json.load(f)

net = RISNetwork(enable_messaging=False)

for node in topo['nodes']:
    name = node['name']
    x, y = node['pos'][0], node['pos'][1]
    if node['type'] == 'AccessPoint':
        net.add_ap(name, x, y, power_dBm=node.get('power_dBm', 20))
    elif node['type'] == 'RIS':
        net.add_ris(name, x, y, N=node.get('N', 16), bits=node.get('bits', 2))
    elif node['type'] == 'UE':
        net.add_ue(name, x, y)

for wall in topo.get('walls', []):
    net.add_wall(wall['start'], wall['end'],
                 attenuation_dB=wall.get('attenuation_dB', 20))

print("Nodes loaded:", list(net.nodes.keys()))
```

---

## Part 18 — Example Scripts Reference

All runnable scripts live in `examples/script/`. Run any of them from the project root:

```bash
# If installed via pip install -e .
python3 examples/script/example_1_simple.py

# Without installing (development mode)
PYTHONPATH=. python3 examples/script/example_1_simple.py
```

To run all non-interactive examples in sequence:

```bash
for f in examples/script/example_{1,2,3,4,5,6,8,10,12,13,14,15,16,17,18}_*.py; do
    echo "--- $f ---"
    PYTHONPATH=. python3 "$f"
done
```

### Scripts, levels, and expected output

| Script | Level | Deps | Expected last line / key output |
|---|---|---|---|
| `example_1_simple.py` | Beginner | core | `SNR: 73.3 dB` |
| `example_2_topology.py` | Beginner | core | `ap1 -> ue3: SNR = 71.5 dB` |
| `example_3_custom_topology.py` | Beginner | core | `ap1 -> ris3 -> ue3: SNR = ...` |
| `example_4_obstacles.py` | Beginner | core | `SNR: 70.7 dB` (wall-attenuated) |
| `example_5_context_manager.py` | Beginner | core | `Network auto-stopped` |
| `example_6_batch_testing.py` | Intermediate | core | SNR table across array sizes |
| `example_8_sdr_validation.py` | Intermediate | core | `RIS assisted  : SNR=59.75 dB` |
| `example_9_interactive_cli.py` | Beginner | core | Opens interactive `waveflow>` shell |
| `example_10_waveform_level.py` | Advanced | core | `All examples completed!` |
| `example_11_ml_beam_prior.py` | Advanced | `[ml]` | Beam prediction results table |
| `example_12_feedback_integration.py` | Advanced | core | `# All examples completed!` |
| `example_13_adaptive_control.py` | Advanced | core | `# All examples completed successfully!` |
| `example_14_full_integration.py` | Advanced | core | `All integration examples completed successfully!` |
| `example_15_video_streaming.py` | Advanced | core | Throughput and capacity summary |
| `example_16_quantization_codebook.py` | Advanced | core | Codebook SNR table |
| `example_17_beam_sweeping_trials.py` | Advanced | core | Algorithm comparison results |
| `example_18_aruco_markers.py` | Advanced | `[vision]` | `✓ Successfully saved: aruco_markers/aruco_id_0.png` |
| `example_19_hog_human_detection.py` | Advanced | `[vision]` + webcam | Interactive menu (requires hardware) |

### TUTORIAL part cross-reference

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
| Part 16 — Batch study | `example_6` |
| Vision / hardware | `example_18`, `example_19` |
| Streaming | `example_15` |

### Dependency notes

- **`[ml]` extra** (`example_11`): `pip install -e ".[ml]"` — requires scikit-learn / torch.
- **`[vision]` extra** (`example_18`, `example_19`): `pip install -e ".[vision]"` — requires opencv-python. Example 19 also requires a connected webcam.
- **`example_15`**: expects `streaming/video.mp4`; the demo runs with simulated throughput if the file is absent.
- **`example_9`**: opens an interactive shell — exit with `quit` or Ctrl-D.

### MATLAB examples

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

## Next Steps

- Run example scripts in `examples/script/` for complete end-to-end demonstrations
- See `FUTURE.md` for the v3 architecture roadmap — spatial channels, AI-native runtime, phased arrays
- See `INSTALL.md` for dependency management and troubleshooting
- Open an issue at https://github.com/nqmn/waveflow/issues for questions or bug reports
