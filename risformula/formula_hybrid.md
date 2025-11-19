
# Reconfigurable Intelligent Surface (RIS) Phase Pattern Generation
## Hybrid Model: Beam Steering (Far-field) + Point Focusing (Near-field)

This document provides the mathematical formulation for generating the RIS phase pattern
based on 3D coordinates of the transmitter (AP), RIS, and receiver (UE).
It supports two RIS modes:

1. **Beam-Steering Mode (Far-field)**
2. **Point-Focusing Mode (Near-field)**

Both modes can use either spherical or plane waves for TX/RX components.

---

## 1. Input Coordinates and Configuration

### Core Coordinates
```
source = [x_s, y_s, z_s]      # AP position
ris_center = [x_r, y_r, z_r]  # RIS center position
target = [x_t, y_t, z_t]      # UE position
```

### Configuration Approach A: Mode-based (pattern_gen_hybrid.py)
```
mode = "steer" or "focus" or "auto"    # RIS operating mode
plane_tx = True/False                   # Use plane wave for TX
```
- `mode='focus'` → spherical RX (near-field, point-focusing)
- `mode='steer'` → plane RX (far-field, beam-steering)
- `mode='auto'` → automatic selection via Fraunhofer boundary

### Configuration Approach B: Flag-based (pattern_hybrid_sap.txt)
```
plane_tx = True/False         # Use plane wave for TX
plane_rx = True/False         # Use plane wave for RX
```
- Independent control of TX and RX wave types
- No automatic mode selection

---

## 2. Physical Constants
```
c = 299,792,458               # Speed of light
f = carrier frequency         # e.g., 5.8e9 Hz
λ = c / f                     # Wavelength
k = 2π / λ                    # Wavenumber
d = λ / 2                     # RIS element spacing
```

---

## 3. RIS Array Geometry
A uniform planar array (UPA), 16×16 elements centered at (0,0):

```
N = 16
lim_x = (N-1)/2 * d
lim_y = (N-1)/2 * d
```

Element coordinates:
```
x_i ∈ [−lim_x, +lim_x]
y_j ∈ [−lim_y, +lim_y]
z_ij = 0
```

---

## 4. Transmitter (AP) to RIS Phase Component

Let:
\[
\Delta x_s = x_s - x_r,\quad
\Delta y_s = y_s - y_r,\quad
\Delta z_s = z_s - z_r
\]

### 4A. Spherical Wave (Near-field, default)
Distance from AP to RIS element:
\[
r_{{\text{src}}}(i,j)
= \sqrt{(\Delta x_s - x_i)^2 + (\Delta y_s - y_i)^2 + (\Delta z_s)^2}
\]

TX phase (spherical):
\[
\phi_{{\text{tx,sph}}}(i,j) = k \cdot r_{{\text{src}}}(i,j)
\]

**Use case:** Near-field transmitter, accurate spherical wavefront compensation.

### 4B. Plane Wave (Far-field approximation)
Incident direction vector (normalized):
\[
\mathbf{u}_s = \frac{[\Delta x_s,\; \Delta y_s,\; \Delta z_s]}{\sqrt{\Delta x_s^2 + \Delta y_s^2 + \Delta z_s^2}}
\]

TX phase (plane wave):
\[
\phi_{{\text{tx,plane}}}(i,j) = -k \cdot (\mathbf{u}_s \cdot [x_i,\; y_i,\; 0])
= -k \cdot (x_i u_{s,x} + y_i u_{s,y})
\]

**Use case:** Far-field transmitter, linear phase gradient approximation.

**Selection Rule:**
- Use spherical (4A) for near-field TX or accurate wavefront modeling
- Use plane wave (4B) for far-field TX or simplified beamforming

---

## 5. Receiver (UE) from RIS Phase Component

### 5A. Spherical Wave (Near-field, Point-Focusing Mode)
Distance from RIS element to UE:
\[
r_{{\text{rcv}}}(i,j)
= \sqrt{(x_t - x_i)^2 + (y_t - y_i)^2 + (z_t - z_i)^2}
\]

RX phase (spherical, focusing):
\[
\phi_{{\text{rx,focus}}}(i,j)
= k \cdot r_{{\text{rcv}}}(i,j)
\]

**Use case:** Near-field operations, point-focusing, localization, radar imaging.

### 5B. Plane Wave (Far-field, Beam-Steering Mode)
Outgoing direction vector:
\[
\mathbf{v}_{{\text{out}}} = [x_t - x_r,\; y_t - y_r,\; z_t - z_r]
\]

Normalized:
\[
\hat{\mathbf{v}} = \frac{\mathbf{v}}{\|\mathbf{v}\|}
\]

Azimuth angle:
\[
\theta_{{\text{az}}} = \arctan2(v_y, v_x)
\]

Elevation angle:
\[
\theta_{{\text{el}}} = \arcsin\left(\frac{v_z}{\|\mathbf{v}\|}\right)
\]

RX phase (plane wave, steering):
\[
\phi_{{\text{rx,steer}}}(i,j)
= -k\,(x_i \sin\theta_{{\text{az}}} + y_j \sin\theta_{{\text{el}}})
\]

**Use case:** Far-field communications, beam steering, wide-area coverage.

**Selection Rule:**
- Use spherical (5A) for near-field RX or localization applications
- Use plane wave (5B) for far-field RX or classical beamforming

