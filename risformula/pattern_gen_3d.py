import numpy as np
import matplotlib.pyplot as plt
import math

# ===========================================================
# 5.8 GHz 1-Bit RIS Phase Pattern — 3D Deflection Angle Version
# (from actual 3D node positions: AP, RIS, UE)
# Explicit decomposition: φ = φ_incident + φ_steering (azimuth + elevation)
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

# Source offset and height above RIS plane
delta_x_s = source[0] - ris_center[0]
delta_y_s = source[1] - ris_center[1]
delta_z_s = source[2] - ris_center[2]

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
# Compute 3D deflection angles from geometry (azimuth + elevation)
# ===========================================================

# Calculate direction vectors in 3D
to_target = target - ris_center
to_target_norm = to_target / np.linalg.norm(to_target)

from_source = ris_center - source
from_source_norm = from_source / np.linalg.norm(from_source)

# ===== AZIMUTH STEERING (Horizontal) =====
# Extract 2D components (XY plane only)
vec_in_2d = from_source_norm[:2]
vec_out_2d = to_target_norm[:2]
len_in = np.linalg.norm(vec_in_2d)
len_out = np.linalg.norm(vec_out_2d)

# Calculate azimuth deflection angle (angle between incident and reflected directions in XY plane)
if len_in > 1e-6 and len_out > 1e-6:
    norm_in_2d = vec_in_2d / len_in
    norm_out_2d = vec_out_2d / len_out
    dot_product_az = np.clip(np.dot(norm_in_2d, norm_out_2d), -1, 1)
    azimuth_deflection_rad = np.arccos(dot_product_az)
else:
    azimuth_deflection_rad = np.pi / 2

# Calculate azimuth angles
theta_in_rad = np.arctan2(norm_in_2d[1], norm_in_2d[0])
theta_out_rad = np.arctan2(norm_out_2d[1], norm_out_2d[0])

# ===== ELEVATION STEERING (Vertical) =====
# Calculate elevation angles
r_horizontal_source = np.sqrt(delta_x_s**2 + delta_y_s**2)
r_horizontal_target = np.sqrt((target[0] - ris_center[0])**2 + (target[1] - ris_center[1])**2)

if r_horizontal_source > 1e-6:
    elevation_in_rad = np.arctan2(delta_z_s, r_horizontal_source)
else:
    elevation_in_rad = np.pi / 2 if delta_z_s > 0 else -np.pi / 2

if r_horizontal_target > 1e-6:
    elevation_out_rad = np.arctan2(target[2] - ris_center[2], r_horizontal_target)
else:
    elevation_out_rad = 0

# Elevation deflection angle
elevation_deflection_rad = elevation_out_rad - elevation_in_rad

print("========== 3D BEAMFORMING ==========")
print(f"Azimuth deflection angle: {np.degrees(azimuth_deflection_rad):.2f}°")
print(f"Elevation deflection angle: {np.degrees(elevation_deflection_rad):.2f}°")
print(f"Incident azimuth (theta_in): {np.degrees(theta_in_rad):.2f}°")
print(f"Reflected azimuth (theta_out): {np.degrees(theta_out_rad):.2f}°")
print(f"Incident elevation: {np.degrees(elevation_in_rad):.2f}°")
print(f"Reflected elevation: {np.degrees(elevation_out_rad):.2f}°")
print(f"Source offset: Δx={delta_x_s:.3f} m, Δy={delta_y_s:.3f} m, Δz={delta_z_s:.3f} m")

# ===========================================================
# Phase computation using 3D DEFLECTION ANGLE DECOMPOSITION
# ===========================================================
# φ(i,j) = φ_incident(i,j) + φ_steering_azimuth(i,j) + φ_steering_elevation(i,j)
# where:
#   φ_incident = k·√((Δx_s - x_i)² + (Δy_s - y_i)² + Δz_s²)  [spherical wavefront from source]
#   φ_steering_azimuth = -k·x_i·sin(Δθ_az)                   [azimuth array steering]
#   φ_steering_elevation = -k·y_i·sin(Δθ_el)                 [elevation array steering]
# ===========================================================

