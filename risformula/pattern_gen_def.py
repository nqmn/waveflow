import numpy as np
import matplotlib.pyplot as plt
import math

# ===========================================================
# 5.8 GHz 1-Bit RIS Phase Pattern — Deflection Angle Version
# (from actual 3D node positions: AP, RIS, UE)
# Explicit decomposition: φ = φ_incident + φ_steering
# ===========================================================

# --- Physical constants
c = 299_792_458.0
f = 5.8e9
wavelength = c / f
k = 2 * np.pi / wavelength
d = 0.5 * wavelength   # half-wavelength element spacing (≈25.9 mm)

# --- RIS geometry
N = 16                               # 16×16 array (can change)
X, Y = np.meshgrid(np.arange(N), np.arange(N))

# --- Visualization and export flags
plot_components = False              # Set to True to generate component heatmaps (incident + steering)
export_csv = False                   # Set to True to export phase matrices to CSV files

# ===========================================================
# Define 3D coordinates of the nodes (meters)
# ===========================================================
# Example setup: AP→RIS = 7 m along x-axis; RIS→UE arbitrary in 3D
source = np.array([8.0, 10.0, 0.5])    # Source position (height 0.5 m above RIS)
ris_center = np.array([15.0, 10.0, 0.0])  # RIS center (reference)
target = np.array([11.4, 6.5, 0.0])       # Target position (UE)

# Source height above RIS plane (for spherical wave model)
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
# Compute deflection angle from geometry (2D azimuth angles)
# ===========================================================

# Extract 2D positions from 3D coordinates
AP = source[:2]
RIS = ris_center[:2]
UE = target[:2]

# Calculate absolute azimuth angles in XY plane
phi_AP = np.arctan2(AP[1] - RIS[1], AP[0] - RIS[0])
phi_UE = np.arctan2(UE[1] - RIS[1], UE[0] - RIS[0])

# Calculate angle difference (deflection angle)
angle_diff = phi_UE - phi_AP
# Wrap angle to [-π, π]
while angle_diff > np.pi:
    angle_diff -= 2 * np.pi
while angle_diff < -np.pi:
    angle_diff += 2 * np.pi

# Deflection angle (steering angle for RIS)
deflection_angle_rad = abs(angle_diff)
theta_rcv_rad = deflection_angle_rad

# Calculate incident and reflected angles (for reference)
theta_in_rad = phi_AP
theta_out_rad = phi_UE

print(f"Deflection angle: {np.degrees(deflection_angle_rad):.2f}°")
print(f"Incident angle (theta_in): {np.degrees(theta_in_rad):.2f}°")
print(f"Reflected angle (theta_out): {np.degrees(theta_out_rad):.2f}°")
print(f"Steering angle (theta_rcv = deflection): {np.degrees(theta_rcv_rad):.2f}°")

# ===========================================================
# Phase computation using DEFLECTION ANGLE DECOMPOSITION
# ===========================================================
# φ(i,j) = φ_incident(i,j) + φ_steering(i,j)
# where:
#   φ_incident = k·√(x_i² + y_i² + r_src²)  [spherical wavefront compensation]
#   φ_steering = -k·x_i·sin(θ_rcv)          [linear array steering to deflection angle]
# ===========================================================

phase_incident_rad = np.zeros_like(x_rel)
phase_steering_rad = np.zeros_like(x_rel)
phase_rad = np.zeros_like(x_rel)

for i in range(N):
    for j in range(N):
        # Element position relative to RIS center
        x_i = x_rel[i, j]
        y_i = y_rel[i, j]

        # Component 1: Incident spherical wavefront compensation
        # Accounts for phase advance due to spherical wave from source
        r_source_dist = np.sqrt(x_i**2 + y_i**2 + r_src**2)
        phase_incident_rad[i, j] = k * r_source_dist

        # Component 2: Steering phase (linear gradient from deflection angle)
        # Creates phase ramp to point reflected beam toward deflection direction
        phase_steering_rad[i, j] = -k * x_i * np.sin(theta_rcv_rad)

        # Total phase: superposition of incident and steering
        phase_rad[i, j] = (phase_incident_rad[i, j] + phase_steering_rad[i, j]) % (2 * np.pi)

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
print(f"Element spacing: {d*1000:.1f} mm (half-wavelength)")
print(f"Source height (r_src): {r_src:.3f} m")

# ===========================================================
# Pre-compute geometry visualization data (used by both plots)
# ===========================================================
# Convert previously computed angles to degrees for visualization
phi_AP_deg = np.degrees(theta_in_rad)
phi_UE_deg = np.degrees(theta_out_rad)

# Calculate deflection angle in degrees
angle_diff_rad = theta_out_rad - theta_in_rad
# Wrap angle to [-π, π]
while angle_diff_rad > np.pi:
    angle_diff_rad -= 2 * np.pi
while angle_diff_rad < -np.pi:
    angle_diff_rad += 2 * np.pi

abs_diff = np.degrees(abs(angle_diff_rad))
signed_diff = np.degrees(angle_diff_rad)
bisector = phi_AP_deg + signed_diff / 2
FoV_full = 60  # Full field of view (degrees)

