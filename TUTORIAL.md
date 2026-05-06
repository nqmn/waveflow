# RISNet Tutorial

This tutorial covers RISNet from a first simulation to advanced beam sweeping,
waveform-level analysis, and ML-guided optimization. Each section builds on
the previous one.

Prerequisites: completed installation per [INSTALL.md](INSTALL.md).

---

## Part 1 — Basic Simulation

### 1.1 First AP → RIS → UE Connection

The low-level API (`RISNetwork`) gives direct access to all simulation
primitives.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)

# Add nodes: AccessPoint at origin, RIS at (5,0), UE at (10,3)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# Connect: compute optimal RIS phases and evaluate SNR
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
| `beam_angle` | Best beam steering angle (degrees) |
| `current_phases` | Continuous phase values per element |
| `quantized_phases` | Quantized phase values per element |

**RIS FOV constraint**: the RIS has a ±`max_angle_deg` field of view. Both the
AP and UE must be within this cone. The default is ±60°. Use
`max_angle_deg=90` or wider when your geometry requires it.

### 1.2 High-Level API

`RISnet` wraps `RISNetwork` with a higher-level interface modelled after
network testing tools.

```python
from risnet import RISnet

net = RISnet()
ap  = net.addAP('ap1',  position=(0, 0))
ris = net.addRIS('ris1', position=(5, 0), N=16, bits=2)
ue  = net.addUE('ue1',  position=(10, 3))
net.start()

# ping: reachability + SNR
result = net.ping(ap, ue)
print(f"Reachable: {result['reachable']}")
print(f"SNR:       {result['snr_dB']:.1f} dB")
print(f"Hops:      {result['hops']}")

# iperf: estimated throughput
throughput = net.iperf(ap, ue)
print(f"Throughput: {throughput['throughput_Mbps']:.1f} Mbps")

net.stop()
```

### 1.3 Node Parameters

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
    N=32,                 # number of elements
    bits=2,               # phase shifter resolution (1–4 bits)
    max_angle_deg=60,     # half-angle FOV
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

## Part 2 — Environment and Obstacles

### 2.1 Adding Walls

Walls block LOS and add attenuation to paths that pass through them.

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

### 2.2 Line-of-Sight Check

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ue('ue1', 10, 0)
net.add_wall([5, -2], [5, 2], attenuation_dB=30)

env = net.environment
has_los, _ = env.check_line_of_sight([0, 0, 0], [10, 0, 0])
blocking = env.get_blocked_paths([0, 0, 0], [10, 0, 0])

print(f"LOS clear: {has_los}")
print(f"Blocking walls: {len(blocking)}")
```

### 2.3 Predefined Topologies

```python
from risnet import RISnet, topos

# Available topologies: 'simple', 'obstacle', 'grid', 'sdr'
topo = topos['obstacle']()
topo.build()

net = RISnet(topo=topo)
net.start()

ap = net.aps['ap1']
ue = net.ues['ue1']
result = net.ping(ap, ue)
print(f"SNR: {result['snr_dB']:.1f} dB via {result['hops']} hops")

net.stop()
```

---

## Part 3 — Pathfinding

### 3.1 Finding Paths

```python
from risnet import RISnet

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

### 3.2 Algorithm Comparison

| Algorithm | Optimal? | Speed | Use case |
|---|---|---|---|
| `dijkstra` | Yes | Fast | Default; maximum SNR path |
| `astar` | Yes | Fast | Same quality as Dijkstra, heuristic-accelerated |
| `greedy` | No | Fastest | Real-time, approximate |
| `exhaustive` | Yes | Slow | Small networks only; enumerate all paths |

### 3.3 Low-Level Pathfinding API

```python
from core import RISNetwork
from controller.pathfinding import get_algorithm

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

paths = net.find_paths('ap1', 'ue1', algorithm='dijkstra')
for p in paths:
    print(f"  {p['path']}  SNR={p.get('snr_dB', 'N/A')}")
```

---

## Part 4 — Beam Sweeping

### 4.1 Basic Sweep

The `sweep()` method searches over local deflection angles relative to the
specular reflection direction (not boresight). `best_local_fine` is the
offset that maximises SNR. Use `connect()` with the returned beam angle
to apply it, or let `connect()` compute the optimal angle automatically.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, N=16, bits=2, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# fov=90: search ±90° local deflection, step=15°
result = net.sweep('ap1', 'ris1', 'ue1', fov=90, step=15)

