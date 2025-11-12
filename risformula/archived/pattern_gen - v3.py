import numpy as np
import matplotlib.pyplot as plt
import math

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
source = np.array([8.0, 10.0, 0.5])    # Source position (height 0.45 m above RIS)
ris_center = np.array([15.0, 10.0, 0.0])  # RIS center (reference)
target = np.array([11.4, 6.5, 0.0])       # Target position (UE)

# Source height above RIS plane (for spherical wave model)
# r_src = 0.45  # hardcoded - now derived from source z-coordinate
r_src = source[2] - ris_center[2]

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

# ===========================================================
# Wave mode selection
# ===========================================================
wave_mode = 'spherical'  # 'spherical' or 'plane' (default: spherical)

# Compute phase for each element
phase_rad = np.zeros_like(x_rel)

for i in range(N):
    for j in range(N):
        # Element position relative to RIS center
        x_i = x_rel[i, j]
        y_i = y_rel[i, j]

        # Dot product with steering direction
        dot_prod = x_i * u_x + y_i * u_y + 0 * u_z

        if wave_mode == 'spherical':
            # Spherical wave: distance from source to element
            r_source_dist = np.sqrt(x_i**2 + y_i**2 + r_src**2)
            phase_rad[i, j] = (k * r_source_dist - k * dot_prod) % (2 * np.pi)
        elif wave_mode == 'plane':
            # Plane wave: only uses direction (no distance term)
            phase_rad[i, j] = (k * dot_prod) % (2 * np.pi)
        else:
            raise ValueError(f"Invalid wave_mode: {wave_mode}. Use 'spherical' or 'plane'.")

# Ensure phase is in [0, 2π] range
phase_rad = np.where(phase_rad < 0, phase_rad + 2 * np.pi, phase_rad)

# ===========================================================
# N-bit quantization: quantize phase to discrete levels
# ===========================================================
n_bit = 1  # Number of bits (default: 1-bit, alternatives: 2, 3, 4, ...)
num_levels = 2 ** n_bit
phase_deg = np.degrees(phase_rad)

# Quantize phase to n-bit levels
phase_quant_deg = np.round((phase_deg / 360.0) * (num_levels - 1)) / (num_levels - 1) * 360.0

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
# Plot heatmap and geometry
# ===========================================================
fig = plt.figure(figsize=(10, 14))
# Use a two-column grid so the heatmap keeps full width while the colorbar sits in its own column.
gs = fig.add_gridspec(
    2,
    2,
    height_ratios=[1.5, 1],
    width_ratios=[30, 1.2],
    hspace=0.35,
    wspace=0.08,
    left=0.08,
    right=0.95,
    top=0.95,
    bottom=0.08,
)

# Plot 1: Geometry (Top-down view) - full width top
ax1 = fig.add_subplot(gs[0, :])

# Extract 2D positions from 3D coordinates
AP = source[:2]
RIS = ris_center[:2]
UE = target[:2]

# Calculate angles for geometry visualization
phi_AP = np.degrees(np.arctan2(AP[1] - RIS[1], AP[0] - RIS[0]))
phi_UE = np.degrees(np.arctan2(UE[1] - RIS[1], UE[0] - RIS[0]))

# Calculate deflection angle
angle_diff = phi_UE - phi_AP
if angle_diff > 180:
    angle_diff -= 360
elif angle_diff < -180:
    angle_diff += 360

abs_diff = abs(angle_diff)
signed_diff = angle_diff
bisector = phi_AP + signed_diff / 2
FoV_full = 60  # Full field of view (degrees)

# Scatter plot for nodes
ax1.scatter(AP[0], AP[1], s=120, color='green', marker='s', label='Source (AP)', zorder=5)
ax1.scatter(RIS[0], RIS[1], s=160, color='orange', marker='^', label='RIS', zorder=5)
ax1.scatter(UE[0], UE[1], s=120, color='red', marker='o', label='Target (UE)', zorder=5)

# Lines from RIS to other nodes
ax1.plot([RIS[0], AP[0]], [RIS[1], AP[1]], 'g--', lw=2, label=f'RIS→AP ({phi_AP:.1f}°)', alpha=0.7)
ax1.plot([RIS[0], UE[0]], [RIS[1], UE[1]], 'r--', lw=2, label=f'RIS→UE ({phi_UE:.1f}°)', alpha=0.7)

# Field of View cone (optional)
theta_fill = np.linspace(math.radians(bisector - FoV_full/2),
                         math.radians(bisector + FoV_full/2), 200)
for sign in (+1, -1):
    edge_ang = bisector + sign * FoV_full/2
    edge_rad = math.radians(edge_ang)
    ax1.plot([RIS[0], RIS[0] + 5 * math.cos(edge_rad)],
             [RIS[1], RIS[1] + 5 * math.sin(edge_rad)],
             color='gray', ls=':', lw=1.5, alpha=0.5)

x_fill = [RIS[0]] + list(RIS[0] + 5 * np.cos(theta_fill)) + [RIS[0]]
y_fill = [RIS[1]] + list(RIS[1] + 5 * np.sin(theta_fill)) + [RIS[1]]
ax1.fill(x_fill, y_fill, color='gray', alpha=0.08, label=f'FoV ±{FoV_full/2}°')

# Arc showing deflection angle
arc_radius = 1.2
theta1 = math.radians(phi_AP)
theta2 = math.radians(phi_AP + signed_diff)
theta_vals = np.linspace(theta1, theta2, 200)
xs = RIS[0] + arc_radius * np.cos(theta_vals)
ys = RIS[1] + arc_radius * np.sin(theta_vals)
ax1.plot(xs, ys, color='purple', lw=2.5, label=f'Deflection: {abs_diff:.2f}°')

mid_ang = math.radians(phi_AP + signed_diff / 2)
ax1.text(RIS[0] + 1.6 * math.cos(mid_ang),
         RIS[1] + 1.6 * math.sin(mid_ang),
         f"{abs_diff:.2f}°", color='purple', fontsize=10, fontweight='bold')

ax1.set_xlim(5, 19)
ax1.set_ylim(3, 13)
ax1.set_aspect('equal')
ax1.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
ax1.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='black')
ax1.set_title('RIS Geometry (Top-Down View)', fontsize=14, fontweight='bold', pad=15)
ax1.set_xlabel('X (m)', fontsize=11)
ax1.set_ylabel('Y (m)', fontsize=11)
ax1.tick_params(labelsize=10)

# Plot 2: Quantized phase (n-bit) (bottom, full width)
ax2 = fig.add_subplot(gs[1, 0])
im2 = ax2.imshow(phase_quant_deg, cmap='bwr', origin='lower', vmin=0, vmax=360)
ax2.set_title(f'RIS {n_bit}-Bit Quantized Phase Map (5.8 GHz, {num_levels} levels)', fontsize=12, fontweight='bold')
ax2.set_xlabel('Element index (x)', fontsize=10)
ax2.set_ylabel('Element index (y)', fontsize=10)
cax = fig.add_subplot(gs[1, 1])
cbar = fig.colorbar(im2, cax=cax)
cbar.set_label('Quantized Phase (°)')

plt.savefig('RIS_phase_pattern.png', dpi=150, bbox_inches='tight')
plt.show()

# Save numerical phase matrices
np.savetxt('RIS_phase_continuous.csv', phase_deg, fmt='%.1f', delimiter=',')
np.savetxt('RIS_phase_quantized_1bit.csv', phase_quant_deg, fmt='%.0f', delimiter=',')
