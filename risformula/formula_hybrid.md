
# Reconfigurable Intelligent Surface (RIS) Phase Pattern Generation  
## Hybrid Model: Beam Steering (Far-field) + Point Focusing (Near-field)

This document provides the mathematical formulation for generating the RIS phase pattern
based on 3D coordinates of the transmitter (AP), RIS, and receiver (UE).  
It supports two RIS modes:

1. **Beam-Steering Mode (Far-field)**  
2. **Point-Focusing Mode (Near-field)**  

Both modes share the same spherical incident phase, but differ in the reflection component.

---

## 1. Input Coordinates
```
source = [x_s, y_s, z_s]      # AP position
ris_center = [x_r, y_r, z_r]  # RIS center position
target = [x_t, y_t, z_t]      # UE position
mode = "steer" or "focus"     # RIS operating mode
```

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

## 4. Spherical Incident Phase (AP → RIS)
Let:
\[
\Delta x_s = x_s - x_r,\quad
\Delta y_s = y_s - y_r,\quad
\Delta z_s = z_s - z_r
\]

Distance from AP to RIS element:
\[
r_{	ext{src}}(i,j)
= \sqrt{(\Delta x_s - x_i)^2 + (\Delta y_s - y_i)^2 + (\Delta z_s)^2}
\]

Incident phase:
\[
\phi_{	ext{incident}}(i,j) = k \cdot r_{	ext{src}}(i,j)
\]

---

## 5. Reflection Component

### 5A. Beam-Steering Mode (Far-field)
Compute outgoing direction vector:
\[
\mathbf{v}_{	ext{out}} = [x_t - x_r,\; y_t - y_r,\; z_t - z_r]
\]
Normalized:
\[
\hat{\mathbf{v}} = rac{\mathbf{v}}{\|\mathbf{v}\|}
\]

Azimuth:
\[
	heta_{	ext{az}} = rctan2(v_y, v_x)
\]

Elevation:
\[
	heta_{	ext{el}} = rcsin\left(rac{v_z}{\|\mathbf{v}\|}ight)
\]

Steering phase:
\[
\phi_{	ext{steer}}(i,j)
= -k\,(x_i \sin	heta_{	ext{az}} + y_j \sin	heta_{	ext{el}})
\]

---

### 5B. Point-Focusing Mode (Near-field)
Distance from RIS element to UE:
\[
r_{	ext{rcv}}(i,j)
= \sqrt{(x_t - x_i)^2 + (y_t - y_i)^2 + (z_t - z_i)^2}
\]

Focusing phase:
\[
\phi_{	ext{focus}}(i,j)
= k \cdot r_{	ext{rcv}}(i,j)
\]

---

## 6. Total Phase

### If mode = "steer"
\[
\phi(i,j)
= \phi_{	ext{incident}}(i,j)
+ \phi_{	ext{steer}}(i,j)
\]

### If mode = "focus"
\[
\phi(i,j)
= \phi_{	ext{incident}}(i,j)
+ \phi_{	ext{focus}}(i,j)
\]

---

## 7. Phase Normalization
\[
\phi(i,j) = \phi(i,j) mod 2\pi
\]
If negative:
\[
\phi := \phi + 2\pi
\]

---

## 8. Quantization
Let:
\[
L = 2^{n_	ext{bit}}
\]

Quantized phase:
\[
\phi_q(i,j)
= 360^\circ \cdot
rac{\mathrm{round}\left(rac{\phi(i,j)}{360^\circ}(L-1)ight)}
{(L-1)}
\]

---

## 9. Output Matrices
```
φ_incident[i,j]
φ_steer[i,j]      # used if mode="steer"
φ_focus[i,j]      # used if mode="focus"
φ_total[i,j]
φ_quantized[i,j]
```

---

## 10. Heatmap Visualization
Quantized matrix is displayed using:
```
imshow(φ_quantized)
colorbar()
```

---

## 11. Automatic Mode Selection (Optional)
Fraunhofer boundary:
\[
r_{	ext{boundary}} = rac{2D^2}{\lambda}
\]

If:
- UE distance > boundary → use **steer mode**
- UE distance ≤ boundary → use **focus mode**

---

## 12. Summary

| Mode | Formula | Use Case |
|------|---------|----------|
| Steering | φ = φ_incident + φ_steer | Far-field communications |
| Focusing | φ = φ_incident + φ_focus | Near-field, localization, radar |

This unified formulation allows the RIS to operate either as a classical beam-steering array or as a near-field lens, depending on system requirements.
