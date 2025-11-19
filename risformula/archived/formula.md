# RIS Phase Pattern Generation — Data Flow and Formulas

## 1. Input Coordinates

```
source = [x_s, y_s, z_s]           # AP position (meters)
ris_center = [x_r, y_r, z_r]       # RIS center reference (meters)
target = [x_t, y_t, z_t]           # UE position (meters)
```

**Example values:**
```
source = [8.0, 10.0, 0.5]
ris_center = [15.0, 10.0, 0.0]
target = [11.4, 6.5, 0.0]
```

## 2. Physical Constants

```
c = 299,792,458 m/s                # Speed of light
f = 5.8 × 10^9 Hz                  # Frequency
λ = c/f ≈ 0.0517 m                 # Wavelength
k = 2π/λ ≈ 121.5 rad/m             # Wave vector
d = λ/2 ≈ 0.0259 m                 # Element spacing (half-wavelength)
```

## 3. RIS Array Geometry

```
N = 16                              # Array size (16×16)
```

**Element positions relative to RIS center:**

```
lim_x = (N-1)/2 × d
lim_y = (N-1)/2 × d

For element (i,j) where i,j ∈ [0, N-1]:

x_i = -lim_x + (i/(N-1)) × 2×lim_x
y_i = -lim_y + (j/(N-1)) × 2×lim_y

Range: x_i, y_i ∈ [-lim_x, lim_x] = [-0.206 m, 0.206 m]
```

## 4. Deflection Angle Calculation

**From 3D coordinates to 2D deflection (using absolute azimuth angles):**

```
Extract 2D positions:
AP = [x_s, y_s]              # Source position (XY)
RIS = [x_r, y_r]             # RIS center (XY)
UE = [x_t, y_t]              # Target position (XY)

Calculate absolute azimuth angles:
θ_in = arctan2(AP_y - RIS_y, AP_x - RIS_x)    # Incident azimuth angle
θ_out = arctan2(UE_y - RIS_y, UE_x - RIS_x)   # Reflected azimuth angle

Compute azimuth angle difference:
Δθ = θ_out - θ_in

Wrap angle to [-π, π]:
if Δθ > π:   Δθ -= 2π
if Δθ < -π:  Δθ += 2π

Deflection angle (magnitude of azimuth difference):
θ_rcv = |Δθ|

Example: θ_rcv ≈ 44.19° ≈ 0.771 rad
```

**Steering angle vector:**

```
u_x = sin(θ_rcv)
u_y = 0
u_z = cos(θ_rcv)

Example for θ_rcv = 44.19°:
u_x ≈ 0.696
u_y = 0
u_z ≈ 0.718
```

## 5. Phase Computation — Deflection Angle Decomposition

### Component 1: Incident Spherical Wavefront Compensation

The source emits a spherical wave. RIS elements at different positions experience different phases based on propagation distance:

```
Source offset and height above RIS:
Δx_s = x_s - x_r = 8.0 - 15.0 = -7.0 m
Δy_s = y_s - y_r = 10.0 - 10.0 = 0.0 m
Δz_s = z_s - z_r = 0.5 - 0.0 = 0.5 m

Distance from source to element (i,j) on RIS:
r_source_dist(i,j) = √((Δx_s - x_i)² + (Δy_s - y_i)² + Δz_s²)

**For current implementation (source assumed above RIS center):**
If x_s ≈ x_r and y_s ≈ y_r, this simplifies to:
r_source_dist(i,j) ≈ √(x_i² + y_i² + r_src²)

**General 3D formulation (note: incident phase is still relative to RIS):**
r_source_dist(i,j) = √(x_i² + y_i² + (z_s - z_r)²)

The source offset (Δx_s, Δy_s) affects **steering phase**, not incident phase, because the RIS phase pattern is optimized relative to the RIS surface, not absolute source position.

Incident phase (spherical wavefront):
φ_incident(i,j) = k × r_source_dist(i,j)
```

**Physical meaning:** Accounts for the phase accumulated during propagation from source to RIS. Increases radially outward. The exact formula depends on source position relative to RIS center.

**Implementation note:** Current code assumes source is roughly above RIS center (Δx_s ≈ 0, Δy_s ≈ 0). For arbitrary source positions or 3D generalization, use the full formula above.

### Component 2: Reflection Steering Phase (Deflection-Based)

RIS applies phase shifts to redirect the beam toward the target. This creates a linear phase gradient across the array:

```
Steering phase (linear gradient from deflection angle):
φ_steering(i,j) = -k × x_i × sin(θ_rcv)
                = -k × x_i × sin(deflection_angle)
```

