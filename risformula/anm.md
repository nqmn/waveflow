# RIS Localization Combined Method (ANM-Based)

## Overview

Combined near-field/far-field localization method using Atomic Norm Minimization (ANM) for RIS-assisted positioning. Automatically detects propagation regime and applies appropriate localization algorithm.

---

## Function Definition

```
FUNCTION RIS_Localization_Combined(Y, RIS_params, lambda, threshold, K_est):

    # -------------------------------------------------------
    # INPUT DEFINITIONS
    # -------------------------------------------------------
    # Y            : complex array (N_x × N_z × M)
    #                Where M = number of phase configurations
    # RIS_params   : {D_x, D_z, N_x, N_z, d_x, d_z, position}
    # lambda       : wavelength
    # threshold    : curvature threshold for near/far detection
    # K_est        : estimated number of paths (usually 1)
    #
    # -------------------------------------------------------
    # OUTPUT DEFINITIONS
    # -------------------------------------------------------
    # mode         : "far-field" or "near-field"
    # location     :
    #                if far-field → {azimuth, elevation, type="direction-only"}
    #                if near-field → {x, y, z, type="3D-location"}
    # confidence   : optional confidence score (0–1)
    # -------------------------------------------------------


    # =======================================================
    # STEP 1 — Preprocess signal
    # =======================================================
    y_vector = Flatten_OR_Average(Y)
        # Convert RIS 2D array per phase into 1D vector
        # Example: y_vector size = (N_x*N_z) × 1


    # =======================================================
    # STEP 2 — Fast initial far-field ANM to get rough angle
    # =======================================================
    (theta_init, alpha_init) = ANM_FARFIELD(y_vector,
                                            N = RIS_params.N_x * RIS_params.N_z,
                                            lambda,
                                            d = mean(RIS_params.d_x, RIS_params.d_z),
                                            K_est)


    # =======================================================
    # STEP 3 — Estimate phase curvature
    # =======================================================
    curvature = ComputePhaseCurvature(y_vector, theta_init)
        # curvature = variance of 2nd-order phase difference


    # =======================================================
    # STEP 4 — Auto decision: Near-field or Far-field
    # =======================================================
    IF curvature < threshold:
        mode = "far-field"
    ELSE:
        mode = "near-field"


    # =======================================================
    # STEP 5 — RUN CORRESPONDING LOCALIZATION ALGORITHM
    # =======================================================

    IF mode == "far-field":

        # Run full far-field ANM
        (angles, amplitudes) = ANM_FARFIELD(y_vector,
                                             N = RIS_params.N_x * RIS_params.N_z,
                                             lambda,
                                             d = mean(RIS_params.d_x, RIS_params.d_z),
                                             K_est)

        location = {
            "azimuth"   : angles.azimuth,
            "elevation" : angles.elevation,
            "type"      : "direction-only"
        }
        confidence = ComputeConfidenceFarField(curvature)


    ELSE IF mode == "near-field":

        # Run full near-field 2D ANM
        (x, y, z) = ANM_NEARFIELD_SEPARABLE(Y,
                                            RIS_params.N_x,
                                            RIS_params.N_z,
                                            lambda,
                                            RIS_params.d_x,
                                            RIS_params.d_z,
                                            K_est)

        location = {
            "x"     : x,
            "y"     : y,
            "z"     : z,
            "type"  : "3D-location"
        }
        confidence = ComputeConfidenceNearField(curvature)


    # =======================================================
    # STEP 6 — RETURN OUTPUT
    # =======================================================
    RETURN mode, location, confidence

END FUNCTION
```

---

## Implementation in RISNet

### Current RISNet Capabilities

✅ **Already Available**:
- Measurement system: Scalar SNR measurements at multiple beam angles
- RIS parameters: Full geometry (N, spacing, positions, frequency)
- Far-field beam steering: Operational in all sweep algorithms
- Near-field focusing code: Exists in `pattern_gen_hybrid.py`
- 3D coordinate system: AP/RIS/UE positions tracked
- Deflection angles: Incident/reflected azimuths computed