phase_incident_rad = np.zeros_like(x_rel)
phase_steering_azimuth_rad = np.zeros_like(x_rel)
phase_steering_elevation_rad = np.zeros_like(x_rel)
phase_rad = np.zeros_like(x_rel)

for i in range(N):
    for j in range(N):
        # Element position relative to RIS center
        x_i = x_rel[i, j]
        y_i = y_rel[i, j]

        # Component 1: Incident spherical wavefront compensation (3D version)
        # Accounts for phase advance due to spherical wave from source
        # Phase depends on distance from source to element
        # Since RIS is relative to RIS center, and element position is relative to RIS center,
        # the distance is based on element position and source height
        r_source_dist = np.sqrt(x_i**2 + y_i**2 + delta_z_s**2)
        phase_incident_rad[i, j] = k * r_source_dist

        # Component 2: Azimuth steering phase (horizontal, x-direction)
        # Creates phase ramp to point reflected beam toward azimuth deflection direction
        phase_steering_azimuth_rad[i, j] = -k * x_i * np.sin(azimuth_deflection_rad)

        # Component 3: Elevation steering phase (vertical, y-direction)
        # Creates phase ramp for elevation steering (note: 2D RIS has limited elevation control)
        phase_steering_elevation_rad[i, j] = -k * y_i * np.sin(elevation_deflection_rad)

        # Total phase: superposition of incident, azimuth steering, and elevation steering
        phase_rad[i, j] = (phase_incident_rad[i, j] + phase_steering_azimuth_rad[i, j] +
                          phase_steering_elevation_rad[i, j]) % (2 * np.pi)

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
print(f"\nSource→RIS distance: {np.linalg.norm(vec_in):.2f} m")
print(f"RIS→Target distance: {np.linalg.norm(vec_out):.2f} m")
print(f"Incident angle:  {theta_inc:.2f}°   Reflected angle: {theta_ref:.2f}°")
print(f"Element spacing: {d*1000:.1f} mm (half-wavelength)")

# ===========================================================
# Pre-compute geometry visualization data (used by both plots)
# ===========================================================
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

# Pre-compute visualization elements
arc_radius = 1.2
theta1 = math.radians(phi_AP)
theta2 = math.radians(phi_AP + signed_diff)
theta_vals = np.linspace(theta1, theta2, 200)
xs = RIS[0] + arc_radius * np.cos(theta_vals)
ys = RIS[1] + arc_radius * np.sin(theta_vals)
mid_ang = math.radians(phi_AP + signed_diff / 2)

theta_fill = np.linspace(math.radians(bisector - FoV_full/2),
                         math.radians(bisector + FoV_full/2), 200)
x_fill = [RIS[0]] + list(RIS[0] + 5 * np.cos(theta_fill)) + [RIS[0]]
y_fill = [RIS[1]] + list(RIS[1] + 5 * np.sin(theta_fill)) + [RIS[1]]