# Pre-compute visualization elements
arc_radius = 1.2
# Normalize angles for arc visualization (theta_out_rad may be negative)
theta1_norm = theta_in_rad
theta2_norm = theta_out_rad
# Ensure arc goes in correct direction (short arc between incident and reflected)
if theta2_norm < theta1_norm:
    theta2_norm += 2 * np.pi
theta_vals = np.linspace(theta1_norm, theta2_norm, 200)
xs = RIS[0] + arc_radius * np.cos(theta_vals)
ys = RIS[1] + arc_radius * np.sin(theta_vals)
mid_ang = (theta1_norm + theta2_norm) / 2

theta_fill = np.linspace(math.radians(bisector - FoV_full/2),
                         math.radians(bisector + FoV_full/2), 200)
x_fill = [RIS[0]] + list(RIS[0] + 5 * np.cos(theta_fill)) + [RIS[0]]
y_fill = [RIS[1]] + list(RIS[1] + 5 * np.sin(theta_fill)) + [RIS[1]]

# ===========================================================
# Plotting Section 1: Component visualization (if enabled)
# ===========================================================
if plot_components:
    fig = plt.figure(figsize=(14, 16))

    # Grid layout: 3 rows, 2 columns for separate incident/steering/combined heatmaps
    gs = fig.add_gridspec(
        3,
        2,
        height_ratios=[1.5, 1, 1],
        width_ratios=[30, 1.2],
        hspace=0.4,
        wspace=0.1,
        left=0.08,
        right=0.95,
        top=0.95,
        bottom=0.06,
    )

    # Plot 1: Geometry (Top-down view) - full width top
    ax0 = fig.add_subplot(gs[0, :])

    # Scatter plot for nodes
    ax0.scatter(AP[0], AP[1], s=120, color='green', marker='s', label='Source (AP)', zorder=5)
    ax0.scatter(RIS[0], RIS[1], s=160, color='orange', marker='^', label='RIS', zorder=5)
    ax0.scatter(UE[0], UE[1], s=120, color='red', marker='o', label='Target (UE)', zorder=5)

    # Lines from RIS to other nodes
    ax0.plot([RIS[0], AP[0]], [RIS[1], AP[1]], 'g--', lw=2, label=f'RIS→AP ({phi_AP_deg:.1f}°)', alpha=0.7)
    ax0.plot([RIS[0], UE[0]], [RIS[1], UE[1]], 'r--', lw=2, label=f'RIS→UE ({phi_UE_deg:.1f}°)', alpha=0.7)

    # Field of View cone
    for sign in (+1, -1):
        edge_ang = bisector + sign * FoV_full/2
        edge_rad = math.radians(edge_ang)
        ax0.plot([RIS[0], RIS[0] + 5 * math.cos(edge_rad)],
                 [RIS[1], RIS[1] + 5 * math.sin(edge_rad)],
                 color='gray', ls=':', lw=1.5, alpha=0.5)

    ax0.fill(x_fill, y_fill, color='gray', alpha=0.08, label=f'FoV ±{FoV_full/2}°')

    # Arc showing deflection angle
    ax0.plot(xs, ys, color='purple', lw=2.5, label=f'Deflection: {abs_diff:.2f}°')
    ax0.text(RIS[0] + 1.6 * math.cos(mid_ang),
             RIS[1] + 1.6 * math.sin(mid_ang),
             f"{abs_diff:.2f}°", color='purple', fontsize=10, fontweight='bold')

    ax0.set_xlim(5, 19)
    ax0.set_ylim(3, 13)
    ax0.set_aspect('equal')
    ax0.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax0.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='black')
    ax0.set_title('RIS Geometry (Top-Down View)', fontsize=14, fontweight='bold', pad=15)
    ax0.set_xlabel('X (m)', fontsize=11)
    ax0.set_ylabel('Y (m)', fontsize=11)
    ax0.tick_params(labelsize=10)

    # Plot 2: Incident wavefront phase component (spherical compensation)
    ax1 = fig.add_subplot(gs[1, 0])
    phase_incident_deg = np.degrees(phase_incident_rad)
    im1 = ax1.imshow(phase_incident_deg, cmap='viridis', origin='lower')
    ax1.set_title(f'Incident Phase Component: φ_incident = k·√(x² + y² + r_src²)',
                  fontsize=11, fontweight='bold')
    ax1.set_xlabel('Element index (x)', fontsize=10)
    ax1.set_ylabel('Element index (y)', fontsize=10)
    cax1 = fig.add_subplot(gs[1, 1])
    cbar1 = fig.colorbar(im1, cax=cax1)
    cbar1.set_label('Phase (°)')

    # Plot 3: Steering phase component (linear gradient from deflection)
    ax2 = fig.add_subplot(gs[2, 0])
    phase_steering_deg = np.degrees(phase_steering_rad)
    im2 = ax2.imshow(phase_steering_deg, cmap='RdBu_r', origin='lower')
    ax2.set_title(f'Steering Phase Component: φ_steering = -k·x_i·sin(θ_rcv={np.degrees(theta_rcv_rad):.2f}°)',
                  fontsize=11, fontweight='bold')
    ax2.set_xlabel('Element index (x)', fontsize=10)
    ax2.set_ylabel('Element index (y)', fontsize=10)
    cax2 = fig.add_subplot(gs[2, 1])
    cbar2 = fig.colorbar(im2, cax=cax2)
    cbar2.set_label('Phase (°)')

    # Note: Component phases are continuous (0-360°), only combined phase is quantized

    plt.savefig('RIS_phase_pattern_deflection_components.png', dpi=150, bbox_inches='tight')
    print("Saved: RIS_phase_pattern_deflection_components.png")