⚠️ **Needs Implementation**:
- ANM solver (CVX/CVXPY required)
- Phase curvature detection algorithm
- Near-field mode integration into sweep flow
- Separable 2D ANM for 3D localization

---

### Proposed Implementation Architecture

#### **Option A: New Sweep Algorithm** (Recommended)

```
controller/beamsweeping/algorithms/anm_localization_sweep.py
```

Inherits from `SweepAlgorithmBase` with these stages:
1. Run coarse far-field sweep (reuse existing algorithms)
2. Compute phase curvature from SNR response curve
3. Classify propagation mode (near/far field)
4. Apply appropriate ANM solver
5. Return structured location output

#### **Option B: Standalone Localization Module**

```
controller/localization/
├── anm_solver.py          # CVX-based ANM implementation
├── nearfield_detector.py  # Phase curvature analysis
├── manifold_builder.py    # Generate steering vectors from RIS geometry
└── combined_localizer.py  # Main orchestrator
```

More flexible for research but requires more integration work.

---

## Algorithm Details

### ANM Far-Field

**Goal**: Estimate direction-of-arrival (azimuth, elevation) using atomic norm minimization.

**Problem Formulation**:
```
minimize    ||y - A(θ)·α||₂² + λ·||α||_*
subject to  θ ∈ [-π/2, π/2]

where:
  y       = received signal vector (N×1)
  A(θ)    = steering matrix (N×G) for grid of angles θ
  α       = sparse coefficient vector (G×1)
  ||·||_* = atomic norm (convex relaxation of sparsity)
```

**Steering Vector** (Far-Field):
```
a(θ) = [e^(j·k·d·n·sin(θ))]  for n = 0, 1, ..., N-1

where:
  k = 2π/λ  (wavenumber)
  d = element spacing
  θ = azimuth angle
```

**Output**:
- Angle estimates: θ̂ = argmax |α|
- Confidence: Based on SNR peak sharpness

---

### ANM Near-Field

**Goal**: Estimate 3D position (x, y, z) using separable near-field model.

**Problem Formulation** (Separable):
```
Step 1: Estimate x-coordinate using x-axis measurements
  minimize ||y_x - A_x(x)·α_x||₂² + λ·||α_x||_*

Step 2: Estimate z-coordinate using z-axis measurements
  minimize ||y_z - A_z(z)·α_z||₂² + λ·||α_z||_*

Step 3: Compute y-coordinate from geometry
  y = √(r² - x² - z²)
  where r = estimated range
```

**Steering Vector** (Near-Field):
```
a_x(x) = [e^(j·k·√((x-x_n)² + y₀² + z₀²))]  for n = 0, 1, ..., N_x-1

where:
  x_n = n·d_x  (element position along x-axis)
  y₀, z₀ = assumed y, z coordinates for 2D slice
```

**Output**:
- 3D position: (x̂, ŷ, ẑ)
- Confidence: Based on curvature strength

---

### Phase Curvature Detection

**Purpose**: Distinguish near-field from far-field based on wavefront curvature.

**Method**:
```
1. Measure SNR response: snr(θ) for θ ∈ [θ_min, θ_max]

2. Compute second-order differences:
   Δ²snr(i) = snr(i+1) - 2·snr(i) + snr(i-1)

3. Calculate curvature metric:
   curvature = var(Δ²snr) / mean(snr)²

4. Classify:
   IF curvature < threshold:
       mode = "far-field"  (planar wavefront)
   ELSE:
       mode = "near-field"  (spherical wavefront)
```

**Threshold Selection**:
- Use Fraunhofer distance: D_F = 2D²/λ
  - If range r > D_F → far-field
  - If range r < D_F → near-field
- Typical threshold: `curvature_threshold = 0.1` (empirical)

**Physical Intuition**:
- Near-field: Sharp SNR peaks → high curvature
- Far-field: Broad SNR peaks → low curvature

---

## Integration with RISNet

### Data Flow