print(f"Best local deflection: {result['best_local_fine']:.1f}°")
print(f"Best SNR:              {result['best_snr_fine']:.1f} dB")

# Coarse sweep results (local deflection angle vs SNR)
for angle, snr in zip(result['local_coarse'], result['snr_coarse']):
    print(f"  {angle:+6.1f}°  {snr:.1f} dB")

# Apply via direct connect (auto-computes optimal beam)
best = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"Absolute beam angle: {best['beam_angle']:.1f}°")
print(f"SNR:                 {best['snr_dB']:.1f} dB")
```

### 4.2 Choosing a Sweep Algorithm

```python
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# List all registered algorithms
loader = SweepAlgorithmLoader(net)
print(loader.list_algorithms())

# Run a specific algorithm
algo = loader.get_algorithm('adaptive')
result = algo.sweep('ap1', 'ris1', 'ue1', fov=60, step=10)
print(f"Best SNR: {result['best_snr_fine']:.1f} dB")
```

### 4.3 Differential Evolution Sweep

DE performs global search over the phase space, useful when the SNR surface
has multiple local maxima.

```python
algo = loader.get_algorithm('de')
result = algo.sweep(
    'ap1', 'ris1', 'ue1',
    fov=60,
    step=10,
    M=32,              # population size
    target_snr_db=25,  # optional early stop
)
print(f"DE best SNR: {result['best_snr_fine']:.1f} dB")
```

### 4.4 Sweep via CLI

```bash
risnet> add ap ap1 0 0
risnet> add ris ris1 5 0 0 16 2
risnet> add ue ue1 10 3
risnet> sweep ap1 ris1 ue1 60 10
risnet> sweep ap1 ris1 ue1 60 10 --algo adaptive
risnet> sweep ap1 ris1 ue1 60 10 --algo de M=32
risnet> sweep ap1 ris1 ue1 60 10 --algo ml-guided --ml-predictor rf
```

---

## Part 5 — Physics and Link Budget

### 5.1 Manual Link Budget

```python
from core.physics import Physics

freq_GHz = 5.8
distance_m = 11.4  # AP-RIS + RIS-UE

path_loss = Physics.path_loss_dB(distance_m, freq_GHz * 1e9)
atm_loss  = Physics.atmospheric_loss_dB(distance_m, freq_GHz)
array_gain = Physics.array_gain_dBi(16)
quant_loss = Physics.quantization_loss_dB(2)

tx_power_dBm = 20.0
noise_figure_dB = 10.0
bandwidth_MHz = 20.0

snr = Physics.compute_snr_dB(
    tx_power_dBm,
    path_loss + atm_loss + quant_loss,  # fold quant loss into total loss
    array_gain,
    bandwidth_MHz,
    noise_figure_dB,
)
print(f"SNR: {snr:.1f} dB")
```

### 5.2 Effect of Quantization Bits

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

### 5.3 Effect of Array Size

```python
from core.physics import Physics

for N in [4, 8, 16, 32, 64, 128]:
    gain = Physics.array_gain_dBi(N)
    print(f"  N={N:3d}: {gain:.1f} dBi")
```

### 5.4 Rician Fading

```python
import numpy as np
from core.physics import Physics

np.random.seed(42)
fading = Physics.rician_fading(K_factor_dB=10)
print(f"Fading coefficient: {fading:.4f}")
```

---

## Part 6 — Feedback and Adaptive Control

### 6.1 Creating a Feedback Channel

RISNet models the UE→AP feedback path for closed-loop beam adaptation.

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# Establish feedback: UE reports SNR measurements back to AP
net.create_feedback_channel(
    ue_name='ue1',
    ris_name='ris1',
    feedback_interval=0.1,   # seconds
    snr_threshold_dB=15.0,
)

# Connect with feedback enabled
result = net.connect(
    'ap1', 'ris1', 'ue1',
    use_get_snr=False,
    enable_feedback=True,
)
print(f"SNR after adaptation: {result['snr_dB']:.1f} dB")
```

### 6.2 Feedback Statistics

```python
stats = net.get_feedback_statistics()
for ue_ris, s in stats.items():
    print(f"{ue_ris}: {s}")
```

---

## Part 7 — Waveform-Level Simulation

System-level simulation uses a link budget formula. Waveform-level simulation
runs a full OFDM signal through the channel and measures per-subcarrier SNR.