# ===========================================================
# Plotting Section 1: Component visualization (if enabled)
# ===========================================================
if plot_components:
    fig = plt.figure(figsize=(14, 20))

    # Grid layout: 4 rows, 2 columns for incident/azimuth/elevation/combined heatmaps
    gs = fig.add_gridspec(
        4,
        2,
        height_ratios=[1.5, 1, 1, 1],
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
    ax0.plot([RIS[0], AP[0]], [RIS[1], AP[1]], 'g--', lw=2, label=f'RIS→AP ({phi_AP:.1f}°)', alpha=0.7)
    ax0.plot([RIS[0], UE[0]], [RIS[1], UE[1]], 'r--', lw=2, label=f'RIS→UE ({phi_UE:.1f}°)', alpha=0.7)

    # Field of View cone
    for sign in (+1, -1):
        edge_ang = bisector + sign * FoV_full/2
        edge_rad = math.radians(edge_ang)
        ax0.plot([RIS[0], RIS[0] + 5 * math.cos(edge_rad)],
                 [RIS[1], RIS[1] + 5 * math.sin(edge_rad)],
                 color='gray', ls=':', lw=1.5, alpha=0.5)

    ax0.fill(x_fill, y_fill, color='gray', alpha=0.08, label=f'FoV ±{FoV_full/2}°')

    # Arc showing deflection angle
    ax0.plot(xs, ys, color='purple', lw=2.5, label=f'Azimuth Deflection: {abs_diff:.2f}°')
    ax0.text(RIS[0] + 1.6 * math.cos(mid_ang),
             RIS[1] + 1.6 * math.sin(mid_ang),
             f"{abs_diff:.2f}°", color='purple', fontsize=10, fontweight='bold')

    ax0.set_xlim(5, 19)
    ax0.set_ylim(3, 13)
    ax0.set_aspect('equal')
    ax0.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    ax0.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='black')
    ax0.set_title('RIS Geometry (Top-Down View) — 3D Beamforming', fontsize=14, fontweight='bold', pad=15)
    ax0.set_xlabel('X (m)', fontsize=11)
    ax0.set_ylabel('Y (m)', fontsize=11)
    ax0.tick_params(labelsize=10)

    # Plot 2: Incident wavefront phase component (3D spherical compensation)
    ax1 = fig.add_subplot(gs[1, 0])
    phase_incident_deg = np.degrees(phase_incident_rad)
    im1 = ax1.imshow(phase_incident_deg, cmap='viridis', origin='lower')
    ax1.set_title(f'Incident Phase Component (3D): φ_incident = k·√((Δx_s - x_i)² + (Δy_s - y_i)² + Δz_s²)',
                  fontsize=11, fontweight='bold')
    ax1.set_xlabel('Element index (x)', fontsize=10)
    ax1.set_ylabel('Element index (y)', fontsize=10)
    cax1 = fig.add_subplot(gs[1, 1])
    cbar1 = fig.colorbar(im1, cax=cax1)
    cbar1.set_label('Phase (°)')

    # Plot 3: Azimuth steering phase component
    ax2 = fig.add_subplot(gs[2, 0])
    phase_steering_azimuth_deg = np.degrees(phase_steering_azimuth_rad)
    im2 = ax2.imshow(phase_steering_azimuth_deg, cmap='RdBu_r', origin='lower')
    ax2.set_title(f'Azimuth Steering: φ_az = -k·x_i·sin(Δθ_az={np.degrees(azimuth_deflection_rad):.2f}°)',
                  fontsize=11, fontweight='bold')
    ax2.set_xlabel('Element index (x)', fontsize=10)
    ax2.set_ylabel('Element index (y)', fontsize=10)
    cax2 = fig.add_subplot(gs[2, 1])
    cbar2 = fig.colorbar(im2, cax=cax2)
    cbar2.set_label('Phase (°)')

    # Plot 4: Elevation steering phase component
    ax3 = fig.add_subplot(gs[3, 0])
    phase_steering_elevation_deg = np.degrees(phase_steering_elevation_rad)
    im3 = ax3.imshow(phase_steering_elevation_deg, cmap='RdBu_r', origin='lower')
    ax3.set_title(f'Elevation Steering: φ_el = -k·y_i·sin(Δθ_el={np.degrees(elevation_deflection_rad):.2f}°)',
                  fontsize=11, fontweight='bold')
    ax3.set_xlabel('Element index (x)', fontsize=10)
    ax3.set_ylabel('Element index (y)', fontsize=10)
    cax3 = fig.add_subplot(gs[3, 1])
    cbar3 = fig.colorbar(im3, cax=cax3)
    cbar3.set_label('Phase (°)')

    # Note: Component phases are continuous (0-360°), only combined phase is quantized

    plt.savefig('RIS_phase_pattern_3d_components.png', dpi=150, bbox_inches='tight')
    print("Saved: RIS_phase_pattern_3d_components.png")

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
ax_g.plot([RIS[0], AP[0]], [RIS[1], AP[1]], 'g--', lw=2, label=f'RIS→AP ({phi_AP:.1f}°)', alpha=0.7)
ax_g.plot([RIS[0], UE[0]], [RIS[1], UE[1]], 'r--', lw=2, label=f'RIS→UE ({phi_UE:.1f}°)', alpha=0.7)
ax_g.plot(xs, ys, color='purple', lw=2.5, label=f'Azimuth Deflection: {abs_diff:.2f}°')
ax_g.text(RIS[0] + 1.6 * math.cos(mid_ang), RIS[1] + 1.6 * math.sin(mid_ang),
         f"{abs_diff:.2f}°", color='purple', fontsize=10, fontweight='bold')