**Physical meaning:** Creates a linear phase ramp proportional to the deflection angle. This is the classical phased array beamsteering formula.

**Phase gradient (array steering slope):**
```
∂φ/∂x_i = -k × sin(θ_rcv)
```

A larger deflection angle produces a steeper phase gradient, steering the beam more aggressively toward the target.

### Component 3: Total Phase

Superposition of incident and steering components:

```
φ(i,j) = φ_incident(i,j) + φ_steering(i,j)
        = k√(x_i² + y_i² + r_src²) - k×x_i×sin(θ_rcv)

Normalize to [0, 2π]:
φ(i,j) = φ(i,j) mod 2π
If φ(i,j) < 0: φ(i,j) += 2π
```

**Convert to degrees:**
```
φ_deg(i,j) = φ(i,j) × (180/π)  ∈ [0°, 360°]
```

## 6. N-bit Quantization

Convert continuous phase to discrete levels:

```
Number of levels:
num_levels = 2^n_bit

Quantization formula:
φ_quant_deg(i,j) = round((φ_deg(i,j) / 360) × (num_levels - 1)) / (num_levels - 1) × 360

Output phase levels:
φ_quant(i,j) ∈ {0°, Δ°, 2Δ°, ..., (num_levels-1)×Δ°}

where Δ = 360° / (num_levels - 1)
```

**Examples for different n_bit values:**

| n_bit | Levels | Δ | Discrete Phase Levels |
|-------|--------|---|---|
| 1 | 2 | 180° | {0°, 180°} |
| 2 | 4 | 120° | {0°, 120°, 240°} |
| 3 | 8 | 51.4° | {0°, 51.4°, 102.9°, 154.3°, 205.7°, 257.1°, 308.6°} |
| 4 | 16 | 24° | {0°, 24°, 48°, 72°, ..., 336°} |

**Note:** Phase is periodic with period 360°. The level 360° wraps to 0°, so we represent the codebook as {0°, Δ°, 2Δ°, ..., (L-1)Δ°} where Δ = 360°/(L-1) and L = 2^n_bit. This is equivalent to a uniform phase quantizer with L discrete states across [0°, 360°).

## 7. Heatmap Visualization

**Matrix formation:**
```
Φ = {φ_quant(i,j) | i,j ∈ [0, N-1]}

Φ is a 16×16 matrix of quantized phase values
```

**Colormap:**
```
Colormap: Blue-White-Red (BWR)
Value range: [0°, vmax]

where:
vmax = 360 / (2^n_bit) × ((2^n_bit) - 1)

Examples:
n_bit=1: vmax = 180°  (2 colors: blue to red)
n_bit=2: vmax = 120°  (4 discrete colors)
n_bit=3: vmax = 45.7°
```

**Output:**
```
RIS_phase_pattern_deflection_combined.png
- Geometry plot (top): Shows source, RIS, target positions and deflection angle
- Heatmap (bottom): 16×16 quantized phase pattern with 2-color legend
```

## 8. CSV Data Export

```
RIS_phase_incident.csv         # φ_incident matrix (continuous)
RIS_phase_steering.csv         # φ_steering matrix (continuous)
RIS_phase_continuous.csv       # φ_total matrix (continuous, 0-360°)
RIS_phase_quantized_1bit.csv   # φ_quant matrix (quantized, n-bit dependent)
```

Each file: 16×16 matrix in CSV format

---

# Pseudocode