### 7.1 OFDM Configuration

```python
import numpy as np
from core.waveform import OFDMConfig, OFDMSignal, calculate_papr

config = OFDMConfig(
    bandwidth=100e6,        # 100 MHz
    num_subcarriers=256,
    center_frequency=10e9,  # 10 GHz
)

ofdm = OFDMSignal(config, num_symbols=20)
tx_signal = ofdm.generate(seed=42)

power = np.mean(np.abs(tx_signal)**2)
papr  = calculate_papr(tx_signal)
print(f"Signal power: {power:.4f}")
print(f"PAPR:         {papr:.2f} dB")
```

### 7.2 RIS Reflection Model

```python
from core.waveform import RISReflectionModel
import numpy as np

# N×N element grid, 2-bit quantization, 10 GHz center frequency
ris_model = RISReflectionModel(N=4, bits=2, center_freq=10e9)

# Set ideal phases (radians, one per element)
num_elements = ris_model.num_elements   # N*N = 16
ideal_phases = np.linspace(0, 2 * np.pi, num_elements)

ris_model.set_phase_config(ideal_phases)

# Compute RMS quantization error
error_rad = ideal_phases - ris_model.quantized_phases
rms_error = np.sqrt(np.mean(error_rad**2))
print(f"Phase RMS error: {np.degrees(rms_error):.2f}°")
print(f"Num elements: {num_elements}")
```

### 7.3 Waveform vs System-Level SNR

```python
import random
import numpy as np
from core import RISNetwork
from core.waveform import OFDMConfig
from controller.waveform_controller import WaveformController

def set_deterministic_seeds(seed=42):
    np.random.seed(seed)
    random.seed(seed)

set_deterministic_seeds(42)

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1',  0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

# System-level
sys_result = net.connect('ap1', 'ris1', 'ue1', use_get_snr=False)
print(f"System-level SNR:   {sys_result['snr_dB']:.2f} dB")

# Waveform-level (returns snr_ris_dB and snr_effective_dB, not snr_dB)
wc = WaveformController(net)
wav_result = wc.compute_waveform_snr('ap1', 'ris1', 'ue1', num_symbols=20)
print(f"Waveform RIS SNR:      {wav_result['snr_ris_dB']:.2f} dB")
print(f"Waveform effective SNR:{wav_result['snr_effective_dB']:.2f} dB")
```

Both approaches should produce consistent results within a few dB for the
same topology and seed.

### 7.4 Waveform Beam Sweep

```python
wc = WaveformController(net)
sweep = wc.compute_beam_sweep_waveform(
    'ap1', 'ris1', 'ue1',
    angle_range=60,   # ±30° sweep
    angle_step=5,
)

for angle, snr in zip(sweep['angles'], sweep['snr_values']):
    marker = " <-- BEST" if angle == sweep['best_angle'] else ""
    print(f"  {angle:+5.1f}°: {snr:.2f} dB{marker}")

print(f"Best angle: {sweep['best_angle']:.1f}°  SNR: {sweep['best_snr_dB']:.2f} dB")
```

---

## Part 8 — ML-Guided Beam Sweeping

ML predictors learn a mapping from topology geometry to optimal beam angle,
then pass predicted candidates to the sweep for refinement.

### 8.1 Using a Pre-Trained Predictor

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
    ml_predictor='rf',   # 'rf', 'xgb', 'svr', 'knn', 'lgbm', etc.
)
print(f"Best angle: {result['best_local_fine']:.1f}°")
print(f"Best SNR:   {result['best_snr_fine']:.1f} dB")
```

Requires pre-trained model files in `controller/beamsweeping/ml/models/`.

### 8.2 Listing Available Predictors

```python
from controller.beamsweeping.ml import MLPredictorLoader

predictors = MLPredictorLoader.list_predictors()
for name, info in predictors.items():
    print(f"{name}: {info['description']}")
```

### 8.3 Training Your Own Model

The dataset builder and training scripts are in
`controller/beamsweeping/ml/tools/`. Run them from the repository root with
`PYTHONPATH=.` so all packages resolve correctly.

```bash
# 1. Generate a dataset
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/dataset_builder.py

# 2. Train predictors (after dataset is generated)
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_rf.py
PYTHONPATH=. python3 controller/beamsweeping/ml/tools/train_xgb.py

