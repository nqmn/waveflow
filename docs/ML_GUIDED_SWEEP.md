# ML-Guided Beam Sweep Strategy

## Overview

The ML-Guided Beam Sweep is an intelligent beam optimization algorithm that combines machine learning predictions with real measurement validation. It identifies promising beam angles using pre-trained ML models, then tests those predictions to find the actual best performer.

**Key Insight:** ML predictions are fast but imperfect. This strategy validates predictions through measurement, ensuring you get the best angle while staying efficient.

## Strategy Architecture

### Two-Stage Process

```
┌─────────────────────────────────────────────────────────────┐
│ STAGE 1: ML PREDICTION                                      │
│                                                              │
│  Input: Node geometry (positions, distances)                │
│  ↓                                                           │
│  ML Model predicts top-K candidate angles                   │
│  ↓                                                           │
│  Output: [angle_1, angle_2, ..., angle_K]                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ STAGE 2: VALIDATION THROUGH MEASUREMENT                     │
│                                                              │
│  For each predicted angle:                                  │
│    - Test the angle (measure SNR)                           │
│    - Store result                                           │
│  ↓                                                           │
│  Select angle with HIGHEST measured SNR                     │
│  ↓                                                           │
│  Output: Best angle (actual, not predicted)                 │
└─────────────────────────────────────────────────────────────┘
```

## How It Works

### Stage 1: ML Prediction

The algorithm loads a pre-trained ML model and extracts geometry features from the network:

**Features Used (15 total):**
- **Node Positions (9):** AP (x, y, z), RIS (x, y, z), UE (x, y, z)
- **Distances (2):** AP→RIS distance, RIS→UE distance
- **Hardware (4):** AP power, frequency, RIS element count, phase quantization bits

**ML Models Available:**
- **XGBoost** (default): Best accuracy, R² = 0.9438
- **Random Forest**: Good accuracy, R² = 0.9313
- **SVR (Support Vector Regression)**: High accuracy, R² = 0.8830
- **KNN (K-Nearest Neighbors)**: Local pattern recognition, R² = 0.8721
- **Linear Regression**: Simple baseline, R² = 0.7842

The model predicts the top-K angles most likely to have high SNR.

### Stage 2: Validation Through Measurement

For each predicted angle, the algorithm:
1. **Sets the beam** to the predicted angle
2. **Measures SNR** through actual signal simulation (physics + waveform)
3. **Records result** with full metrics (SNR, power, SER)
4. **Compares all** to find the winner

**Final Selection:** Returns the angle with the **highest measured SNR**, not the ML prediction.

## Efficiency vs Accuracy Trade-off

### Performance Comparison

| Metric | Linear Sweep | ML-Guided Sweep |
|--------|-------------|-----------------|
| **Measurements** | FOV ÷ Step (e.g., 120÷10 = 12) | Top-K (e.g., 5) |
| **Angle Count** | 12 angles | 5 angles |
| **Efficiency** | 100% (baseline) | ~42% fewer tests |
| **Accuracy** | Guaranteed best angle | Near-guaranteed best angle* |

*ML predictions have high accuracy (R² > 0.94), so top-K usually contains the global optimum.

### When to Use ML-Guided

**Use when:**
- You want **faster results** than exhaustive search
- **Measurement budget is limited** (fewer tests allowed)
- **Pre-trained model available** for your geometry
- **Trade-off acceptable:** ~5-10% risk of missing absolute best for 50-60% speedup

**Don't use when:**
- You **absolutely need** the guaranteed global optimum
- **Measurements are free** (no latency/power budget)
- **No trained model** available for your scenario

## Implementation Details

### Class: `MLGuidedSweep`

**Location:** `controller/beamsweeping/algorithms/ml_guided_sweep.py`

**Registration:**
```python
@register_algorithm("ml", aliases=("ml-guided",))
class MLGuidedSweep(SweepAlgorithmBase):
```

**Command Line Usage:**
```bash
# With XGBoost (default, fastest, best accuracy)
connect ap1 ris1 ue1 --sweep 60 10 --algo ml

# With specific predictor
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor rf    # Random Forest
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor knn   # KNN
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor svr   # SVR
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor lr    # Linear Regression

# With signal-level simulation
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --modulation 16QAM
```

### Key Parameters

```python
def sweep(self,
    ap_name: str,
    ris_name: str,
    ue_name: str,
    fov: float = 60.0,           # Field of view (±degrees from incident)
    step: float = 10.0,           # Not used in ML-guided mode
    seed: int = 42,               # Random seed for reproducibility
    enable_feedback: bool = True, # Closed-loop adaptation per angle
    max_feedback_iterations: int = 3,  # Max iterations per angle
    ml_predictor: str = 'xgb',   # Which ML model to use
    top_k: int = 5,              # Number of predictions to validate
    codebook_increment: float = 5.0,  # Discretize predictions to this step
    codebook_neighbors: int = 1,      # How many increments on each side to test
    enable_codebook_validation: bool = False, # Quantize and verify neighbors (disabled by default)
    include_predicted_angle: bool = True,    # Also test the raw prediction
    use_waveform: bool = False,  # Real signal-level simulation
    modulation: str = 'QPSK',    # Modulation type (QPSK, 16QAM, 64QAM)
    num_symbols: int = 1000      # Symbols per measurement
) -> Dict:
```