---

## 6. Total Phase Combination

### If mode = "steer" (far-field, plane wave RX)
\[
\phi(i,j)
= \phi_{{\text{tx}}}(i,j)
+ \phi_{{\text{rx,steer}}}(i,j)
\]

where φ_tx is selected from 4A (spherical) or 4B (plane wave).

### If mode = "focus" (near-field, spherical wave RX)
\[
\phi(i,j)
= \phi_{{\text{tx}}}(i,j)
+ \phi_{{\text{rx,focus}}}(i,j)
\]

where φ_tx is selected from 4A (spherical) or 4B (plane wave).

### Recommended Combinations
| TX | RX | Mode | Use Case |
|----|----|------|----------|
| Spherical | Spherical | focus | Full near-field |
| Spherical | Plane | steer | Near-field TX, far-field RX |
| Plane | Spherical | focus | Far-field TX, near-field RX |
| Plane | Plane | steer | Full far-field (classical) |

---

## 7. Phase Normalization
\[
\phi(i,j) = \phi(i,j) \bmod 2\pi
\]
If negative:
\[
\phi := \phi + 2\pi
\]

---

## 8. Quantization
Let:
\[
L = 2^{n_{\text{bit}}}
\]

Quantized phase:
\[
\phi_q(i,j)
= 360^\circ \cdot
\frac{\mathrm{round}\left(\frac{\phi(i,j)}{360^\circ}(L-1)\right)}{(L-1)}
\]

---

## 9. Output Matrices
```
φ_tx[i,j]          # TX phase component (spherical or plane)
φ_rx[i,j]          # RX phase component (focusing or steering)
φ_total[i,j]       # Combined phase (continuous)
φ_quantized[i,j]   # Quantized phase (n_bit levels)
```

---

## 10. Heatmap Visualization
Quantized matrix is displayed using:
```
imshow(φ_quantized)
colorbar()
```
Colorbar auto-scales to the range of quantized values.

---

## 11. Automatic Mode Selection (Optional)
Fraunhofer boundary:
\[
r_{{\text{boundary}}} = \frac{2D^2}{\lambda}
\]

where D = (N-1)·d is the array aperture.

If:
- UE distance > boundary → use **steer mode** (plane wave RX)
- UE distance ≤ boundary → use **focus mode** (spherical RX)

---

## 12. Summary

| Aspect | Spherical TX | Plane TX |
|--------|---|---|
| **Use case** | Near-field, spherical wavefront | Far-field, plane wave approx |
| **Formula** | k·√((Δx_s - x_i)² + (Δy_s - y_i)² + Δz_s²) | -k·(x_i·u_s,x + y_i·u_s,y) |
| **Computational cost** | Higher (per-element distance) | Lower (linear phase) |
| **Accuracy** | Exact for arbitrary distances | Approximate for far-field |

| Aspect | Spherical RX (Focus) | Plane RX (Steer) |
|--------|---|---|
| **Use case** | Near-field, localization, radar | Far-field, beam steering |
| **Formula** | k·√((x_t - x_i)² + (y_t - y_i)² + (z_t - z_i)²) | -k·(x_i·sin(θ_az) + y_i·sin(θ_el)) |
| **Physics** | Point-focusing lens | Directional steering |
| **Array control** | Focuses energy to a point | Steers beam in a direction |

This unified formulation allows the RIS to operate in multiple modes:
- Pure near-field (spherical TX + RX): Full 3D wavefront control
- Pure far-field (plane TX + RX): Classical phased array steering
- Hybrid modes: Flexible TX/RX combinations for mixed scenarios

---

## 13. Implementation Approaches

### Approach A: Mode-based Control (pattern_gen_hybrid.py)
Uses high-level `mode` parameter with intelligent automatic selection.

**Advantages:**
- Simple API: single `mode` parameter for RX selection
- Automatic mode selection via Fraunhofer boundary
- Cleaner for users (fewer parameters)
- Explicit hybrid near-field/far-field switching

**Parameters:**
```
plane_tx = False/True    # TX wave type
mode = 'auto'/'steer'/'focus'    # RX mode with auto-selection
```

**Implementation:**
- TX: `incident_phase(plane_tx=...)`
- RX: `steering_phase()` (plane) OR `focusing_phase()` (spherical)

### Approach B: Flag-based Control (pattern_hybrid_sap.txt)
Uses independent boolean flags for each component.

**Advantages:**
- Full flexibility: all 4 TX/RX combinations available
- No hidden automatic selection
- Transparent control flow
- Supports advanced features (OAM)

**Parameters:**
```
plane_tx = False/True    # TX wave type
plane_rx = False/True    # RX wave type
```

**Implementation:**
- TX: `if plane_tx: ... else: ...`
- RX: `if plane_rx: ... else: ...`

### Recommendation

| Use Case | Approach | Why |
|----------|----------|-----|
| **Standard beamforming** | A (mode-based) | Simpler, automatic selection |
| **Research/development** | B (flag-based) | Full control, all combinations |
| **Automatic far/near-field** | A (mode-based) | Fraunhofer boundary built-in |
| **OAM modulation** | B (flag-based) | Only approach supporting OAM |
| **Production system** | A (mode-based) | User-friendly, fewer parameters |

Both approaches are mathematically equivalent and produce correct results. Choose based on use case and preference.