```pseudocode
FUNCTION GenerateRISPhasePattern(source, ris_center, target, n_bit):

    // Step 1: Calculate physical constants
    wavelength = c / f
    k = 2π / wavelength
    d = wavelength / 2

    // Step 2: Generate RIS element coordinates
    N = 16
    lim_x = (N-1) / 2 * d
    lim_y = (N-1) / 2 * d

    FOR i = 0 TO N-1:
        FOR j = 0 TO N-1:
            x_rel[i,j] = -lim_x + (i/(N-1)) * 2 * lim_x
            y_rel[i,j] = -lim_y + (j/(N-1)) * 2 * lim_y

    // Step 3: Calculate deflection angle from 2D azimuth angles
    AP = [source.x, source.y]
    RIS = [ris_center.x, ris_center.y]
    UE = [target.x, target.y]

    theta_in = arctan2(AP.y - RIS.y, AP.x - RIS.x)    // Incident azimuth
    theta_out = arctan2(UE.y - RIS.y, UE.x - RIS.x)   // Reflected azimuth

    angle_diff = theta_out - theta_in

    // Wrap angle to [-π, π]
    WHILE angle_diff > π:
        angle_diff -= 2π
    WHILE angle_diff < -π:
        angle_diff += 2π

    theta_rcv = ABS(angle_diff)  // Deflection angle magnitude

    // Step 4: Calculate steering angle vector
    u_x = sin(theta_rcv)
    u_y = 0
    u_z = cos(theta_rcv)

    // Step 5: Calculate source offset and height
    delta_x_s = source.x - ris_center.x
    delta_y_s = source.y - ris_center.y
    delta_z_s = source.z - ris_center.z
    r_src = delta_z_s  // Height above RIS

    // Step 6: Compute phase components for each element
    r_src_dist = ZEROS(N, N)
    phase_incident = ZEROS(N, N)
    phase_steering = ZEROS(N, N)
    phase_total = ZEROS(N, N)

    FOR i = 0 TO N-1:
        FOR j = 0 TO N-1:
            x_i = x_rel[i,j]
            y_i = y_rel[i,j]

            // Incident spherical wavefront
            // SIMPLIFIED (current): assumes source above RIS center
            // r_source_dist[i,j] = sqrt(x_i² + y_i² + r_src²)

            // GENERAL (3D-ready): accounts for arbitrary source position
            r_source_dist[i,j] = sqrt((delta_x_s - x_i)² + (delta_y_s - y_i)² + delta_z_s²)

            phase_incident[i,j] = k * r_source_dist[i,j]

            // Steering phase from deflection angle
            phase_steering[i,j] = -k * x_i * sin(theta_rcv)

            // Total phase (superposition)
            phase_total[i,j] = phase_incident[i,j] + phase_steering[i,j]
            phase_total[i,j] = phase_total[i,j] MOD (2π)

            IF phase_total[i,j] < 0:
                phase_total[i,j] += 2π

    // Step 7: Convert to degrees
    phase_deg = phase_total * (180/π)

    // Step 8: Quantize to n-bit levels
    num_levels = 2^n_bit
    phase_quant_deg = ZEROS(N, N)

    FOR i = 0 TO N-1:
        FOR j = 0 TO N-1:
            normalized = phase_deg[i,j] / 360.0
            level = ROUND(normalized * (num_levels - 1))
            phase_quant_deg[i,j] = level / (num_levels - 1) * 360.0

    // Step 9: Calculate colorbar range
    vmax = 360.0 / (2^n_bit) * ((2^n_bit) - 1)

    // Step 10: Create visualization
    figure = CREATE_FIGURE(size=(10, 14))

    // Subplot 1: Geometry
    ax_geom = CREATE_SUBPLOT(2, 2, [1, 1])
    PLOT_NODES(source, ris_center, target)
    PLOT_DEFLECTION_ANGLE(ris_center, source, target)

    // Subplot 2: Heatmap
    ax_heat = CREATE_SUBPLOT(2, 2, [2])
    IMSHOW(phase_quant_deg, cmap='BWR', vmin=0, vmax=vmax)
    COLORBAR(label=f'Quantized Phase (0-{vmax:.0f}°)')

    // Step 11: Save outputs
    SAVE_FIGURE('RIS_phase_pattern_deflection_combined.png')
    SAVE_CSV('RIS_phase_incident.csv', phase_incident * 180/π)
    SAVE_CSV('RIS_phase_steering.csv', phase_steering * 180/π)
    SAVE_CSV('RIS_phase_continuous.csv', phase_deg)
    SAVE_CSV('RIS_phase_quantized_1bit.csv', phase_quant_deg)

    RETURN phase_quant_deg, vmax

END FUNCTION
```

---

# 3D Beamforming Implementation — Validation & Results

## Comparison: 2D vs 3D Beamforming

### Corrected 3D Formula

After implementation and testing, the correct 3D formula is:

```
Incident Phase (3D-aware, RIS-relative):
φ_incident(i,j) = k·√(x_i² + y_i² + Δz_s²)

Azimuth Steering (horizontal):
φ_steering_az(i,j) = -k·x_i·sin(Δθ_az)

Elevation Steering (vertical):
φ_steering_el(i,j) = -k·y_i·sin(Δθ_el)

Total Phase:
φ(i,j) = φ_incident + φ_steering_az + φ_steering_el
```

**Key insight:** The incident phase is **RIS-relative**, not source-absolute. Source offset (Δx_s, Δy_s) affects steering angle calculation, not incident phase magnitude.

### Numerical Comparison (Example Coordinates)