```
User Request
    ↓
ANMLocalizationSweep.sweep()
    ↓
1. Validate nodes (AP, RIS, UE)
    ↓
2. Compute incident/reflected azimuths
    ↓
3. Run coarse sweep (existing algorithm)
    ↓
4. Collect SNR measurements → y_vector
    ↓
5. Compute phase curvature
    ↓
6. Classify mode (near/far)
    ↓
7a. Far-field branch         7b. Near-field branch
    ANM_FARFIELD()               ANM_NEARFIELD_SEPARABLE()
    ↓                            ↓
    {azimuth, elevation}         {x, y, z}
    ↓                            ↓
8. Return structured result
    {
      'mode': 'far-field' | 'near-field',
      'location': {...},
      'confidence': float,
      'curvature': float,
      'measurements': y_vector,
      'metadata': {...}
    }
```

### RIS Phase Configuration

**Far-Field Mode** (Already Implemented):
```python
# Uses linear steering phases
phi_steering = -k * x_i * sin(theta_target)
phi_incident = k * sqrt(x_i² + y_i² + r_src²)
phi_total = phi_incident + phi_steering
```

**Near-Field Mode** (Code Exists, Not Integrated):
```python
# Uses spherical focusing phases
phi_focusing = -k * sqrt((x_i - x_target)² + (y_i - y_target)² + (z_i - z_target)²)
phi_incident = k * sqrt(x_i² + y_i² + r_src²)
phi_total = phi_incident + phi_focusing
```

---

## Mathematical Background

### Atomic Norm

**Definition**: Convex relaxation of sparse recovery problem.

For signal model `y = ∑ α_k · a(θ_k)`, the atomic norm is:
```
||α||_* = inf{ t > 0 : α ∈ t·conv(A) }

where:
  A = {a(θ) : θ ∈ [-π/2, π/2]}  (set of steering vectors)
  conv(A) = convex hull of A
```

**Semidefinite Programming (SDP) Formulation**:
```
minimize    λ·trace(T) + ||y - u||₂²
subject to  [T      u  ]
            [u^H    1  ] ≽ 0   (positive semidefinite)

            T is Toeplitz

Variables: T (matrix), u (vector)
```

**Solver**: Use CVXPY with SCS/MOSEK backend.

---

### Near-Field vs Far-Field Transition

**Fraunhofer Distance**:
```
D_F = 2D²/λ

where:
  D = RIS aperture size
  λ = wavelength
```

**Example** (28 GHz, 16×16 RIS with λ/2 spacing):
- D = 16 × (λ/2) = 8λ = 8.57 cm
- D_F = 2 × (8.57 cm)² / 1.07 cm ≈ 137 cm
- Near-field: r < 1.37 m
- Far-field: r > 1.37 m

**Curvature Scaling**:
```
Phase curvature ∝ D²/(λ·r)

Near-field (r = 0.5 m):  High curvature → Sharp beams
Far-field (r = 10 m):    Low curvature → Broad beams
```

---

## Performance Considerations

### Computational Complexity

**Far-Field ANM**:
- SDP solver: O(N³·G²) per iteration
- Grid size G ≈ 100-500 angles
- RIS size N = 256 elements
- Runtime: ~1-5 seconds (CVXPY + SCS)

**Near-Field ANM** (Separable):
- 2D decomposition: O(N_x³·G_x² + N_z³·G_z²)
- Faster than full 3D: O((N_x·N_z)³·G_x³·G_z³)
- Runtime: ~2-10 seconds

**Optimization**:
- Use coarse-to-fine grid refinement
- Warm-start SDP solver with far-field solution
- Parallelize x/z dimension solving

---

### Measurement Requirements

**Minimum Measurements**:
- Far-field: M ≥ 2K (K = number of targets)
- Near-field: M ≥ 3K (need 3D information)

**RISNet Sweep Coverage**:
- Typical sweep: 10-50 measurements (depends on step size)
- Adequate for single-target localization (K=1)
- May need denser sampling for multi-target (K>1)

**SNR Requirements**:
- Far-field: SNR > 0 dB (moderate)
- Near-field: SNR > 10 dB (higher due to curvature sensitivity)

---

## Implementation Roadmap

### Phase 1: Far-Field Only
1. Implement `ANM_FARFIELD()` using CVXPY
2. Build steering matrix from RIS geometry
3. Integrate with existing sweep measurements
4. Validate against known UE angles

