"""
RIS Hybrid Phase Engine - Flexible near-field/far-field phase computation

Implements Approach B (flag-based) from risformula/formula_hybrid.md:
- Independent TX and RX wave type control
- All 4 combinations: spherical/plane TX × spherical/plane RX
- Automatic Fraunhofer boundary selection
- Full flexibility for research and production use

Author: Generated for risnet hybrid integration
"""

import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class HybridPhaseEngine:
    """Hybrid RIS phase pattern generator with flexible TX/RX wave types"""

    # Physical constants
    C = 299_792_458.0  # Speed of light (m/s)

    @staticmethod
    def fraunhofer_boundary(array_size: int, element_spacing: float, wavelength: float) -> float:
        """
        Compute Fraunhofer boundary: r_boundary = 2D²/λ
        where D is the array aperture.

        Args:
            array_size: RIS array size (N for N×N)
            element_spacing: Distance between elements (m)
            wavelength: Operating wavelength (m)

        Returns:
            Fraunhofer boundary distance (m)
        """
        D = (array_size - 1) * element_spacing
        return 2.0 * (D ** 2) / wavelength

    @staticmethod
    def generate_ris_grid(array_size: int, element_spacing: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate RIS element grid centered at origin.

        Args:
            array_size: N for N×N array
            element_spacing: Distance between elements (m)

        Returns:
            Tuple of (X, Y, Z) meshgrids for element positions
        """
        lim_x = (array_size - 1) / 2 * element_spacing
        lim_y = (array_size - 1) / 2 * element_spacing
        x_coords = np.linspace(-lim_x, lim_x, array_size)
        y_coords = np.linspace(-lim_y, lim_y, array_size)
        X, Y = np.meshgrid(x_coords, y_coords)
        Z = np.zeros_like(X)
        return X, Y, Z

    @staticmethod
    def incident_phase_spherical(
        k: float,
        source_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        x_rel: np.ndarray,
        y_rel: np.ndarray
    ) -> np.ndarray:
        """
        Compute incident phase using spherical wave (near-field TX).

        Formula: φ_tx(i,j) = k·√[(Δx_s - x_i)² + (Δy_s - y_i)² + Δz_s²]

        Args:
            k: Wavenumber (2π/λ)
            source_pos: AP position [x_s, y_s, z_s]
            ris_center_pos: RIS center position [x_r, y_r, z_r]
            x_rel: X-coordinates of elements relative to RIS center
            y_rel: Y-coordinates of elements relative to RIS center

        Returns:
            Incident phase array (radians)
        """
        delta_x_s = source_pos[0] - ris_center_pos[0]
        delta_y_s = source_pos[1] - ris_center_pos[1]
        delta_z_s = source_pos[2] - ris_center_pos[2]

        # Distance from AP to each element
        r_src = np.sqrt((delta_x_s - x_rel)**2 + (delta_y_s - y_rel)**2 + delta_z_s**2)
        phi_incident = k * r_src
        return phi_incident

    @staticmethod
    def incident_phase_plane(
        k: float,
        source_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        x_rel: np.ndarray,
        y_rel: np.ndarray
    ) -> np.ndarray:
        """
        Compute incident phase using plane wave (far-field TX).

        Formula: φ_tx(i,j) = -k·(x_i·u_s,x + y_i·u_s,y)

        Args:
            k: Wavenumber (2π/λ)
            source_pos: AP position [x_s, y_s, z_s]
            ris_center_pos: RIS center position [x_r, y_r, z_r]
            x_rel: X-coordinates of elements relative to RIS center
            y_rel: Y-coordinates of elements relative to RIS center

        Returns:
            Incident phase array (radians)
        """
        delta_x_s = source_pos[0] - ris_center_pos[0]
        delta_y_s = source_pos[1] - ris_center_pos[1]
        delta_z_s = source_pos[2] - ris_center_pos[2]

        # Normalized direction vector
        norm_src = np.sqrt(delta_x_s**2 + delta_y_s**2 + delta_z_s**2)
        if norm_src < 1e-9:
            return np.zeros_like(x_rel)

        u_s_x = delta_x_s / norm_src
        u_s_y = delta_y_s / norm_src

        # Linear phase gradient
        phi_incident = -k * (x_rel * u_s_x + y_rel * u_s_y)
        return phi_incident

    @staticmethod
    def reflect_phase_spherical(
        k: float,
        target_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        x_rel: np.ndarray,
        y_rel: np.ndarray,
        z_rel: np.ndarray
    ) -> np.ndarray:
        """
        Compute reflect phase using spherical wave (near-field RX, point focusing).

        Formula: φ_rx(i,j) = k·√[(x_t - x_i)² + (y_t - y_i)² + (z_t - z_i)²]

        Args:
            k: Wavenumber (2π/λ)
            target_pos: UE position [x_t, y_t, z_t]
            ris_center_pos: RIS center position [x_r, y_r, z_r]
            x_rel: X-coordinates of elements relative to RIS center
            y_rel: Y-coordinates of elements relative to RIS center
            z_rel: Z-coordinates of elements relative to RIS center

        Returns:
            Reflect phase array (radians)
        """
        # Convert relative to absolute coordinates
        x_abs = ris_center_pos[0] + x_rel
        y_abs = ris_center_pos[1] + y_rel
        z_abs = ris_center_pos[2] + z_rel

        # Distance from each element to target
        r_rcv = np.sqrt((target_pos[0] - x_abs)**2 + (target_pos[1] - y_abs)**2 + (target_pos[2] - z_abs)**2)
        phi_reflect = k * r_rcv
        return phi_reflect

    @staticmethod
    def reflect_phase_plane(
        k: float,
        target_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        x_rel: np.ndarray,
        y_rel: np.ndarray
    ) -> Tuple[np.ndarray, float, float]:
        """
        Compute reflect phase using plane wave (far-field RX, beam steering).

        Formula: φ_rx(i,j) = -k·(x_i·sin(θ_az) + y_i·sin(θ_el))

        Args:
            k: Wavenumber (2π/λ)
            target_pos: UE position [x_t, y_t, z_t]
            ris_center_pos: RIS center position [x_r, y_r, z_r]
            x_rel: X-coordinates of elements relative to RIS center
            y_rel: Y-coordinates of elements relative to RIS center

        Returns:
            Tuple of (reflect_phase, azimuth_angle_rad, elevation_angle_rad)
        """
        # Direction vector from RIS to target
        v_out = target_pos - ris_center_pos
        norm = np.linalg.norm(v_out)

        if norm < 1e-9:
            # Degenerate case: target at RIS center
            return np.zeros_like(x_rel), 0.0, 0.0

        v_hat = v_out / norm

        # Azimuth and elevation angles
        theta_az = np.arctan2(v_out[1], v_out[0])  # radians
        theta_el = np.arcsin(v_hat[2])             # radians, in [-π/2, π/2]

        # Linear phase for beam steering
        phi_reflect = -k * (x_rel * np.sin(theta_az) + y_rel * np.sin(theta_el))
        return phi_reflect, theta_az, theta_el

    @staticmethod
    def compute_hybrid_pattern(
        source_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        target_pos: np.ndarray,
        frequency: float,
        array_size: int = 16,
        plane_tx: Optional[bool] = None,
        plane_rx: Optional[bool] = None,
        max_angle_deg: Optional[float] = None,
        ris_normal_deg: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Compute hybrid RIS phase pattern with flexible TX/RX wave types.

        Implements Approach B (flag-based) from formula_hybrid.md with automatic
        Fraunhofer boundary selection when plane_tx or plane_rx is None.

        Args:
            source_pos: AP position [x_s, y_s, z_s] (m)
            ris_center_pos: RIS center position [x_r, y_r, z_r] (m)
            target_pos: UE position [x_t, y_t, z_t] (m)
            frequency: Operating frequency (Hz)
            array_size: RIS array size (N for N×N)
            plane_tx: TX wave type - True: plane wave, False: spherical, None: auto-select
            plane_rx: RX wave type - True: plane wave, False: spherical, None: auto-select
            max_angle_deg: Maximum steering angle constraint (hardware FOV limit)
            ris_normal_deg: RIS normal direction in degrees (0° = east)

        Returns:
            Tuple of:
            - phase_pattern: Flattened phase array (N²) in radians [0, 2π)
            - metadata: Dictionary with configuration and geometry info

        Example:
            # Full near-field (spherical TX + RX)
            phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
                ap_pos, ris_pos, ue_pos, 5.8e9, plane_tx=False, plane_rx=False
            )

            # Full far-field (plane TX + RX)
            phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
                ap_pos, ris_pos, ue_pos, 5.8e9, plane_tx=True, plane_rx=True
            )

            # Auto-selection based on distance
            phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
                ap_pos, ris_pos, ue_pos, 5.8e9, plane_tx=None, plane_rx=None
            )
        """
        # Physical parameters
        wavelength = HybridPhaseEngine.C / frequency
        k = 2.0 * np.pi / wavelength
        d = wavelength / 2.0  # Element spacing

        # Generate RIS element grid
        x_rel, y_rel, z_rel = HybridPhaseEngine.generate_ris_grid(array_size, d)

        # Compute distances
        dist_ap_to_ris = np.linalg.norm(source_pos - ris_center_pos)
        dist_ris_to_ue = np.linalg.norm(target_pos - ris_center_pos)

        # Fraunhofer boundary for auto-selection
        r_boundary = HybridPhaseEngine.fraunhofer_boundary(array_size, d, wavelength)

        # Auto-select TX wave type if not specified
        if plane_tx is None:
            plane_tx = dist_ap_to_ris > r_boundary

        # Auto-select RX wave type if not specified
        if plane_rx is None:
            plane_rx = dist_ris_to_ue > r_boundary

        # ===== Compute TX phase component =====
        if plane_tx:
            phi_tx = HybridPhaseEngine.incident_phase_plane(k, source_pos, ris_center_pos, x_rel, y_rel)
            tx_mode = "plane"
        else:
            phi_tx = HybridPhaseEngine.incident_phase_spherical(k, source_pos, ris_center_pos, x_rel, y_rel)
            tx_mode = "spherical"

        # ===== Compute RX phase component =====
        theta_az = None
        theta_el = None
        if plane_rx:
            phi_rx, theta_az, theta_el = HybridPhaseEngine.reflect_phase_plane(k, target_pos, ris_center_pos, x_rel, y_rel)
            rx_mode = "plane"
        else:
            phi_rx = HybridPhaseEngine.reflect_phase_spherical(k, target_pos, ris_center_pos, x_rel, y_rel, z_rel)
            rx_mode = "spherical"

        # ===== Combine TX and RX phases =====
        phi_total = (phi_tx + phi_rx) % (2.0 * np.pi)
        phi_total = np.where(phi_total < 0, phi_total + 2.0 * np.pi, phi_total)

        # ===== Calculate geometry info =====
        # 2D projections for azimuth
        ap_2d = source_pos[:2]
        ris_2d = ris_center_pos[:2]
        ue_2d = target_pos[:2]

        # Azimuth angles
        theta_in_rad = np.arctan2(ap_2d[1] - ris_2d[1], ap_2d[0] - ris_2d[0])
        theta_out_rad = np.arctan2(ue_2d[1] - ris_2d[1], ue_2d[0] - ris_2d[0])

        # Deflection angle
        angle_diff = theta_out_rad - theta_in_rad
        while angle_diff > np.pi:
            angle_diff -= 2 * np.pi
        while angle_diff < -np.pi:
            angle_diff += 2 * np.pi
        deflection_angle = angle_diff

        # Elevation angles
        r_horizontal_ap = np.hypot(ap_2d[0] - ris_2d[0], ap_2d[1] - ris_2d[1])
        r_horizontal_ue = np.hypot(ue_2d[0] - ris_2d[0], ue_2d[1] - ris_2d[1])

        elevation_in = np.arctan2(source_pos[2] - ris_center_pos[2], r_horizontal_ap) if r_horizontal_ap > 1e-9 else 0.0
        elevation_out = np.arctan2(target_pos[2] - ris_center_pos[2], r_horizontal_ue) if r_horizontal_ue > 1e-9 else 0.0

        # ===== Check FOV constraint =====
        fov_clamped = False
        if max_angle_deg is not None:
            max_angle_rad = np.radians(max_angle_deg)
            if deflection_angle > max_angle_rad:
                fov_clamped = True
                logger.warning(
                    f"RIS deflection angle {np.degrees(deflection_angle):.2f}° exceeds hardware FOV limit of ±{max_angle_deg:.0f}°"
                )

        # ===== Prepare metadata =====
        metadata = {
            'tx_mode': tx_mode,
            'rx_mode': rx_mode,
            'plane_tx': plane_tx,
            'plane_rx': plane_rx,
            'wavelength_m': wavelength,
            'wavenumber': k,
            'element_spacing_m': d,
            'array_size': array_size,
            'fraunhofer_boundary_m': r_boundary,
            'dist_ap_to_ris_m': dist_ap_to_ris,
            'dist_ris_to_ue_m': dist_ris_to_ue,
            'deflection_angle_deg': np.degrees(deflection_angle),
            'azimuth_in_deg': np.degrees(theta_in_rad),
            'azimuth_out_deg': np.degrees(theta_out_rad),
            'azimuth_deflection_deg': np.degrees(angle_diff),
            'elevation_in_deg': np.degrees(elevation_in),
            'elevation_out_deg': np.degrees(elevation_out),
            'elevation_deflection_deg': np.degrees(elevation_out - elevation_in),
            'fov_clamped': fov_clamped,
            'max_angle_deg': max_angle_deg,
            'phase_pattern_2d': phi_total,
            'tx_component': phi_tx,
            'rx_component': phi_rx,
        }

        # Add steering angles if plane wave RX was used
        if theta_az is not None:
            metadata['steering_azimuth_rad'] = theta_az
            metadata['steering_elevation_rad'] = theta_el

        return phi_total.flatten(), metadata

    @staticmethod
    def get_mode_description(plane_tx: bool, plane_rx: bool) -> str:
        """Get human-readable description of TX/RX mode combination"""
        tx_desc = "Plane" if plane_tx else "Spherical"
        rx_desc = "Plane (Steering)" if plane_rx else "Spherical (Focusing)"
        return f"{tx_desc} TX + {rx_desc} RX"