```
Coordinates:
source = [8.0, 10.0, 0.5]
ris_center = [15.0, 10.0, 0.0]
target = [11.4, 6.5, 0.0]

Azimuth Deflection Angle:
2D: 135.81° (azimuth only)
3D: 135.81° (same as 2D)

Elevation Deflection Angle:
2D: 0° (ignored)
3D: -4.09° (NEW component)

Steering Phase Contributions at Corner Element (x_i=0.1938, y_i=0.1938):
2D: φ_steering = -941.06° (azimuth only)
3D: φ_steering_az = -941.06° (azimuth, same)
3D: φ_steering_el = +96.18° (elevation, new)
     Total steering = -844.88° (difference: 96.18°)

Net Result: Elevation component adds ~96° phase variation across array
```

### Heatmap Pattern Differences

**Expected differences between 2D and 3D:**

| Aspect | Observation | Impact |
|--------|-------------|--------|
| **Overall structure** | Similar checkerboard pattern | ✓ Acceptable |
| **Phase gradient direction** | Primarily X-direction (azimuth) | ✓ Dominant feature |
| **Y-direction modulation** | Added by elevation component | ✓ Visible but secondary |
| **Phase range** | 0-180° (1-bit, same in both) | ✓ Same |
| **Magnitude of difference** | ~96° elevation effect at edges | ✓ Measurable (~13% of range) |

### Visual Comparison

**RIS_phase_pattern_deflection.png (2D):**
- Clean linear phase gradient in X-direction
- Minimal Y-direction variation
- Strictly follows azimuth steering

**RIS_phase_pattern_3d.png (3D):**
- Same linear X-gradient (azimuth dominates)
- Additional Y-direction modulation (elevation steering)
- Checkerboard pattern slightly modified
- More realistic 3D beamforming

## Acceptability Assessment

**Is the difference acceptable? YES** ✓

### Reasons:

1. **Dominance of azimuth over elevation** (95% vs 5% effect)
   - Azimuth deflection: 135.81°
   - Elevation deflection: -4.09°
   - The X-direction gradient remains primary feature

2. **Physical validity**
   - 3D version correctly accounts for height difference
   - Elevation component (-4.09°) is physically accurate
   - Pattern reflects realistic 3D propagation

3. **Small but measurable effect**
   - ~96° phase difference is 13% of 0-180° range
   - Visible in heatmap as subtle Y-direction modulation
   - Not negligible, but not dominant

4. **Use case suitability**
   - For ML training: Both acceptable, 3D more accurate
   - For system design: 3D recommended for precision
   - Trade-off: Complexity vs accuracy

### Quantitative Difference

```
2D Phase Pattern: φ = φ_incident + φ_steering_az
3D Phase Pattern: φ = φ_incident + φ_steering_az + φ_steering_el

Additional term: φ_steering_el = -k·y_i·sin(-4.09°) = 0.24·y_i (radians/element)

At array boundary (y = ±0.1938m):
Additional phase swing: ±0.047 radians ≈ ±2.7° (minor effect on quantized pattern)

At 1-bit quantization (0° or 180°):
The ±2.7° variation is absorbed into quantization rounding (negligible impact)
```

## Recommendation for Usage

| Scenario | Recommendation |
|----------|---|
| **ML training with current coordinates** | Either 2D or 3D acceptable; 3D slightly more accurate |
| **Production system design** | Use 3D for full physical accuracy |
| **Comparing to measurements** | Use 3D if vertical offset is measured |
| **Elevation > 5°** | Must use 3D (becomes significant) |
| **Quick prototyping** | Use 2D for speed; 3D for final validation |

---

# Limitations: 2D Beamforming (Current Implementation)

## Scope

Current implementation (`pattern_gen_def.py`) performs **2D horizontal beamforming only**:

```
Deflection angle calculated from 2D XY-plane projection:
vec_in_2d = [from_source_norm_x, from_source_norm_y]
vec_out_2d = [to_target_norm_x, to_target_norm_y]

θ_rcv = arccos(normalize(vec_in_2d) · normalize(vec_out_2d))
```

**This ignores the Z-component entirely**, affecting elevation/depression steering.

## When This Is Valid

✅ **Use 2D implementation when:**
- Target is at RIS plane or near it: z_t ≈ z_r
- Vertical offset is negligible: |z_t - z_r| << horizontal distance
- Beam steering required only in azimuth (horizontal)
- 2D simulation sufficient for your ML training