ax_g.set_xlim(5, 19)
ax_g.set_ylim(3, 13)
ax_g.set_aspect('equal')
ax_g.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
ax_g.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='black')
ax_g.set_title('RIS Geometry (Top-Down View) — 3D Beamforming', fontsize=14, fontweight='bold', pad=15)
ax_g.set_xlabel('X (m)', fontsize=11)
ax_g.set_ylabel('Y (m)', fontsize=11)
ax_g.tick_params(labelsize=10)

# Plot combined quantized phase
ax4 = fig2.add_subplot(gs2[1, 0])

# Determine colorbar range based on number of quantization levels
vmax_phase = 360.0 / (2 ** n_bit) * ((2 ** n_bit) - 1)

im4 = ax4.imshow(phase_quant_deg, cmap='bwr', origin='lower', vmin=0, vmax=vmax_phase)
ax4.set_title(f'RIS {n_bit}-Bit Quantized Phase Map (5.8 GHz, {num_levels} levels) — 3D Beamforming\n'
              f'φ = φ_incident + φ_az + φ_el | Geometric az: {abs_diff:.2f}° | Steering az: {np.degrees(azimuth_deflection_rad):.2f}° | Steering el: {np.degrees(elevation_deflection_rad):.2f}°',
              fontsize=12, fontweight='bold')
ax4.set_xlabel('Element index (x)', fontsize=10)
ax4.set_ylabel('Element index (y)', fontsize=10)
cax4 = fig2.add_subplot(gs2[1, 1])
cbar4 = fig2.colorbar(im4, cax=cax4)
cbar4.set_label(f'Quantized Phase (0-{vmax_phase:.0f}°)')

# Save combined figure
plt.savefig('RIS_phase_pattern_3d.png', dpi=150, bbox_inches='tight')
print("Saved: RIS_phase_pattern_3d.png")

plt.show()

# ===========================================================
# Save component matrices for ML analysis (optional)
# ===========================================================
if export_csv:
    phase_incident_deg = np.degrees(phase_incident_rad)
    phase_steering_azimuth_deg = np.degrees(phase_steering_azimuth_rad)
    phase_steering_elevation_deg = np.degrees(phase_steering_elevation_rad)

    np.savetxt('RIS_phase_incident_3d.csv', phase_incident_deg, fmt='%.2f', delimiter=',')
    np.savetxt('RIS_phase_steering_azimuth_3d.csv', phase_steering_azimuth_deg, fmt='%.2f', delimiter=',')
    np.savetxt('RIS_phase_steering_elevation_3d.csv', phase_steering_elevation_deg, fmt='%.2f', delimiter=',')
    np.savetxt('RIS_phase_continuous_3d.csv', phase_deg, fmt='%.1f', delimiter=',')
    np.savetxt('RIS_phase_quantized_3d.csv', phase_quant_deg, fmt='%.0f', delimiter=',')

    print("  - RIS_phase_incident_3d.csv (incident component, 3D formula)")
    print("  - RIS_phase_steering_azimuth_3d.csv (azimuth steering component)")
    print("  - RIS_phase_steering_elevation_3d.csv (elevation steering component)")
    print("  - RIS_phase_continuous_3d.csv (combined continuous phase)")
    print("  - RIS_phase_quantized_3d.csv (combined quantized phase)")

print("\nFiles saved:")
if plot_components:
    print("  - RIS_phase_pattern_3d_components.png (incident + steering components)")
print("  - RIS_phase_pattern_3d.png (combined phase heatmap)")