By default ML predictions are used as-is—no quantization or neighbor validation happens. If you want to validate a small codebook around each suggestion, set `enable_codebook_validation` to `True`, adjust `codebook_increment` (defaults to 5°), and `codebook_neighbors` to the number of steps you want to test on each side. That keeps the measurement budget small while compensating for the predictor’s ±5° MAE.

### Return Value

```python
{
    'ml_predictor': 'xgb',              # Which model was used
    'ml_suggestions': [45.2, 48.1, ...], # Raw ML predictions
    'ml_results': [                      # Detailed results per angle
        {
            'local_angle': 45.2,         # Deflection angle
            'abs_angle': 125.5,          # Absolute beam angle
            'snr_dB': 18.3,              # Measured SNR
            'pwr_dBm': -65.2,            # Received power
            'ser_percent': 0.5           # Symbol error rate (if waveform enabled)
        },
        ...
    ],
    'best_angle': 125.5,                 # Best absolute angle found
    'best_snr': 18.3,                    # Best SNR measured
    'best_local': 45.2,                  # Best deflection angle
    'num_predictions': 5,                 # ML suggestions that were generated
    'num_angles_tested': 13,              # Actual measurements recorded
    'codebook_increment': 5.0,            # Quantization step used during validation
    'codebook_neighbors': 1,              # ± neighbors tested around each codebook value
    'codebook_validation_enabled': True,  # Whether the quantization/neighbor loop ran
    'ml_metrics': {...},                 # Confidence metrics from ML model
    'specular_angle': 80.3               # Reference incident angle
}
```

## Example Workflow

### Setup Network
```python
from risnet import Network

net = Network()
net.add_ap('AP1', x=0, y=0, z=0)
net.add_ris('RIS1', x=10, y=0, z=2, N=16, bits=1)
net.add_ue('UE1', x=15, y=5, z=1)
```

### Run ML-Guided Sweep
```python
from controller.beamsweeping import SweepAlgorithmLoader

algo = SweepAlgorithmLoader.get_algorithm('ml', net)
result = algo.sweep(
    ap_name='AP1',
    ris_name='RIS1',
    ue_name='UE1',
    fov=60.0,
    ml_predictor='xgb',    # Use XGBoost
    top_k=5,               # Test top 5 predictions
    use_waveform=True,     # Real signal simulation
    modulation='16QAM'
)

print(f"Best angle: {result['best_angle']:.2f}°")
print(f"Best SNR: {result['best_snr']:.2f} dB")
print(f"Tested {result['num_angles_tested']} angles")
```

### CLI Usage
```bash
# In RISNet CLI
risnet> add random          # Create random topology
risnet> connect AP1 R1 UE1 --sweep 60 10 --algo ml --ml-predictor xgb
```

## ML Model Details

### Feature Engineering

Each predictor uses the same 15-dimensional feature vector:

```python
features = [
    ap.pos[0], ap.pos[1], ap.pos[2],      # AP position (xyz)
    ris.pos[0], ris.pos[1], ris.pos[2],   # RIS position (xyz)
    ue.pos[0], ue.pos[1], ue.pos[2],      # UE position (xyz)
    np.linalg.norm(ris.pos - ap.pos),     # AP→RIS distance
    np.linalg.norm(ue.pos - ris.pos),     # RIS→UE distance
    ap.power_dBm,                          # AP transmit power
    ap.freq,                               # Frequency (Hz)
    ris.N,                                 # RIS element count
    ris.bits                               # Phase quantization bits
]
```

### Training Dataset

Models trained on `controller/beamsweeping/ml/data/beam_dataset.csv`:
- **Sampling mode:** Default `ris-aware` matches `add random`; pass `--sampling-mode stratified` with higher `--ap/--ris/--ue-bins` (e.g., `20 20 5`) when you need full cube coverage.
- **Samples:** ~1000 different geometries
- **Target:** Optimal local deflection angle for each geometry
- **Validation:** Test on unseen geometries
Regenerate the dataset with `python3 controller/beamsweeping/ml/tools/dataset_builder.py --samples 10000` (RIS-aware mode defaults to 5–7 m), or switch to `--sampling-mode stratified` when you want systematic spatial coverage.

### Model Selection Guide

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| **XGBoost** | Fast | Best (R²=0.94) | Default choice |
| **Random Forest** | Fast | Very Good (R²=0.93) | Stable predictions |
| **SVR** | Slow | High (R²=0.88) | Smooth manifold |
| **KNN** | Very Fast | Good (R²=0.87) | Nearest neighbor logic |
| **Linear Regression** | Fastest | Fair (R²=0.78) | Quick prototyping |

## Measurement Phases

### Per-Angle Measurement

For each predicted angle, the algorithm performs:

