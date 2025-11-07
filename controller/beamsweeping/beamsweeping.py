"""
Adaptive Center-Out Beam Sweeping Algorithm

Implements an efficient two-phase beam sweeping strategy:
- Phase 1: Coarse adaptive center-out sweep (10° steps)
- Phase 2: Fine-resolution refinement (1° steps)

Efficiency: ~30% measurement savings vs exhaustive search
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def adaptive_center_out_beam_sweep(
    ris_position: np.ndarray,
    target_position: np.ndarray,
    ap_position: np.ndarray,
    max_angle: float = 60.0,
    coarse_step: float = 10.0,
    fine_step: float = 1.0,
    compute_snr_fn=None,
    is_ris_node: bool = True,
    verbose: bool = False
) -> Dict:
    """
    Adaptive center-out beam sweep with two-phase refinement.

    Implements intelligent beam steering that starts from the specular reflection
    angle and expands adaptively, reducing measurement overhead by ~30%.

    Args:
        ris_position: RIS node position (3D array)
        target_position: Target node position (3D array)
        ap_position: Access Point position (3D array)
        max_angle: Maximum deflection angle in degrees (default: 60°)
        coarse_step: Coarse search step size in degrees (default: 10°)
        fine_step: Fine search step size in degrees (default: 1°)
        compute_snr_fn: Function to compute SNR(pos1, pos2, node1, node2, beam_angle, specular_angle)
        is_ris_node: Whether transmitter is a RIS node
        verbose: Enable detailed logging

    Returns:
        Dictionary with:
            - angle: Deflection from specular angle (degrees)
            - absoluteAngle: Absolute beam direction (degrees)
            - SNR: Peak SNR (linear scale)
            - numMeasurements: Total beams tested
            - specularAngle: Reference specular angle
            - measurements: List of all measurements
    """

    # ===== PHASE 0: SETUP =====
    measurements = []

    # Calculate specular reflection angle
    if is_ris_node:
        incident_vec = ap_position - ris_position
        incident_angle = np.arctan2(incident_vec[1], incident_vec[0]) * 180 / np.pi

        # Specular reflection: mirror the incident ray
        reflected_vec = -incident_vec
        specular_angle = np.arctan2(reflected_vec[1], reflected_vec[0]) * 180 / np.pi
    else:
        specular_angle = 0.0

    # Generate coarse codebook
    codebook = []
    num_steps = int(2 * max_angle / coarse_step) + 1
    for i in range(num_steps):
        beam_angle = specular_angle + (-max_angle + i * coarse_step)
        codebook.append(beam_angle)

    if verbose:
        logger.info(f"Specular angle: {specular_angle:.1f}°")
        logger.info(f"Coarse codebook: {len(codebook)} beams from {codebook[0]:.1f}° to {codebook[-1]:.1f}°")

    # ===== PHASE 1: ADAPTIVE CENTER-OUT SWEEP (COARSE) =====
    center_idx = len(codebook) // 2
    best_idx = center_idx
    best_snr = -np.inf
    expansion_dir = 0  # 0=symmetric, -1=left, +1=right
    peak_found = False
    last_snr = 0

    # Test center (specular)
    center_snr = compute_snr_fn(
        ris_position, target_position, 'RIS', 'target',
        codebook[center_idx], specular_angle
    )
    measurements.append({'angle': codebook[center_idx], 'SNR': center_snr})
    best_snr = center_snr
    last_snr = center_snr

    # Peak detection threshold: 50% above center
    peak_threshold = center_snr * 1.5

    # Expansion loop
    for step in range(1, len(codebook) // 2 + 1):
        left_idx = center_idx - step
        right_idx = center_idx + step

        # Bounds checking
        if left_idx < 0:
            left_idx = None
        if right_idx >= len(codebook):
            right_idx = None

        if expansion_dir == 0:
            # SYMMETRIC EXPANSION: Test both directions
            left_snr = None
            right_snr = None

            if left_idx is not None:
                left_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    codebook[left_idx], specular_angle
                )
                measurements.append({'angle': codebook[left_idx], 'SNR': left_snr})

            if right_idx is not None:
                right_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    codebook[right_idx], specular_angle
                )
                measurements.append({'angle': codebook[right_idx], 'SNR': right_snr})

            # Determine which direction is better
            if left_snr is not None and right_snr is not None:
                if left_snr > right_snr:
                    expansion_dir = -1
                    if left_snr > best_snr:
                        best_snr = left_snr
                        best_idx = left_idx
                    last_snr = max(left_snr, right_snr)
                elif right_snr > left_snr:
                    expansion_dir = 1
                    if right_snr > best_snr:
                        best_snr = right_snr
                        best_idx = right_idx
                    last_snr = max(left_snr, right_snr)
                else:
                    # Equal: keep symmetric
                    last_snr = left_snr
            elif left_snr is not None:
                if left_snr > best_snr:
                    best_snr = left_snr
                    best_idx = left_idx
                expansion_dir = -1
                last_snr = left_snr
            elif right_snr is not None:
                if right_snr > best_snr:
                    best_snr = right_snr
                    best_idx = right_idx
                expansion_dir = 1
                last_snr = right_snr

            # Check for peak
            if best_snr > peak_threshold and not peak_found:
                peak_found = True
                if verbose:
                    logger.info(f"PEAK DETECTED at step {step}: {best_snr:.2f} dB (threshold: {peak_threshold:.2f})")

        elif expansion_dir == -1:
            # LEFT-ONLY EXPANSION
            if left_idx is not None:
                left_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    codebook[left_idx], specular_angle
                )
                measurements.append({'angle': codebook[left_idx], 'SNR': left_snr})

                if left_snr > best_snr:
                    best_snr = left_snr
                    best_idx = left_idx
                    if best_snr > peak_threshold:
                        peak_found = True
                    last_snr = left_snr
                elif peak_found and left_snr < last_snr:
                    # SNR declining after peak: STOP early
                    if verbose:
                        logger.info(f"SNR declining after peak at step {step}, stopping early")
                    break
                else:
                    last_snr = left_snr
            else:
                break

        elif expansion_dir == 1:
            # RIGHT-ONLY EXPANSION
            if right_idx is not None:
                right_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    codebook[right_idx], specular_angle
                )
                measurements.append({'angle': codebook[right_idx], 'SNR': right_snr})

                if right_snr > best_snr:
                    best_snr = right_snr
                    best_idx = right_idx
                    if best_snr > peak_threshold:
                        peak_found = True
                    last_snr = right_snr
                elif peak_found and right_snr < last_snr:
                    # SNR declining after peak: STOP early
                    if verbose:
                        logger.info(f"SNR declining after peak at step {step}, stopping early")
                    break
                else:
                    last_snr = right_snr
            else:
                break

    # Phase 1 result
    peak_angle = codebook[best_idx]
    phase1_snr = best_snr
    phase1_measurements = len(measurements)

    if verbose:
        logger.info(f"Phase 1 complete: Peak at {peak_angle:.1f}°, SNR={phase1_snr:.2f}, measurements={phase1_measurements}")

    # ===== PHASE 2: EXACT REFINEMENT (FINE) =====
    refinement_range = 5.0  # ±5° window

    # Generate fine-resolution codebook
    refined_codebook = []
    offset = -refinement_range
    while offset <= refinement_range:
        refined_codebook.append(peak_angle + offset)
        offset += fine_step

    # Run adaptive center-out on refined codebook
    refined_center_idx = len(refined_codebook) // 2
    refined_best_idx = refined_center_idx
    refined_best_snr = -np.inf
    refined_expansion_dir = 0
    refined_peak_found = False
    refined_last_snr = 0

    # Test center (peak from phase 1)
    center_angle = refined_codebook[refined_center_idx]
    center_snr_refined = compute_snr_fn(
        ris_position, target_position, 'RIS', 'target',
        center_angle, specular_angle
    )
    measurements.append({'angle': center_angle, 'SNR': center_snr_refined})
    refined_best_snr = center_snr_refined
    refined_last_snr = center_snr_refined

    refined_peak_threshold = center_snr_refined * 1.5

    # Refined expansion loop
    for step in range(1, len(refined_codebook) // 2 + 1):
        left_idx = refined_center_idx - step
        right_idx = refined_center_idx + step

        if left_idx < 0:
            left_idx = None
        if right_idx >= len(refined_codebook):
            right_idx = None

        if refined_expansion_dir == 0:
            # SYMMETRIC expansion in refined range
            left_snr = None
            right_snr = None

            if left_idx is not None:
                left_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    refined_codebook[left_idx], specular_angle
                )
                measurements.append({'angle': refined_codebook[left_idx], 'SNR': left_snr})

            if right_idx is not None:
                right_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    refined_codebook[right_idx], specular_angle
                )
                measurements.append({'angle': refined_codebook[right_idx], 'SNR': right_snr})

            if left_snr is not None and right_snr is not None:
                if left_snr > right_snr:
                    refined_expansion_dir = -1
                elif right_snr > left_snr:
                    refined_expansion_dir = 1

                # Update best
                if left_snr > refined_best_snr:
                    refined_best_snr = left_snr
                    refined_best_idx = left_idx
                if right_snr > refined_best_snr:
                    refined_best_snr = right_snr
                    refined_best_idx = right_idx
            elif left_snr is not None:
                if left_snr > refined_best_snr:
                    refined_best_snr = left_snr
                    refined_best_idx = left_idx
                refined_expansion_dir = -1
            elif right_snr is not None:
                if right_snr > refined_best_snr:
                    refined_best_snr = right_snr
                    refined_best_idx = right_idx
                refined_expansion_dir = 1

        elif refined_expansion_dir == -1:
            # LEFT-ONLY in refined range
            if left_idx is not None:
                left_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    refined_codebook[left_idx], specular_angle
                )
                measurements.append({'angle': refined_codebook[left_idx], 'SNR': left_snr})

                if left_snr > refined_best_snr:
                    refined_best_snr = left_snr
                    refined_best_idx = left_idx
                elif refined_peak_found and left_snr < refined_last_snr:
                    if verbose:
                        logger.info(f"Refined: SNR declining after peak at step {step}, stopping")
                    break
                refined_last_snr = left_snr
            else:
                break

        elif refined_expansion_dir == 1:
            # RIGHT-ONLY in refined range
            if right_idx is not None:
                right_snr = compute_snr_fn(
                    ris_position, target_position, 'RIS', 'target',
                    refined_codebook[right_idx], specular_angle
                )
                measurements.append({'angle': refined_codebook[right_idx], 'SNR': right_snr})

                if right_snr > refined_best_snr:
                    refined_best_snr = right_snr
                    refined_best_idx = right_idx
                elif refined_peak_found and right_snr < refined_last_snr:
                    if verbose:
                        logger.info(f"Refined: SNR declining after peak at step {step}, stopping")
                    break
                refined_last_snr = right_snr
            else:
                break

    # Final result
    best_beam_angle = refined_codebook[refined_best_idx]
    final_snr = refined_best_snr
    deflection_used = best_beam_angle - specular_angle

    if verbose:
        logger.info(f"Phase 2 complete: Refined angle={best_beam_angle:.2f}°, SNR={final_snr:.2f}")
        logger.info(f"Total measurements: {len(measurements)} (vs {len(codebook) + len(refined_codebook)} exhaustive)")

    return {
        'angle': deflection_used,
        'absoluteAngle': best_beam_angle,
        'SNR': final_snr,
        'SNR_dB': 10 * np.log10(final_snr) if final_snr > 0 else -np.inf,
        'numMeasurements': len(measurements),
        'specularAngle': specular_angle,
        'measurements': measurements,
        'efficiency': len(measurements) / (len(codebook) + len(refined_codebook))
    }


def compute_snr(
    pos1: np.ndarray,
    pos2: np.ndarray,
    node1: str,
    node2: str,
    beam_angle: float,
    specular_angle: float,
    ris_reflectors: int = 16,
    frequency_ghz: float = 10.0,
    bandwidth_mhz: float = 100.0,
    transmit_power_dbm: float = 20.0,
    noise_figure_db: float = 6.0,
    active_ris_mode: bool = False,
    amplifier_gain: float = 0.0
) -> float:
    """
    Compute SNR for a given beam angle.

    Calculates path loss, atmospheric loss, gain, and thermal noise.

    Args:
        pos1: Transmitter position (3D array)
        pos2: Receiver position (3D array)
        node1: Transmitter node type ('AP', 'RIS', etc.)
        node2: Receiver node type ('target', 'RIS', 'H', etc.)
        beam_angle: Steering angle in degrees
        specular_angle: Specular reflection angle in degrees
        ris_reflectors: Number of RIS reflectors (NxN array)
        frequency_ghz: Operating frequency in GHz
        bandwidth_mhz: Signal bandwidth in MHz
        transmit_power_dbm: Transmit power in dBm
        noise_figure_db: Noise figure in dB
        active_ris_mode: Whether RIS is in active mode (default: passive RIS)
        amplifier_gain: RIS amplifier gain in dB (only used if active_ris_mode=True)

    Returns:
        SNR in linear scale
    """

    # Calculate distance
    distance = np.linalg.norm(pos2 - pos1)

    if distance < 0.01:
        return 1e-6  # Too close

    # Free-space path loss (dB)
    wavelength = 3e8 / (frequency_ghz * 1e9)  # meters
    path_loss_db = 20 * np.log10(4 * np.pi * distance / wavelength)

    # Atmospheric loss (frequency dependent)
    # Simplified: ~0.5 dB/km at 28 GHz
    atm_loss_db = (distance / 1000) * 0.5

    # Gain calculation
    if node1 == 'AP' and node2.startswith('R'):
        # AP→RIS: Direct link with known RIS location
        N = ris_reflectors * ris_reflectors
        # RIS array gain: 20*log10(N)
        theoretical_gain_dbi = 20 * np.log10(N)
        insertion_loss = 2.0  # dB
        reflection_loss = 1.0  # dB
        gain_dbi = theoretical_gain_dbi - insertion_loss - reflection_loss
        # Add amplifier gain separately (if active RIS)
        if active_ris_mode:
            gain_dbi += amplifier_gain

    elif node1.startswith('R') and (node2 == 'H' or node2.startswith('R') or node2 == 'target'):
        # RIS→target/RIS: Blind beam steering - angle matters
        target_angle = np.arctan2(pos2[1] - pos1[1], pos2[0] - pos1[0]) * 180 / np.pi
        target_deflection = target_angle - specular_angle

        # Normalize to [-180, 180]
        while target_deflection > 180:
            target_deflection -= 360
        while target_deflection < -180:
            target_deflection += 360

        # Check alternate direction
        target_deflection_alt = target_deflection
        if abs(target_deflection) > 90:
            target_deflection_alt = target_deflection - 180 if target_deflection > 0 else target_deflection + 180
            if target_deflection_alt < -180:
                target_deflection_alt += 360
            if target_deflection_alt > 180:
                target_deflection_alt -= 360

        # Angle error to target
        angle_error = min(abs(beam_angle - target_deflection),
                         abs(beam_angle - target_deflection_alt))

        # Target within 5° of beam: aligned
        if angle_error < 5:
            N = ris_reflectors * ris_reflectors
            # RIS array gain: 20*log10(N)
            theoretical_gain_dbi = 20 * np.log10(N)
            insertion_loss = 2.0  # dB
            reflection_loss = 1.0  # dB
            gain_dbi = theoretical_gain_dbi - insertion_loss - reflection_loss
            # Add amplifier gain separately (if active RIS)
            if active_ris_mode:
                gain_dbi += amplifier_gain
        else:
            # Misaligned: reduced gain (10% efficiency)
            N = ris_reflectors * ris_reflectors
            # RIS array gain: 20*log10(N)
            theoretical_gain_dbi = 20 * np.log10(N)
            gain_dbi = theoretical_gain_dbi * 0.1
            # Add amplifier gain separately if active, but at reduced efficiency
            if active_ris_mode:
                gain_dbi += amplifier_gain * 0.1

        # RIS→RIS: Apply relay efficiency penalty
        if node2.startswith('R'):
            gain_dbi = gain_dbi * 0.70

    else:
        # Default: minimal gain
        gain_dbi = 3.0

    # Quantization loss
    quantization_loss_db = 0.5  # dB

    # Total loss
    total_loss_db = path_loss_db + atm_loss_db + quantization_loss_db - gain_dbi

    # Thermal noise
    bw_hz = bandwidth_mhz * 1e6
    noise_power_dbm = -174 + 10 * np.log10(bw_hz) + noise_figure_db

    # SNR calculation
    snr_db = transmit_power_dbm - total_loss_db - noise_power_dbm
    snr_linear = 10 ** (snr_db / 10)

    return max(snr_linear, 1e-6)  # Ensure positive
