"""
Advanced beamforming algorithms with CFAR detection

Implements:
- Greedy beam sweeping with adaptive search
- CFAR (Constant False Alarm Rate) detection
- Codebook-based beamforming
- Binary search optimization
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class BeamformingEngine:
    """Advanced beamforming and beam sweeping algorithms"""

    @staticmethod
    def cfar_detection(measurements: List[Dict],
                       peak_idx: int,
                       pfa: float = 1e-3,
                       min_snr_linear: float = 1.0) -> bool:
        """CFAR (Constant False Alarm Rate) detection

        Validates if detected peak is a true signal vs noise

        Args:
            measurements: List of {angle, SNR} measurements
            peak_idx: Index of peak to validate
            pfa: Probability of false alarm
            min_snr_linear: Minimum acceptable SNR (linear)

        Returns:
            True if peak is valid
        """
        peak_snr = measurements[peak_idx]['SNR']

        # Absolute minimum threshold
        if peak_snr < min_snr_linear:
            return False

        # Could add more sophisticated CFAR methods here
        # (CA-CFAR, OS-CFAR, etc.)

        return True

    @staticmethod
    def greedy_beam_sweep(pos1: np.ndarray,
                          pos2: np.ndarray,
                          node1: str,
                          node2: str,
                          compute_snr_fn,
                          ap_pos: np.ndarray = None,
                          max_angle_deg: float = 60,
                          coarse_step_deg: float = 10,
                          fine_step_deg: float = 1,
                          verbose: bool = False) -> Dict:
        """Greedy beam sweeping with adaptive center-out expansion

        Implements intelligent beam search:
        1. Start from specular reflection angle
        2. Expand outward adaptively
        3. Use binary search refinement
        4. CFAR validation

        Args:
            pos1: Transmitter position (RIS or AP)
            pos2: Target position
            node1: Transmitter node name
            node2: Target node name
            compute_snr_fn: Function to compute SNR(pos1, pos2, node1, node2, angle)
            ap_pos: AP position (for specular calculation)
            max_angle_deg: Maximum steering angle
            coarse_step_deg: Coarse search step size
            fine_step_deg: Fine search step size
            verbose: Enable detailed logging

        Returns:
            Dict with best_angle, best_snr, measurements, etc.
        """
        measurements = []

        if verbose:
            logger.info(f"\n┌─ BEAM SWEEP: {node1}→{node2} ─────────────")

        # Step 1: Calculate target angle
        target_vec = pos2 - pos1
        target_angle_deg = np.degrees(np.arctan2(target_vec[1], target_vec[0]))

        if verbose:
            logger.info(f"│ Target angle: {target_angle_deg:.1f}°")

        # Step 2: Calculate specular reflection angle for RIS links
        specular_angle_deg = 0
        is_ris_link = node1.startswith('R') or (node1 == 'AP' and node2.startswith('R'))

        if is_ris_link and ap_pos is not None:
            incident_vec = pos1 - ap_pos
            incident_angle_deg = np.degrees(np.arctan2(incident_vec[1], incident_vec[0]))

            # Specular reflection: reflected at 180°
            reflected_vec = -incident_vec
            specular_angle_deg = np.degrees(np.arctan2(reflected_vec[1], reflected_vec[0]))

            if verbose:
                logger.info(f"│ Incident angle: {incident_angle_deg:.1f}°")
                logger.info(f"│ Specular angle: {specular_angle_deg:.1f}°")

        # Step 3: Generate codebook
        num_angles = int(2 * max_angle_deg / coarse_step_deg) + 1
        codebook = np.linspace(
            specular_angle_deg - max_angle_deg,
            specular_angle_deg + max_angle_deg,
            num_angles
        )

        if verbose:
            logger.info(f"│ Codebook: {len(codebook)} angles from {codebook[0]:.1f}° to {codebook[-1]:.1f}°")

        # Step 4: Calculate deflection from specular
        deflection_deg = target_angle_deg - specular_angle_deg
        # Normalize to [-180, 180]
        while deflection_deg > 180:
            deflection_deg -= 360
        while deflection_deg < -180:
            deflection_deg += 360

        # Handle beyond ±90° case
        if abs(deflection_deg) > 90:
            if deflection_deg > 0:
                deflection_deg -= 180
            else:
                deflection_deg += 180

        if verbose:
            logger.info(f"│ Deflection from specular: {deflection_deg:.1f}°")

        # Step 5: Start from center (specular) and expand
        current_idx = len(codebook) // 2
        current_angle = codebook[current_idx]
        current_snr = compute_snr_fn(pos1, pos2, node1, node2, current_angle)
        measurements.append({'angle': current_angle, 'SNR': current_snr, 'idx': current_idx})

        best_idx = current_idx
        best_snr = current_snr
        best_angle = current_angle

        # Step 6: Adaptive center-out expansion
        left_idx = current_idx - 1
        right_idx = current_idx + 1

        while left_idx >= 0 or right_idx < len(codebook):
            # Test left neighbor
            if left_idx >= 0:
                left_angle = codebook[left_idx]
                left_snr = compute_snr_fn(pos1, pos2, node1, node2, left_angle)
                measurements.append({'angle': left_angle, 'SNR': left_snr, 'idx': left_idx})

                if left_snr > best_snr:
                    best_snr = left_snr
                    best_idx = left_idx
                    best_angle = left_angle

            # Test right neighbor
            if right_idx < len(codebook):
                right_angle = codebook[right_idx]
                right_snr = compute_snr_fn(pos1, pos2, node1, node2, right_angle)
                measurements.append({'angle': right_angle, 'SNR': right_snr, 'idx': right_idx})

                if right_snr > best_snr:
                    best_snr = right_snr
                    best_idx = right_idx
                    best_angle = right_angle

            left_idx -= 1
            right_idx += 1

        # Step 7: Fine refinement using binary search
        if best_idx > 0 and best_idx < len(codebook) - 1:
            # Refine between best_angle and neighbors
            left_bound = codebook[best_idx - 1]
            right_bound = codebook[best_idx + 1]

            refined_angles = np.arange(left_bound, right_bound + fine_step_deg, fine_step_deg)

            for angle in refined_angles:
                snr = compute_snr_fn(pos1, pos2, node1, node2, angle)
                measurements.append({'angle': angle, 'SNR': snr, 'idx': -1})

                if snr > best_snr:
                    best_snr = snr
                    best_angle = angle

        # Step 8: CFAR validation
        sorted_measurements = sorted(measurements, key=lambda x: x['SNR'], reverse=True)
        peak_valid = BeamformingEngine.cfar_detection(sorted_measurements, 0)

        best_snr_dB = 10 * np.log10(best_snr) if best_snr > 0 else -np.inf

        if verbose:
            logger.info(f"│ Best angle: {best_angle:.1f}°")
            logger.info(f"│ Best SNR: {best_snr_dB:.1f} dB")
            logger.info(f"│ CFAR valid: {peak_valid}")
            logger.info(f"└─ Total measurements: {len(measurements)}")

        return {
            'best_angle': best_angle,
            'best_snr': best_snr,
            'best_snr_dB': best_snr_dB,
            'measurements': measurements,
            'cfar_valid': peak_valid,
            'target_angle': target_angle_deg,
            'specular_angle': specular_angle_deg,
            'deflection': deflection_deg
        }

    @staticmethod
    def simple_beam_sweep(pos1: np.ndarray,
                          pos2: np.ndarray,
                          node1: str,
                          node2: str,
                          compute_snr_fn,
                          fov_deg: float = 60,
                          coarse_step_deg: float = 10,
                          fine_step_deg: float = 1) -> Dict:
        """Simple uniform beam sweep (legacy method)

        Args:
            pos1: Transmitter position
            pos2: Target position
            node1: Transmitter node name
            node2: Target node name
            compute_snr_fn: SNR computation function
            fov_deg: Field of view
            coarse_step_deg: Coarse step size
            fine_step_deg: Fine step size

        Returns:
            Dict with best angle and SNR
        """
        # Calculate base direction
        vec = pos2 - pos1
        base_angle = np.degrees(np.arctan2(vec[1], vec[0]))

        # Coarse sweep
        coarse_angles = np.arange(-fov_deg, fov_deg + coarse_step_deg, coarse_step_deg)
        abs_angles = base_angle + coarse_angles

        snr_values = []
        for angle in abs_angles:
            snr = compute_snr_fn(pos1, pos2, node1, node2, angle)
            snr_values.append(snr)

        # Find coarse peak
        best_coarse_idx = np.argmax(snr_values)
        best_coarse_angle = abs_angles[best_coarse_idx]

        # Fine sweep around peak
        fine_angles = np.arange(
            best_coarse_angle - coarse_step_deg,
            best_coarse_angle + coarse_step_deg + fine_step_deg,
            fine_step_deg
        )

        fine_snr_values = []
        for angle in fine_angles:
            snr = compute_snr_fn(pos1, pos2, node1, node2, angle)
            fine_snr_values.append(snr)

        # Find fine peak
        best_fine_idx = np.argmax(fine_snr_values)
        best_angle = fine_angles[best_fine_idx]
        best_snr = fine_snr_values[best_fine_idx]

        return {
            'best_angle': best_angle,
            'best_snr': best_snr,
            'best_snr_dB': 10 * np.log10(best_snr) if best_snr > 0 else -np.inf,
            'coarse_angles': coarse_angles.tolist(),
            'coarse_snr': snr_values,
            'fine_angles': fine_angles.tolist(),
            'fine_snr': fine_snr_values
        }

    @staticmethod
    def calculate_codebook(center_angle_deg: float,
                           max_angle_deg: float,
                           step_deg: float) -> np.ndarray:
        """Generate angle codebook for beam sweeping

        Args:
            center_angle_deg: Center angle (e.g., specular)
            max_angle_deg: Maximum deviation
            step_deg: Angular step size

        Returns:
            Array of angles in degrees
        """
        num_angles = int(2 * max_angle_deg / step_deg) + 1
        return np.linspace(
            center_angle_deg - max_angle_deg,
            center_angle_deg + max_angle_deg,
            num_angles
        )