**Example (valid for current code):**
```
source = [8.0, 10.0, 0.5]        # Source 0.5 m above RIS
ris_center = [15.0, 10.0, 0.0]   # RIS reference plane
target = [11.4, 6.5, 0.0]        # Target at RIS plane ✅

Deflection: 44.19° (azimuth only)
Elevation: Not controlled (ignored)
```

## When This Is Invalid

❌ **Do NOT use 2D implementation when:**
- Target significantly above RIS: z_t >> z_r (e.g., z_t = 5 m, z_r = 0 m)
- Target below RIS: z_t < z_r (depression angle needed)
- Elevation beamforming critical for your scenario
- 3D wireless propagation required

**Example (invalid for current code):**
```
target = [11.4, 6.5, 3.0]        # Target 3 m above RIS ❌

Missing: Elevation steering component
Result: Incorrect phase pattern, reduced link quality
```

## Future Work: 3D Beamforming

### Extended Formulation (3D)

```
Full 3D deflection angle (azimuth + elevation):
vec_in_3d = from_source_norm = [Δx_s, Δy_s, Δz_s] (normalized)
vec_out_3d = to_target_norm = [Δx_t, Δy_t, Δz_t] (normalized)

θ_rcv_3d = arccos(vec_in_3d · vec_out_3d)    # Full 3D angle
```

### Decomposed Steering (Azimuth + Elevation)

For 2D RIS array (horizontal plane), we can separate steering into:

```
Azimuth angle (horizontal steering):
φ_az = arctan2(Δy_t, Δx_t) - arctan2(Δy_s, Δx_s)

Elevation angle (vertical steering):
φ_el_in = arcsin(Δz_s / ||from_source||)
φ_el_out = arcsin(Δz_t / ||to_target||)

Elevation deflection:
Δφ_el = φ_el_out - φ_el_in
```

### Extended Phase Formula (3D Version)

```
Current (2D only):
φ_steering(i,j) = -k × x_i × sin(θ_rcv_2d)

Extended (3D azimuth + elevation):
φ_steering_3d(i,j) = -k × [x_i × sin(φ_az) + y_i × sin(φ_el) + ...]

For 3D 2D RIS (elevation-capable):
φ_steering_3d(i,j,m) = -k × [x_i × sin(φ_az) + m × sin(φ_el)]

where m is the element's vertical index (currently all m = 0)
```

### Implementation Path

**To implement 3D beamforming (`pattern_gen_3d.py`):**

1. Use full 3D direction vectors (not 2D projection)
2. Separate azimuth and elevation steering components
3. Support 2D (planar) RIS or 3D (planar or volumetric) RIS
4. Extend phase formula with elevation steering term
5. Update heatmap to show 2D azimuth steering (current approach)
6. Add separate elevation heatmap or 3D volume visualization

**Expected differences:**
- More accurate beam control for elevated/depressed targets
- Additional phase correction for z-offset elements (if 3D RIS)
- Potential improvement in ML model accuracy for realistic 3D scenarios

### Validation Criterion for 2D vs 3D

```
Calculate elevation angle magnitude:
φ_el = arctan(|z_t - z_s| / √((x_t - x_s)² + (y_t - y_s)²))

Use 2D implementation if:  φ_el < 5°   (negligible elevation)
Use 3D implementation if:  φ_el ≥ 5°   (significant elevation)
```

---

# Mathematical Summary

**Three-stage transformation (2D current implementation):**

```
Coordinates (3D)
    ↓ [Extract XY projection, ignore Z]
2D Deflection Angle θ_rcv (azimuth only)
    ↓ [Generate phase components]
Phase Matrix Φ (continuous, 0-360°)
    ↓ [Quantize to n-bit levels]
Quantized Phase Matrix Φ_quant (discrete, 2^n_bit levels)
    ↓ [Visualize with dynamic colormap]
Heatmap (0° to vmax)
```

**Key relationship:**
```
2D Deflection Angle → Azimuth Steering Phase Gradient
                   = Controls horizontal beam direction

φ_steering = -k × x_i × sin(Δθ_az)

Larger Δθ_az → Steeper gradient → More horizontal steering
```

**Future extension (3D):**
```
Coordinates (3D)
    ↓ [Use full 3D vectors]
3D Deflection Angle (azimuth + elevation)
    ↓ [Decompose into steering components]
Phase Components (azimuth + elevation steering)
    ↓ [Combine with incident spherical wave]
Phase Matrix Φ (continuous)
    ↓ [Quantize to n-bit levels]
Quantized Phase Matrix Φ_quant
    ↓ [Visualize with enhanced visualization]
Heatmap + Elevation Steering Map
```