# ===========================================================
# Plotting Section 2: Combined phase visualization (always generated)
# ===========================================================
fig2 = plt.figure(figsize=(10, 14))
gs2 = fig2.add_gridspec(
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

# Plot geometry for combined figure
ax_g = fig2.add_subplot(gs2[0, :])
ax_g.scatter(AP[0], AP[1], s=120, color='green', marker='s', label='Source (AP)', zorder=5)
ax_g.scatter(RIS[0], RIS[1], s=160, color='orange', marker='^', label='RIS', zorder=5)
ax_g.scatter(UE[0], UE[1], s=120, color='red', marker='o', label='Target (UE)', zorder=5)
ax_g.plot([RIS[0], AP[0]], [RIS[1], AP[1]], 'g--', lw=2, label=f'RIS→AP ({phi_AP_deg:.1f}°)', alpha=0.7)
ax_g.plot([RIS[0], UE[0]], [RIS[1], UE[1]], 'r--', lw=2, label=f'RIS→UE ({phi_UE_deg:.1f}°)', alpha=0.7)
ax_g.plot(xs, ys, color='purple', lw=2.5, label=f'Deflection: {abs_diff:.2f}°')
ax_g.text(RIS[0] + 1.6 * math.cos(mid_ang), RIS[1] + 1.6 * math.sin(mid_ang),
         f"{abs_diff:.2f}°", color='purple', fontsize=10, fontweight='bold')
ax_g.set_xlim(5, 19)
ax_g.set_ylim(3, 13)
ax_g.set_aspect('equal')
ax_g.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
ax_g.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='black')
ax_g.set_title('RIS Geometry (Top-Down View)', fontsize=14, fontweight='bold', pad=15)
ax_g.set_xlabel('X (m)', fontsize=11)
ax_g.set_ylabel('Y (m)', fontsize=11)
ax_g.tick_params(labelsize=10)

# Plot combined quantized phase
ax3 = fig2.add_subplot(gs2[1, 0])

# Determine colorbar range based on number of quantization levels
vmax_phase = 360.0 / (2 ** n_bit) * ((2 ** n_bit) - 1)

im3 = ax3.imshow(phase_quant_deg, cmap='bwr', origin='lower', vmin=0, vmax=vmax_phase)
ax3.set_title(f'RIS {n_bit}-Bit Quantized Phase Map (5.8 GHz, {num_levels} levels) — Deflection Angle Version\n'
              f'φ = φ_incident + φ_steering | Steering angle: {np.degrees(theta_rcv_rad):.2f}°',
              fontsize=12, fontweight='bold')
ax3.set_xlabel('Element index (x)', fontsize=10)
ax3.set_ylabel('Element index (y)', fontsize=10)
cax3 = fig2.add_subplot(gs2[1, 1])
cbar3 = fig2.colorbar(im3, cax=cax3)
cbar3.set_label(f'Quantized Phase (0-{vmax_phase:.0f}°)')

# Save combined figure
plt.savefig('RIS_phase_pattern_deflection.png', dpi=150, bbox_inches='tight')
print("Saved: RIS_phase_pattern_deflection.png")

plt.show()

# ===========================================================
# Save component matrices for ML analysis (optional)
# ===========================================================
if export_csv:
    phase_incident_deg = np.degrees(phase_incident_rad)
    phase_steering_deg = np.degrees(phase_steering_rad)

    np.savetxt('RIS_phase_incident.csv', phase_incident_deg, fmt='%.2f', delimiter=',')
    np.savetxt('RIS_phase_steering.csv', phase_steering_deg, fmt='%.2f', delimiter=',')
    np.savetxt('RIS_phase_continuous.csv', phase_deg, fmt='%.1f', delimiter=',')
    np.savetxt('RIS_phase_quantized_1bit.csv', phase_quant_deg, fmt='%.0f', delimiter=',')

    print("  - RIS_phase_incident.csv (incident component)")
    print("  - RIS_phase_steering.csv (steering component)")
    print("  - RIS_phase_continuous.csv (combined continuous phase)")
    print("  - RIS_phase_quantized_1bit.csv (combined quantized phase)")

print("\nFiles saved:")
if plot_components:
    print("  - RIS_phase_pattern_deflection_components.png (incident + steering components)")
print("  - RIS_phase_pattern_deflection_.png (combined phase heatmap)")