1. **AP State Guard:** Save/restore AP state across measurements
2. **Connect:** Establish link with specified beam angle
3. **Waveform Simulation:** If enabled, simulate real signal (QPSK/16QAM/64QAM)
4. **SNR Extraction:** Measure or compute SNR
5. **SER Calculation:** If waveform enabled, calculate symbol error rate

**Output:** SNR, power, SER for each angle tested

### Result Selection

```python
# Find best measured SNR (not best prediction)
best_idx = np.argmax(snr_values)
best_angle = local_angles[best_idx]
best_snr = snr_values[best_idx]
```

## Advanced Options

### Closed-Loop Feedback

Each measurement can adapt using closed-loop feedback:

```python
result = algo.sweep(
    ...,
    enable_feedback=True,           # Enable adaptive refinement
    max_feedback_iterations=3       # Up to 3 adaptation rounds
)
```

**What it does:**
- After initial angle measurement, refine the angle slightly
- Repeat up to 3 times to converge on local optimum
- Increases accuracy but uses more measurements

### Waveform Simulation

Enable real signal-level simulation for accurate SNR:

```python
result = algo.sweep(
    ...,
    use_waveform=True,              # Real signal simulation
    modulation='16QAM',             # Modulation scheme
    num_symbols=1000                # Symbols per measurement
)
```

**Modulation Options:**
- `'QPSK'` - Quadrature Phase Shift Keying (2 bits/symbol)
- `'16QAM'` - 16-point Quadrature Amplitude Modulation (4 bits/symbol)
- `'64QAM'` - 64-point QAM (6 bits/symbol)

**Output includes:**
- `'snr_dB'` - SNR under this modulation
- `'ser_coarse'` - Symbol error rate for each angle
- `'ser_percent'` - Percent of symbols with errors

## Performance Notes

### Speedup Analysis

For FOV=60°, Step=10°:
- **Linear Brute-Force:** 12 measurements
- **ML-Guided (top_k=5):** 5 measurements
- **Speedup:** 2.4× fewer tests

### Accuracy Analysis

On test dataset:
- **XGBoost:** Top-K contains global optimum 96% of the time
- **Random Forest:** Top-K contains global optimum 94% of the time
- **SVR:** Top-K contains global optimum 91% of the time

**Interpretation:** In 96% of cases, the best angle is in the top-5 predictions.

## Troubleshooting

### Low Accuracy (Worse than Linear Sweep)

**Cause:** Top-K too small, missing global optimum
**Solution:** Increase `top_k` parameter
```python
algo.sweep(..., top_k=8)  # Test 8 instead of 5
```

### No ML Model Loaded

**Cause:** Model file not found or dependencies missing
**Error:** `RuntimeError: XGBoost model not available`
**Solution:**
```bash
# Ensure model exists
ls controller/beamsweeping/ml/models/

# Install xgboost if needed
pip install xgboost

# Or use different predictor
connect ap1 ris1 ue1 --sweep 60 10 --algo ml --ml-predictor rf
```

### Model Predicts Out-of-FOV Angles

**Cause:** Model trained on broader FOV
**Solution:** Automatic clamping to FOV bounds
```python
# Angles are automatically clamped to [-fov, +fov]
# No manual intervention needed
```

## Comparison with Other Strategies

### vs. Linear Brute-Force
- **Linear:** Tests every angle at fixed step → guaranteed optimum
- **ML-Guided:** Tests predicted angles → faster but ~5% miss rate
- **Choose Linear if:** Measurement budget huge, need guaranteed best
- **Choose ML-Guided if:** Want 50% speedup, high confidence okay

### vs. Coarse-Fine (Two-Phase)
- **Coarse-Fine:** Tests coarse grid, refines around peak → intelligent search
- **ML-Guided:** Tests ML predictions → orthogonal to step-based thinking
- **Combine them:** Could use ML predictions as coarse grid (future enhancement)

## Extending with New Models

### Adding a New Predictor

1. **Create new file** `controller/beamsweeping/ml/my_model.py`
2. **Inherit from** `SweepMLPredictor`
3. **Implement** `predict_local_angles()` and `predict_with_metrics()`
4. **Load model** in `__init__`
5. **Register** with predictor loader

```python
class MyPredictor(SweepMLPredictor):
    MODEL_ENV = "RISNET_MY_MODEL"
    DEFAULT_MODEL = Path("controller/beamsweeping/ml/models/my_model.pkl")

    def predict_local_angles(self, ap_name, ris_name, ue_name, fov, top_k=3):
        # Your prediction logic here
        pass
```

## References

- **Paper:** ML-guided beam sweeping for reconfigurable intelligent surfaces (RIS)
- **Models:** Trained on RIS beam sweep dataset with 1000+ geometries
- **Validation:** Cross-validation shows R² > 0.94 on test set

## See Also

- `LinearBruteForceSweep` - Exhaustive search baseline
- `CoarseFineSweep` - Two-phase intelligent search
- `DirectionalExhaustiveSweep` - Full codebook sweep
- ML Predictor classes in `controller/beamsweeping/ml/`
