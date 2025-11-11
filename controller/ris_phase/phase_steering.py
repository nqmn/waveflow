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

logger = logging.getLogger(__name__)


class PhaseSteeringEngine:
    """Compute and manage RIS phase steering arrays"""

    @staticmethod
    def linear_steering_phases(
        beam_angle_deg: float,
        ris_position: np.ndarray,
        wavelength: float,
        ris_array_size: int = 16
    ) -> np.ndarray:
        """
        Compute linear steering phases for a given beam angle.

        Uses progressive phase shifts across array elements:
        φ(i) = k * x(i) * sin(θ)
        where k = 2π/λ, x(i) is element position, θ is steering angle

        Args:
            beam_angle_deg: Steering angle in degrees
            ris_position: RIS node position (3D array)
            wavelength: Operating wavelength in meters
            ris_array_size: Array size (N for N×N array)

        Returns:
            Phase array (radians) for all N×N elements
        """
        k = 2 * np.pi / wavelength
        beam_angle_rad = np.radians(beam_angle_deg)

        # Assume ULA along x-axis with λ/2 spacing
        element_spacing = wavelength / 2
        positions = np.arange(ris_array_size) * element_spacing

        # Linear steering: φ = k * x * sin(θ)
        steering_phases = k * positions * np.sin(beam_angle_rad)

        # Wrap to [0, 2π)
        steering_phases = steering_phases % (2 * np.pi)

        # Tile to 2D array (N×N)
        phases_2d = np.tile(steering_phases, (ris_array_size, 1))

        return phases_2d.flatten()

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

        return PhaseSteeringEngine.linear_steering_phases(
            beam_angle_deg=absolute_angle,
            ris_position=np.array([0, 0, 0]),
            wavelength=wavelength,
            ris_array_size=ris_array_size
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
                ris_array_size=self.ris.N
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
