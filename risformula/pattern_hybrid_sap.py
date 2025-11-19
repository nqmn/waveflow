import numpy as np
import matplotlib.pyplot as plt
import scipy.constants as const
from scipy.linalg import norm
from matplotlib.colors import ListedColormap

# Helper function: Cartesian -> Spherical
def cart2sp(x, y, z):
    r= np.sqrt(x**2 + y**2 + z**2)
    theta = np.arccos(z / r) if r != 0 else 0  # Avoid division by zero
    phi = np.arctan2(y, x)
    return r, theta, phi

# Helper function: Spherical -> Cartesian
def sph2cart(r, theta, phi):
    """
    Converts spherical coordinates to Cartesian.
    r: radial distance
    theta: polar angle [0, pi]
    phi: azimuth angle [-pi, pi]
    """
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)
    return x, y, z

# Function to compute and plot the phase pattern
def pattern(plane_tx, plane_rx, freq, r_src, r_rcv, theta_src, phi_src, theta_rcv, phi_rcv,
            nx_in, ny_in, dx, dy, mode, bit):

    # Constants
    c = const.c
    k = 2 * np.pi * freq / c  # Wavenumber

    # Convert angles from degrees to radians
    theta_src, phi_src = np.radians(theta_src), np.radians(phi_src)
    theta_rcv, phi_rcv = np.radians(theta_rcv), np.radians(phi_rcv)

    # Convert spherical -> Cartesian for TX and RX positions
    r_src_cart = sph2cart(r_src, theta_src, phi_src)
    r_rcv_cart = sph2cart(r_rcv, theta_rcv, phi_rcv)

    # Unit vectors (for plane waves)
    u_tx = np.array(r_src_cart) / np.linalg.norm(r_src_cart) if np.linalg.norm(r_src_cart) != 0 else np.array([0.0, 0.0, 1.0])
    u_rx = np.array(r_rcv_cart) / np.linalg.norm(r_rcv_cart) if np.linalg.norm(r_rcv_cart) != 0 else np.array([0.0, 0.0, 1.0])

    # Define array grid
    nx, ny = nx_in, ny_in
    N = nx * ny

    r_c = np.zeros((N, 3))  # Array element positions [x, y, z=0]
    lim_x, lim_y = (nx - 1) / 2 * dx, (ny - 1) / 2 * dy

    x_coords = np.linspace(-lim_x, lim_x, nx)
    y_coords = np.linspace(-lim_y, lim_y, ny)

    # Fill coordinates
    r_c[:, 0] = np.tile(x_coords, ny)
    r_c[:, 1] = np.repeat(y_coords, nx)

    # ==============================
    # Compute Phase from TX side
    # ==============================
    if plane_tx:
        phase_tx = -k * np.dot(r_c, u_tx)  # Plane wave
    else:
        dist_tx = norm(r_src_cart - r_c, axis=1)
        phase_tx = k * dist_tx  # Spherical wave

    # ==============================
    # Compute Phase from/to RX side
    # ==============================
    if plane_rx:
        phase_rx = -k * np.dot(r_c, u_rx)  # Plane wave
    else:
        dist_rx = norm(r_rcv_cart - r_c, axis=1)
        phase_rx = k * dist_rx  # Spherical wave

    # Total TX + RX phase
    phase_prop = (phase_tx + phase_rx) % (2 * np.pi)

    # ==============================
    # Add OAM Phase
    # ==============================
    phi_oam = np.arctan2(r_c[:, 1], r_c[:, 0])
    phase_oam = (mode * phi_oam) % (2 * np.pi)

    # Combine phases
    phase_total = (phase_prop + phase_oam) % (2 * np.pi)

    # ==============================
    # Quantization
    # ==============================
    nlevels = 2**bit  # Number of quantization levels
    intervals = np.linspace(0, 2 * np.pi, nlevels + 1, endpoint=True)

    phase_prop_dg = np.digitize(phase_prop, intervals) - 1
    phase_oam_dg = np.digitize(phase_oam, intervals) - 1
    phase_total_dg = np.digitize(phase_total, intervals) - 1

    # Reshape for plotting
    phase_prop_deg = np.degrees(phase_prop).reshape(nx, ny)
    phase_oam_deg = np.degrees(phase_oam).reshape(nx, ny)
    phase_total_deg = np.degrees(phase_total).reshape(nx, ny)

    phase_prop_dg = phase_prop_dg.reshape(nx, ny)
    phase_oam_dg = phase_oam_dg.reshape(nx, ny)
    phase_total_dg = phase_total_dg.reshape(nx, ny)

    # ==============================
    # Colormap for Quantization
    # ==============================
    color_map_options = {
        1: ['blue', 'yellow'],
        2: ['blue', 'green', 'yellow', 'red'],
        3: ['blue', 'green', 'yellow', 'red', 'purple', 'orange', 'pink', 'gray'],
        4: ['blue', 'green', 'yellow', 'red', 'purple', 'orange', 'pink', 'gray',
            'cyan', 'magenta', 'lime', 'brown', 'teal', 'gold', 'navy', 'maroon']
    }

    cmap_q = ListedColormap(color_map_options[bit]) if bit in color_map_options else plt.get_cmap('jet', nlevels)

    # ==============================
    # Plotting
    # ==============================
    plt.figure(figsize=(20, 10))

    # TX+RX Propagation Phase (no OAM)
    plt.subplot(231)
    plt.pcolormesh(phase_prop_deg, cmap='jet', shading='auto')
    plt.title('Propagation Phase (TX + RX)')
    plt.colorbar(label='Degrees')

    # OAM Phase
    plt.subplot(232)
    plt.pcolormesh(phase_oam_deg, cmap='jet', shading='auto')
    plt.title('OAM Phase')
    plt.colorbar(label='Degrees')

    # Total Phase
    plt.subplot(233)
    plt.pcolormesh(phase_total_deg, cmap='jet', shading='auto')
    plt.title('Total Phase (Propagation + OAM)')
    plt.colorbar(label='Degrees')

    # Quantized Plots
    for i, (data, title) in enumerate(zip([phase_prop_dg, phase_oam_dg, phase_total_dg],
                                          ['Quantized Propagation Phase', 'Quantized OAM Phase', 'Quantized Total Phase']), start=4):
        plt.subplot(230 + i)
        plt.pcolormesh(data, cmap=cmap_q, shading='auto')
        plt.title(f'{title} ({bit}-bit)')
        plt.colorbar(label='Level', ticks=np.arange(nlevels))

    plt.tight_layout()
    plt.show()

# Example usage:
pattern(plane_tx=0,
        plane_rx=0,
        freq=5.8e9,
        r_src=0.5,
        r_rcv=0.5,
        theta_src=0,
        theta_rcv=45,
        phi_src=0,
        phi_rcv=0,
        nx_in=16, ny_in=16,
        dx=0.02585, dy=0.02585,
        mode=0,
        bit=1)