# 3. Use the trained model
PYTHONPATH=. python3 - <<'PY'
from core import RISNetwork
from controller.beamsweeping import SweepAlgorithmLoader

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

loader = SweepAlgorithmLoader(net)
algo = loader.get_algorithm('ml-guided')
result = algo.sweep('ap1', 'ris1', 'ue1', fov=60, step=10, ml_predictor='rf')
print(f"SNR: {result['best_snr_fine']:.1f} dB")
PY
```

### 8.4 Prediction Metrics

```python
from controller.beamsweeping.ml import MLPredictorLoader
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0)
net.add_ris('ris1', 5, 0, max_angle_deg=90)
net.add_ue('ue1', 10, 3)

predictor = MLPredictorLoader.get_predictor('rf', net)
angles, metrics = predictor.predict_with_metrics(
    'ap1', 'ris1', 'ue1', fov=60, top_k=3
)

print(f"Predicted angles:   {angles}")
print(f"Prediction time:    {metrics['prediction_time_ms']:.3f} ms")
print(f"Uncertainty:        ±{metrics['uncertainty']:.1f}°")
```

---

## Part 9 — Adding a Custom Beam Sweep Algorithm

### 9.1 Algorithm Template

```python
# File: controller/beamsweeping/algorithms/my_sweep.py
from ..base import SweepAlgorithmBase
from ..registry import register_algorithm

@register_algorithm("my-sweep", aliases=("my-alias",))
class MySweep(SweepAlgorithmBase):

    @property
    def name(self):
        return "My Sweep"

    @property
    def description(self):
        return "Custom beam sweep algorithm"

    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, **kwargs):
        ap  = self.network.get(ap_name)
        ris = self.network.get(ris_name)
        ue  = self.network.get(ue_name)

        import numpy as np
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

### 9.2 Registering and Using It

```python
# Import to trigger registration
import controller.beamsweeping.algorithms.my_sweep

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
risnet> sweep ap1 ris1 ue1 45 5 --algo my-sweep
```

---

## Part 10 — Loading Scenarios from JSON

### 10.1 Load a JSON Topology

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

### 10.2 Save a Session Topology

```python
import json

state = {
    "nodes": [
        {"name": "ap1",  "type": "AccessPoint", "pos": [0, 0, 0], "power_dBm": 20},
        {"name": "ris1", "type": "RIS",          "pos": [5, 0, 0], "N": 16, "bits": 2},
        {"name": "ue1",  "type": "UE",           "pos": [10, 3, 0]},
    ],
    "walls": [
        {"start": [3, -3], "end": [3, 3], "attenuation_dB": 20}
    ]
}

with open('my_scenario.json', 'w') as f:
    json.dump(state, f, indent=2)
```

---

## Part 11 — Multi-RIS Network

```python
from core import RISNetwork

net = RISNetwork(enable_messaging=False)
net.add_ap('ap1', 0, 0, power_dBm=23)

# Two RIS panels at different positions
net.add_ris('ris1', 5,  2, N=32, bits=2, max_angle_deg=90)
net.add_ris('ris2', 5, -2, N=32, bits=2, max_angle_deg=90, normal_angle_deg=0)

net.add_ue('ue1', 12, 0)
net.add_wall([3, -5], [3, 5], attenuation_dB=15)

# Compare paths through each RIS
for ris in ['ris1', 'ris2']:
    result = net.connect('ap1', ris, 'ue1', use_get_snr=False)
    print(f"Via {ris}: SNR={result['snr_dB']:.1f} dB  "
          f"angle={result['beam_angle']:.1f}°")
```

---

## Part 12 — Batch Sweep and Parameter Study

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

# Print table
print(f"{'N':>4}  {'bits':>4}  {'SNR':>8}  {'gain':>8}  {'qloss':>8}")
for r in results:
    print(f"{r['N']:>4}  {r['bits']:>4}  "
          f"{r['snr_dB']:>8.2f}  {r['gain_dBi']:>8.2f}  "
          f"{r['quant_loss_dB']:>8.3f}")
```

---

## Next Steps

- Run the example scripts in `examples/script/` for more complete demonstrations.
- See `docs/ML_GUIDED_SWEEP.md` for detailed ML predictor documentation.
- See `FUTURE.md` for the v3 architecture roadmap (spatial channels, entity-component model, runtime kernel, AI-native interfaces).
- See `INSTALL.md` for dependency management and troubleshooting.
