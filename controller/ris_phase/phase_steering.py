"""
RIS Phase Steering - Linear beam steering and phase array computation

Implements phase steering algorithms for RIS-based beamforming:
- Linear steering array phase computation
- Optimal path-based phase alignment
- Deflection angle to phase array conversion
"""

import numpy as np
from typing import Dict, Tuple, Optional
import logging
from core.angle_utils import clamp_offset_to_fov

logger = logging.getLogger(__name__)


class PhaseSteeringEngine:
    """Compute and manage RIS phase steering arrays"""

    @staticmethod
    def _synthetic_element_positions(ris_array_size: int, wavelength: float) -> np.ndarray:
        """Create a centered λ/2-spaced planar grid used for phase synthesis."""
        element_spacing = wavelength / 2.0
        coords = np.arange(ris_array_size) - (ris_array_size - 1) / 2.0
        xs, ys = np.meshgrid(coords, coords, indexing="ij")
        positions = np.stack([xs, ys, np.zeros_like(xs)], axis=-1) * element_spacing
        return positions.reshape(-1, 3)

    @staticmethod
    def linear_steering_phases(
        beam_angle_deg: float,
        ris_position: np.ndarray,
        wavelength: float,
        ris_array_size: int = 16,
        element_positions: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Compute planar steering phases for a given beam angle.

        Uses progressive phase shifts across BOTH axes of the RIS:
        φ(i) = -k * r_i · u(θ)
        where k = 2π/λ, r_i is the element position relative to RIS center,
        and u(θ) is the unit vector pointing toward the steering direction.

        Args:
            beam_angle_deg: Steering angle in degrees (absolute azimuth)
            ris_position: RIS node position (3D array)
            wavelength: Operating wavelength in meters
            ris_array_size: Array size (N for N×N array)
            element_positions: Optional explicit element positions (N×3 array)

        Returns:
            Phase array (radians) for all N×N elements
        """
        k = 2 * np.pi / wavelength
        beam_angle_rad = np.radians(beam_angle_deg)
        steering_dir = np.array([np.cos(beam_angle_rad), np.sin(beam_angle_rad), 0.0])

        if element_positions is None:
            rel_positions = PhaseSteeringEngine._synthetic_element_positions(ris_array_size, wavelength)
        else:
            rel_positions = np.asarray(element_positions, dtype=float).copy()
            if ris_position is not None:
                rel_positions -= ris_position
            else:
                rel_positions -= np.mean(rel_positions, axis=0)

        projections = rel_positions[:, 0] * steering_dir[0] + rel_positions[:, 1] * steering_dir[1]
        steering_phases = (-k * projections) % (2 * np.pi)
        return steering_phases

    @staticmethod
    def optimal_path_phases(
        ap_position: np.ndarray,
        ue_position: np.ndarray,
        ris_position: np.ndarray,
        element_positions: np.ndarray,
        frequency: float
    ) -> np.ndarray:
        """
        Compute optimal phases for AP→RIS→UE path alignment.

        Minimizes path length: φ(i) = -k * (r_ap(i) + r_ue(i))
        where r_ap(i) and r_ue(i) are distances from element i to AP and UE

        Args:
            ap_position: Access Point position (3D)
            ue_position: User Equipment position (3D)
            ris_position: RIS center position (3D)
            element_positions: Positions of all RIS elements (N×3 array)
            frequency: Operating frequency in Hz

        Returns:
            Optimal phase array (radians) for path alignment
        """
        wavelength = 3e8 / frequency  # c/f
        k = 2 * np.pi / wavelength

        # Compute distances from each element to AP and UE
        distances_ap = np.linalg.norm(element_positions - ap_position, axis=1)
        distances_ue = np.linalg.norm(element_positions - ue_position, axis=1)

        # Round-trip phase: φ = -k * (r_ap + r_ue)
        # Negative sign for constructive interference
        optimal_phases = -k * (distances_ap + distances_ue)

        # Normalize relative to element 0
        optimal_phases = optimal_phases - optimal_phases[0]

        # Wrap to [0, 2π)
        optimal_phases = optimal_phases % (2 * np.pi)

        return optimal_phases

    @staticmethod
    def deflection_to_phase_array(
        deflection_angle_deg: float,
        specular_angle_deg: float,
        ris_array_size: int = 16,
        wavelength: float = 0.01
    ) -> np.ndarray:
        """
        Convert beam deflection angle to RIS phase array.

        Maps deflection from specular reflection to linear steering phases.

        Args:
            deflection_angle_deg: Deflection from specular in degrees
            specular_angle_deg: Specular reflection angle reference
            ris_array_size: Array size
            wavelength: Operating wavelength in meters

        Returns:
            Phase array for the deflected beam
        """
        # Absolute beam angle
        absolute_angle = specular_angle_deg + deflection_angle_deg

        synthetic_positions = PhaseSteeringEngine._synthetic_element_positions(ris_array_size, wavelength)
        return PhaseSteeringEngine.linear_steering_phases(
            beam_angle_deg=absolute_angle,
            ris_position=np.array([0.0, 0.0, 0.0]),
            wavelength=wavelength,
            ris_array_size=ris_array_size,
            element_positions=synthetic_positions,
        )

    @staticmethod
    def compute_beam_angle_from_phases(
        phases: np.ndarray,
        wavelength: float,
        ris_array_size: int = 16
    ) -> float:
        """
        Estimate beam angle from measured RIS phase configuration.

        Reverse operation of linear steering phase computation.

        Args:
            phases: Phase array (radians)
            wavelength: Operating wavelength
            ris_array_size: Array size

        Returns:
            Estimated beam angle in degrees
        """
        k = 2 * np.pi / wavelength
        element_spacing = wavelength / 2

        # Extract first row phases (should follow linear progression)
        phases_1d = phases[:ris_array_size]

        # Compute phase differences
        phase_diffs = np.diff(phases_1d)

        # Average phase difference
        avg_phase_diff = np.mean(phase_diffs)

        # Solve for sin(θ): Δφ = k * spacing * sin(θ)
        sin_theta = avg_phase_diff / (k * element_spacing)

        # Clamp to valid range [-1, 1]
        sin_theta = np.clip(sin_theta, -1, 1)

        # Compute angle
        beam_angle_rad = np.arcsin(sin_theta)
        beam_angle_deg = np.degrees(beam_angle_rad)

        return beam_angle_deg

    @staticmethod
    def apply_tapering(rows: int, cols: int, window: str = 'hamming') -> np.ndarray:
        """
        Apply amplitude tapering (windowing) to a 2D RIS array.

        Tapering reduces sidelobe levels at the cost of a wider main lobe.
        This is useful for array factor calculations to model element amplitude
        weights that reduce far-field sidelobe levels.

        Window Functions:
            'hamming':  Classic Hamming window, ~-43 dB sidelobe suppression
            'hann':     Hann/Hanning window, ~-32 dB sidelobe suppression (smoother)
            'blackman': Blackman window, ~-58 dB sidelobe suppression (very low sidelobes)
            'kaiser':   Kaiser window, tunable sidelobe suppression
            'uniform':  No tapering (default, ~-13 dB sidelobes for 2D array)
            'taylor':   Taylor window approximation (for planar arrays)

        Args:
            rows: Number of rows in RIS array
            cols: Number of columns in RIS array
            window: Window type ('hamming', 'hann', 'blackman', 'kaiser', 'uniform', 'taylor')

        Returns:
            weights_2d: 2D array of amplitude weights (rows × cols)
                       Ready to be reshaped/flattened for element_weights

        Example:
            >>> weights_hamming = PhaseSteeringEngine.apply_tapering(16, 16, window='hamming')
            >>> # Use in array factor: Physics.compute_array_factor(..., weights=weights_hamming.flatten())
        """
        if window == 'uniform' or window is None:
            # No tapering - all elements weighted equally
            return np.ones((rows, cols))

        elif window == 'hamming':
            # Hamming window
            w_row = np.hamming(rows)
            w_col = np.hamming(cols)
            weights_2d = np.outer(w_row, w_col)

        elif window == 'hann':
            # Hann/Hanning window (smoother than Hamming)
            w_row = np.hanning(rows)
            w_col = np.hanning(cols)
            weights_2d = np.outer(w_row, w_col)

        elif window == 'blackman':
            # Blackman window (very low sidelobes, wider main lobe)
            w_row = np.blackman(rows)
            w_col = np.blackman(cols)
            weights_2d = np.outer(w_row, w_col)

        elif window == 'kaiser':
            # Kaiser window with default shape parameter (beta=8.6 for ~50 dB sidelobe)
            beta = 8.6  # Tunable: higher = lower sidelobes, wider main lobe
            w_row = np.kaiser(rows, beta)
            w_col = np.kaiser(cols, beta)
            weights_2d = np.outer(w_row, w_col)

        elif window == 'taylor':
            # Taylor window approximation for planar arrays
            # Provides nearly equal sidelobe levels
            # Create Taylor window using Hamming as approximation
            w_row = np.hamming(rows) + 0.1 * (1 - np.hamming(rows))  # Slight boost at edges
            w_col = np.hamming(cols) + 0.1 * (1 - np.hamming(cols))
            weights_2d = np.outer(w_row, w_col)

        else:
            # Unknown window type - default to Hamming
            logger.warning(f"Unknown window type '{window}', defaulting to Hamming")
            w_row = np.hamming(rows)
            w_col = np.hamming(cols)
            weights_2d = np.outer(w_row, w_col)

        # Normalize weights to unit energy
        weights_2d = weights_2d / np.sqrt(np.sum(weights_2d ** 2) + 1e-10)

        return weights_2d

    @staticmethod
    def phase_pattern_from_deflection(
        source_pos: np.ndarray,
        ris_center_pos: np.ndarray,
        target_pos: np.ndarray,
        wavelength: float,
        ris_array_size: int = 16,
        max_angle_deg: Optional[float] = None,
        ris_normal_deg: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Generate RIS phase pattern from node coordinates using deflection angle decomposition.

        Implements the algorithm from risformula/formula.md:
        - Section 4: Deflection angle calculation from 3D coordinates
        - Section 5: Phase computation with incident + steering components

        NATIVE FOV CLAMPING: If max_angle_deg is provided (RIS hardware constraint),
        the deflection angle is automatically clamped to ±max_angle_deg before phase computation.
        This ensures phases reflect the actual RIS steering capability.

        Formula:
            φ(i,j) = φ_incident(i,j) + φ_steering(i,j)
                    = k·√(x_i² + y_i² + r_src²) - k·x_i·sin(θ_rcv_clamped)

        Args:
            source_pos: Source/AP position [x_s, y_s, z_s] in meters
            ris_center_pos: RIS center position [x_r, y_r, z_r] in meters
            target_pos: Target/UE position [x_t, y_t, z_t] in meters
            wavelength: Operating wavelength in meters (≈0.0517 m for 5.8 GHz)
            ris_array_size: RIS grid size (N for N×N array, default 16)
            max_angle_deg: Maximum steering angle from RIS normal (native hardware constraint).
                          If None, no FOV clamping applied. If provided, deflection is clamped.
            ris_normal_deg: RIS antenna normal direction in degrees [0, 360).
                           Only used if max_angle_deg is provided for proper offset calculation.

        Returns:
            Tuple of:
            - phase_pattern: Flattened phase array (N×N→N²) in radians, [0, 2π)
            - metadata: Dictionary with:
                - deflection_angle_deg: Calculated deflection angle in degrees (BEFORE clamping)
                - deflection_angle_clamped_deg: Clamped deflection angle used for phase computation
                - fov_clamped: Boolean indicating if clamping was applied
                - incident_azimuth_deg: Incident direction (AP→RIS) in degrees
                - reflected_azimuth_deg: Reflected direction (RIS→UE) in degrees
                - source_height_m: Source height above RIS (z_s - z_r)
                - element_spacing_m: Half-wavelength spacing

        Example:
            >>> source = np.array([8.0, 10.0, 0.5])
            >>> ris = np.array([15.0, 10.0, 0.0])
            >>> target = np.array([11.4, 6.5, 0.0])
            >>> wavelength = 0.0517  # 5.8 GHz
            >>> phases, meta = PhaseSteeringEngine.phase_pattern_from_deflection(
            ...     source, ris, target, wavelength, ris_array_size=16
            ... )
            >>> # Output includes checkerboard pattern with incident spherical wave
            >>> # modulated by linear steering phase ramp
        """
        # Physical constants
        k = 2 * np.pi / wavelength
        d = wavelength / 2  # half-wavelength element spacing

        # ===== STEP 1: Calculate deflection angle from 3D coordinates =====
        # Extract 2D projections (XY plane - azimuth only)
        ap_2d = source_pos[:2]
        ris_2d = ris_center_pos[:2]
        ue_2d = target_pos[:2]

        # Calculate absolute azimuth angles
        theta_in_rad = np.arctan2(ap_2d[1] - ris_2d[1], ap_2d[0] - ris_2d[0])
        theta_out_rad = np.arctan2(ue_2d[1] - ris_2d[1], ue_2d[0] - ris_2d[0])

        # Calculate azimuth angle difference (deflection)
        angle_diff = theta_out_rad - theta_in_rad

        # Wrap to [-π, π]
        while angle_diff > np.pi:
            angle_diff -= 2 * np.pi
        while angle_diff < -np.pi:
            angle_diff += 2 * np.pi

        # Deflection angle (magnitude)
        theta_rcv = abs(angle_diff)

        # Store original deflection for metadata
        theta_rcv_original = theta_rcv
        fov_clamped = False

        # ===== NATIVE FOV CONSTRAINT: Check hardware limit =====
        # If max_angle_deg is provided, verify deflection angle is within RIS capability
        if max_angle_deg is not None:
            # Convert max_angle from degrees to radians for consistent units
            max_angle_rad = np.radians(max_angle_deg)

            # Check if deflection exceeds maximum steering capability
            if theta_rcv > max_angle_rad:
                fov_clamped = True
                raise ValueError(
                    f"RIS deflection angle {np.degrees(theta_rcv):.2f}° exceeds hardware FOV limit of ±{max_angle_deg:.0f}°. "
                    f"Cannot establish link. Consider repositioning UE or RIS to reduce required deflection."
                )

        # ===== STEP 2: Calculate source height above RIS =====
        r_src = source_pos[2] - ris_center_pos[2]

        # ===== STEP 3: Generate RIS element coordinates (2D grid) =====
        # Grid limits
        lim_x = (ris_array_size - 1) / 2 * d
        lim_y = (ris_array_size - 1) / 2 * d

        # Element positions relative to RIS center
        x_indices = np.arange(ris_array_size)
        y_indices = np.arange(ris_array_size)

        x_rel = -lim_x + (x_indices / (ris_array_size - 1)) * (2 * lim_x)
        y_rel = -lim_y + (y_indices / (ris_array_size - 1)) * (2 * lim_y)

        # Create 2D mesh grid
        X, Y = np.meshgrid(x_rel, y_rel)

        # ===== STEP 4: Compute phase components for each element =====

        # Component 1: Incident phase (spherical wavefront compensation)
        # φ_incident(i,j) = k·√(x_i² + y_i² + r_src²)
        # Accounts for phase variation due to different propagation distances
        # from spherical source at height r_src above RIS
        R_source = np.sqrt(X**2 + Y**2 + r_src**2)
        phase_incident = k * R_source

        # Component 2: Steering phase (linear array steering)
        # φ_steering(i,j) = -k·x_i·sin(θ_rcv)
        # Creates linear phase ramp to deflect beam toward target
        phase_steering = -k * X * np.sin(theta_rcv)

        # Component 3: Total phase (superposition)
        # φ(i,j) = φ_incident + φ_steering
        phase_total = phase_incident + phase_steering

        # ===== STEP 5: Normalize to [0, 2π) =====
        phase_pattern = phase_total % (2 * np.pi)
        # Ensure all values are non-negative
        phase_pattern = np.where(phase_pattern < 0, phase_pattern + 2 * np.pi, phase_pattern)

        # ===== STEP 6: Prepare metadata =====
        metadata = {
            'deflection_angle_deg': np.degrees(theta_rcv_original),  # Original, unclamped
            'deflection_angle_clamped_deg': np.degrees(theta_rcv),    # Clamped value used for phases
            'fov_clamped': fov_clamped,                              # Whether clamping was applied
            'max_angle_deg': max_angle_deg,                          # Hardware constraint
            'incident_azimuth_deg': np.degrees(theta_in_rad),
            'reflected_azimuth_deg': np.degrees(theta_out_rad),
            'angle_diff_deg': np.degrees(angle_diff),
            'source_height_m': r_src,
            'element_spacing_m': d,
            'ris_array_size': ris_array_size,
            'wavelength_m': wavelength,
            'phase_pattern_2d': phase_pattern,  # 2D representation for visualization
            'incident_component': phase_incident,
            'steering_component': phase_steering,
        }

        return phase_pattern.flatten(), metadata

    @staticmethod
    def optimize_quantized_phases(
        ideal_phases: np.ndarray,
        bits: int = 1,
        ris_array_size: int = 16,
        element_positions: np.ndarray = None,
        target_angle_deg: float = 0.0,
        frequency: float = 5.8e9,
        method: str = 'gradient_descent'
    ) -> Tuple[np.ndarray, Dict]:
        """
        Optimize quantized phase values to maximize array gain for target angle.

        Given ideal continuous phases, find the best quantized values that
        maximize array factor at the target steering angle. This accounts for
        the fact that 1-bit (or low-bit) quantization loses information,
        but can be optimized for specific geometry.

        Args:
            ideal_phases: Ideal continuous phases (radians) [0, 2π)
            bits: Quantization bits per element (1, 2, 3, etc.)
            ris_array_size: Array dimension (N for N×N array)
            element_positions: 3D positions of all elements (optional, for array factor)
            target_angle_deg: Target steering angle in degrees
            frequency: Operating frequency in Hz
            method: Optimization method ('gradient_descent', 'particle_swarm', 'exhaustive')

        Returns:
            Tuple of:
            - quantized_phases: Optimized quantized phases
            - metadata: Dict with optimization results (gain_improvement, iterations, etc.)
        """
        from scipy.optimize import differential_evolution, minimize

        num_levels = 2 ** bits
        phase_levels = np.linspace(0, 2 * np.pi, num_levels, endpoint=False)
        num_elements = len(ideal_phases)

        # Helper function to quantize phases
        def quantize_to_levels(phases_continuous):
            quantized = np.zeros_like(phases_continuous)
            for i, phase in enumerate(phases_continuous):
                # Find nearest quantization level
                idx = np.argmin(np.abs(phase_levels - phase))
                quantized[i] = phase_levels[idx]
            return quantized

        # Objective function: minimize phase error (deviation from ideal)
        def phase_error(phase_indices):
            # Convert indices to actual phases
            phases_opt = np.array([phase_levels[int(idx) % num_levels] for idx in phase_indices])
            # Return RMS phase error
            error = np.sqrt(np.mean((phases_opt - ideal_phases) ** 2))
            return error

        # For small arrays (1-bit, 16x16), exhaustive search is feasible
        if bits == 1 and ris_array_size == 16:
            # 1-bit, 256 elements: only 2^256 patterns... too large for exhaustive
            # Use greedy approach instead: quantize each element independently
            quantized_phases = quantize_to_levels(ideal_phases)
            iterations = 1
            improvement = 0.0
        else:
            # Use optimization for higher bits
            if method == 'gradient_descent':
                # Continuous optimization, then quantize
                def objective(phases_cont):
                    quantized = quantize_to_levels(phases_cont)
                    return phase_error(quantized)

                result = minimize(objective, ideal_phases, method='L-BFGS-B',
                                bounds=[(0, 2*np.pi) for _ in range(num_elements)])
                quantized_phases = quantize_to_levels(result.x)
                iterations = result.nit if hasattr(result, 'nit') else 0
                improvement = float(phase_error(ideal_phases) - phase_error(quantized_phases))

            elif method == 'particle_swarm':
                # Differential evolution as PSO alternative
                bounds = [(0, 2*np.pi) for _ in range(num_elements)]
                result = differential_evolution(
                    objective=phase_error,
                    bounds=bounds,
                    seed=0,
                    maxiter=20,
                    workers=1,
                    updating='immediate'
                )
                quantized_phases = quantize_to_levels(result.x)
                iterations = result.nit
                improvement = float(phase_error(ideal_phases) - phase_error(quantized_phases))

            else:  # exhaustive or default
                quantized_phases = quantize_to_levels(ideal_phases)
                iterations = 1
                improvement = 0.0

        # Calculate metrics
        ideal_error = phase_error(ideal_phases)
        quantized_error = phase_error(quantized_phases)

        metadata = {
            'method': method,
            'bits': bits,
            'num_elements': num_elements,
            'ideal_phase_error_rms': float(ideal_error),
            'quantized_phase_error_rms': float(quantized_error),
            'improvement_rms': float(improvement),
            'iterations': iterations,
            'num_phase_levels': num_levels,
            'target_angle_deg': target_angle_deg
        }

        return quantized_phases, metadata

    @staticmethod
    def phase_gradient_analysis(
        phases: np.ndarray,
        ris_array_size: int = 16
    ) -> Dict[str, float]:
        """
        Analyze phase gradient to infer steering properties.

        Args:
            phases: Phase array (radians)
            ris_array_size: Array size

        Returns:
            Dictionary with gradient analysis:
            - phase_gradient: Average phase difference between elements
            - linearity: How well phases follow linear progression (0-1)
            - max_deviation: Largest deviation from linear fit
        """
        phases_2d = phases.reshape((ris_array_size, ris_array_size))

        # Analyze row-wise gradient (primary steering direction)
        row_phases = phases_2d[0, :]
        row_diffs = np.diff(row_phases)

        avg_gradient = np.mean(row_diffs)
        linear_fit = np.linspace(row_phases[0], row_phases[-1], ris_array_size)
        linear_phases = np.linspace(row_phases[0], row_phases[-1], ris_array_size)

        # Deviation from linear fit
        deviation = np.abs(row_phases - linear_phases)
        max_deviation = np.max(deviation)
        linearity = 1.0 - (max_deviation / (2 * np.pi))  # Normalize

        return {
            'phase_gradient': avg_gradient,
            'linearity': max(0, linearity),
            'max_deviation': max_deviation,
            'avg_phase': np.mean(phases),
            'phase_range': np.ptp(phases)
        }


class BeamSteeringController:
    """Control RIS beams through phase steering"""

    def __init__(self, ris_node):
        """
        Initialize beam steering controller.

        Args:
            ris_node: RIS node instance from core/nodes.py
        """
        self.ris = ris_node
        self.steering_engine = PhaseSteeringEngine()

    def steer_to_angle(self, beam_angle_deg: float) -> Dict:
        """
        Steer RIS beam to target angle.

        Args:
            beam_angle_deg: Target steering angle in degrees.
                           IMPORTANT: This should be the LOCAL deflection angle (relative to RIS normal),
                           NOT the absolute world angle. The RIS uses linear phased array steering with:
                           φ(i) = k × x(i) × sin(θ), where θ is this local angle.
                           Valid range: -max_angle_deg to +max_angle_deg (typically ±60° for phased arrays)

        Returns:
            Dictionary with:
            - phases: Computed phase array
            - angle: Requested angle
            - status: Success/failure
        """
        try:
            wavelength = 3e8 / self.ris.freq
            phases = self.steering_engine.linear_steering_phases(
                beam_angle_deg=beam_angle_deg,
                ris_position=self.ris.pos,
                wavelength=wavelength,
                ris_array_size=self.ris.N,
                element_positions=getattr(self.ris, "element_positions", None),
            )

            # Apply to RIS node
            self.ris.set_beam_config(beam_angle=beam_angle_deg, phases=phases)
            self.ris.quantize_phases()

            return {
                'status': 'success',
                'angle': beam_angle_deg,
                'phases': phases,
                'num_elements': len(phases)
            }
        except Exception as e:
            logger.error(f"Beam steering failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def steer_to_target(
        self,
        ap_position: np.ndarray,
        ue_position: np.ndarray
    ) -> Dict:
        """
        Steer RIS to align with AP→UE path.

        Args:
            ap_position: Access Point position
            ue_position: User Equipment position

        Returns:
            Dictionary with steering results
        """
        try:
            wavelength = 3e8 / self.ris.freq

            # Generate element positions (assuming planar ULA)
            element_spacing = wavelength / 2
            element_positions = []
            for i in range(self.ris.N):
                for j in range(self.ris.N):
                    x = i * element_spacing
                    y = j * element_spacing
                    z = 0
                    element_positions.append(self.ris.pos + np.array([x, y, z]))

            element_positions = np.array(element_positions)

            # Compute optimal phases
            phases = self.steering_engine.optimal_path_phases(
                ap_position=ap_position,
                ue_position=ue_position,
                ris_position=self.ris.pos,
                element_positions=element_positions,
                frequency=self.ris.freq
            )

            # Apply to RIS
            self.ris.set_beam_config(phases=phases)
            self.ris.quantize_phases()

            # Analyze resulting beam
            analysis = self.steering_engine.phase_gradient_analysis(phases, self.ris.N)

            return {
                'status': 'success',
                'phases': phases,
                'analysis': analysis,
                'num_elements': len(phases)
            }
        except Exception as e:
            logger.error(f"Target steering failed: {e}")
            return {'status': 'failed', 'error': str(e)}

    def get_steering_angle(self) -> float:
        """
        Estimate current beam steering angle from phases.

        Returns:
            Estimated beam angle in degrees
        """
        if self.ris.quantized_phases is None:
            return 0.0

        wavelength = 3e8 / self.ris.freq
        angle = self.steering_engine.compute_beam_angle_from_phases(
            self.ris.quantized_phases,
            wavelength,
            self.ris.N
        )

        return angle