### Phase 2: Curvature Detection
1. Implement `ComputePhaseCurvature()`
2. Analyze SNR response sharpness
3. Set threshold based on Fraunhofer distance
4. Test with UEs at varying distances

### Phase 3: Near-Field Extension
1. Activate spherical focusing in `PhaseSteeringEngine`
2. Implement `ANM_NEARFIELD_SEPARABLE()`
3. Add 2D phase scan capability
4. Validate 3D position accuracy

### Phase 4: Full Integration
1. Create `ANMLocalizationSweep` class
2. Auto-detect mode from initial measurements
3. Add confidence scoring
4. Performance benchmarking

---

## References

### Key Papers
1. **Atomic Norm Minimization**:
   - Bhaskar et al., "Atomic Norm Denoising with Applications to Line Spectral Estimation", IEEE TSP 2013

2. **Near-Field RIS Localization**:
   - Hu et al., "Near-Field Localization for RIS-Aided Systems", IEEE TWC 2023
   - Elzanaty et al., "RIS-Aided Near-Field Localization", IEEE SPAWC 2022

3. **RIS Phase Design**:
   - Wu & Zhang, "Intelligent Reflecting Surface Enhanced Wireless Network via Joint Active and Passive Beamforming", IEEE TWC 2019

### CVX Resources
- CVXPY Documentation: https://www.cvxpy.org/
- SCS Solver: https://github.com/cvxgrp/scs
- Toeplitz Constraint Example: CVXPY Examples → Semidefinite Programming

---

## Feasibility Summary

| Component | Status | Effort | Notes |
|-----------|--------|--------|-------|
| **Measurement System** | ✅ Ready | None | SNR sweep data available |
| **RIS Geometry** | ✅ Ready | None | All parameters tracked |
| **Far-Field Steering** | ✅ Ready | None | Operational in all sweeps |
| **Near-Field Focusing** | ⚠️ Available | Low | Code exists, needs integration |
| **ANM Solver** | ❌ To Implement | Medium | CVXPY + SDP formulation |
| **Curvature Detection** | ❌ To Implement | Low | ~50 lines of code |
| **Full Integration** | ❌ To Implement | Medium | New sweep algorithm class |

**Estimated Timeline**: 2-3 weeks for full implementation and validation.

---

## Example Usage (Future)

```python
from controller.beamsweeping.algorithms.anm_localization_sweep import ANMLocalizationSweep

# Initialize network
network = RISNetwork()
network.add_node('AP1', position=[0, 0, 5])
network.add_node('RIS1', position=[5, 0, 3], N=16)
network.add_node('UE1', position=[8, 3, 1.5])

# Run localization
algo = ANMLocalizationSweep()
result = algo.sweep(
    ap_name='AP1',
    ris_name='RIS1',
    ue_name='UE1',
    fov=120,
    step=2.0,
    curvature_threshold=0.1,
    K_est=1
)

# Output
print(f"Mode: {result['mode']}")
if result['mode'] == 'far-field':
    print(f"Azimuth: {result['location']['azimuth']:.1f}°")
    print(f"Elevation: {result['location']['elevation']:.1f}°")
else:
    print(f"Position: ({result['location']['x']:.2f}, "
          f"{result['location']['y']:.2f}, "
          f"{result['location']['z']:.2f}) m")
print(f"Confidence: {result['confidence']:.2f}")
```

---

## Conclusion

The proposed ANM-based combined localization method is **highly feasible** with the current RISNet architecture. The codebase provides ~80% of required infrastructure:
- ✅ Measurement system ready
- ✅ RIS phase control flexible
- ✅ Geometry fully specified
- ⚠️ ANM solver needs custom implementation
- ⚠️ Near-field mode needs activation

Primary development tasks:
1. Implement CVX-based ANM solver (~300 lines)
2. Add phase curvature detection (~100 lines)
3. Integrate near-field mode (~200 lines)
4. Create new sweep algorithm wrapper (~400 lines)

**Total estimated effort**: ~1000 lines of code + testing/validation.
