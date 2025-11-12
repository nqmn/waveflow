import numpy as np
import matplotlib.pyplot as plt

# ===========================================================
# 5.8 GHz 1-Bit RIS Phase Pattern — Coordinate-Driven Version
# (from actual 3D node positions: AP, RIS, UE)
# Aligned with ris_simulator_6.html phase calculation
# ===========================================================

# --- Physical constants
c = 299_792_458.0
f = 5.8e9
wavelength = c / f
k = 2 * np.pi / wavelength
d = 0.5 * wavelength   # half-wavelength element spacing (≈25.9 mm) to match HTML

# --- RIS geometry
N = 16                               # 16×16 array (can change)
X, Y = np.meshgrid(np.arange(N), np.arange(N))

# ===========================================================
# Define 3D coordinates of the nodes (meters)
# ===========================================================
# Example setup: AP→RIS = 7 m along x-axis; RIS→UE arbitrary in 3D
source = np.array([8.0, 10.0, 0.45])    # Source position (height 0.45 m above RIS)
ris_center = np.array([15.0, 10.0, 0.0])  # RIS center (reference)
target = np.array([11.4, 6.5, 0.0])       # Target position (UE)

# Source height above RIS plane (for spherical wave model)
r_src = 0.45

# ===========================================================
# Compute per-element coordinates using linspace normalization
# (matching HTML's coordinate generation)
# ===========================================================
lim_x = (N - 1) / 2 * d
lim_y = (N - 1) / 2 * d

# Create coordinate grid using linspace-style normalization
X_idx = np.arange(N)
Y_idx = np.arange(N)
X_grid, Y_grid = np.meshgrid(X_idx, Y_idx)

# Compute relative element positions (normalized)
x_rel = -lim_x + (X_grid / (N - 1)) * (2 * lim_x)
y_rel = -lim_y + (Y_grid / (N - 1)) * (2 * lim_y)
z_rel = np.zeros_like(x_rel)

# ===========================================================
# Compute phase compensation (spherical wave model from HTML)
# Matches ris_simulator_6.html calculatePhaseMap function
# ===========================================================

# Calculate direction vectors
to_target = target - ris_center
to_target_norm = to_target / np.linalg.norm(to_target)

# For spherical wave: steering angle (theta_rcv) calculated from deflection angle
from_source = ris_center - source
from_source_norm = from_source / np.linalg.norm(from_source)

# Calculate deflection angle (in 2D XY plane)
vec_in_2d = from_source_norm[:2]
vec_out_2d = to_target_norm[:2]
len_in = np.linalg.norm(vec_in_2d)
len_out = np.linalg.norm(vec_out_2d)

if len_in > 1e-6 and len_out > 1e-6:
    norm_in_2d = vec_in_2d / len_in
    norm_out_2d = vec_out_2d / len_out
    dot_product = np.clip(np.dot(norm_in_2d, norm_out_2d), -1, 1)
    theta_rcv_rad = np.arccos(dot_product)
else:
    theta_rcv_rad = np.pi / 2

# Convert steering angle to unit direction vector u
u_x = np.sin(theta_rcv_rad)  # u = sph2cart(1, theta, 0)
u_y = 0
u_z = np.cos(theta_rcv_rad)

# Compute phase for each element
phase_rad = np.zeros_like(x_rel)

for i in range(N):
    for j in range(N):
        # Element position relative to RIS center
        x_i = x_rel[i, j]
        y_i = y_rel[i, j]

        # Spherical wave: distance from source to element
        r_source_dist = np.sqrt(x_i**2 + y_i**2 + r_src**2)

        # Dot product with steering direction
        dot_prod = x_i * u_x + y_i * u_y + 0 * u_z

        # Phase calculation (spherical wave model)
        phase_rad[i, j] = (k * r_source_dist - k * dot_prod) % (2 * np.pi)

# Ensure phase is in [0, 2π] range
phase_rad = np.where(phase_rad < 0, phase_rad + 2 * np.pi, phase_rad)

# ===========================================================
# 1-bit quantization: map to 0° or 180° (2-level quantization)
# ===========================================================
phase_deg = np.degrees(phase_rad)
phase_quant_deg = np.where(phase_deg < 180, 0, 180)

# ===========================================================
# Display geometry summary
# ===========================================================
def angle_between(v1, v2):
    v1n, v2n = v1 / np.linalg.norm(v1), v2 / np.linalg.norm(v2)
    return np.degrees(np.arccos(np.clip(np.dot(v1n, v2n), -1, 1)))

vec_in  = source - ris_center
vec_out = target - ris_center
theta_inc = angle_between(vec_in, [1, 0, 0])
theta_ref = angle_between(vec_out, [1, 0, 0])
print(f"Source→RIS distance: {np.linalg.norm(vec_in):.2f} m")
print(f"RIS→Target distance: {np.linalg.norm(vec_out):.2f} m")
print(f"Incident angle:  {theta_inc:.2f}°   Reflected angle: {theta_ref:.2f}°")
print(f"Steering angle (theta_rcv): {np.degrees(theta_rcv_rad):.2f}°")
print(f"Element spacing: {d*1000:.1f} mm (half-wavelength)")

# ===========================================================
# Plot heatmap
# ===========================================================
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

# Plot 1: Continuous phase
im1 = axes[0].imshow(phase_deg, cmap='hsv', origin='lower', vmin=0, vmax=360)
axes[0].set_title('RIS Phase (Continuous, 0-360°)')
axes[0].set_xlabel('Element index (x)')
axes[0].set_ylabel('Element index (y)')
plt.colorbar(im1, ax=axes[0], label='Phase (°)')

# Plot 2: Quantized phase (1-bit)
im2 = axes[1].imshow(phase_quant_deg, cmap='bwr', origin='lower', vmin=0, vmax=180)
axes[1].set_title('RIS 1-Bit Quantized Phase Map (5.8 GHz)')
axes[1].set_xlabel('Element index (x)')
axes[1].set_ylabel('Element index (y)')
plt.colorbar(im2, ax=axes[1], label='Quantized Phase (°)')

plt.tight_layout()
plt.savefig('RIS_phase_pattern.png', dpi=150, bbox_inches='tight')
plt.show()

# Save numerical phase matrices
np.savetxt('RIS_phase_continuous.csv', phase_deg, fmt='%.1f', delimiter=',')
np.savetxt('RIS_phase_quantized_1bit.csv', phase_quant_deg, fmt='%.0f', delimiter=',')
