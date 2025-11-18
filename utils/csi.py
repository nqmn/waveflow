"""CSI (Channel State Information) Calculation and Feedback Utilities

Provides unified CSI computation and processing:
- CSI report generation from measurements
- Channel statistics extraction
- CSI feedback formatting
- Channel quality metrics

Integrates with UE receivers, feedback channels, and adaptive control systems.
"""

import numpy as np
from typing import Dict, Optional, List
import time


def generate_csi_report(
    ue_name: str,
    snr_dB: float,
    channel_estimate: Optional[np.ndarray] = None,
    rssi_dBm: Optional[float] = None,
    antenna_gain_dBi: Optional[float] = None,
    noise_figure_dB: Optional[float] = None,
    ris_phases: Optional[np.ndarray] = None,
    pilot_reliability: Optional[float] = None,
    modulation: Optional[str] = None,
    coding_rate: Optional[float] = None,
    timestamp: Optional[float] = None,
) -> Dict:
    """
    Generate a complete CSI (Channel State Information) report.

    This is the primary function for creating CSI feedback that can be sent
    from UE to controller for adaptation and decision making.

    Args:
        ue_name: Source UE node name
        snr_dB: Measured SNR in dB
        channel_estimate: Estimated channel response (complex array, optional)
        rssi_dBm: Received signal strength in dBm (optional)
        antenna_gain_dBi: UE antenna gain in dBi (optional)
        noise_figure_dB: Receiver noise figure in dB (optional)
        ris_phases: RIS phase configuration (optional, for context)
        pilot_reliability: Confidence score (0-1) of pilot-based estimation (optional)
        modulation: Current modulation scheme (optional)
        coding_rate: Current coding rate (optional)
        timestamp: Report timestamp (default: current time)

    Returns:
        Dictionary with complete CSI report
    """
    if timestamp is None:
        timestamp = time.time()

    report = {
        'ue_name': ue_name,
        'timestamp': timestamp,
        'snr_dB': float(snr_dB),
        'snr_linear': 10 ** (float(snr_dB) / 10),  # Convert to linear
    }

    # Optional fields
    if rssi_dBm is not None:
        report['rssi_dBm'] = float(rssi_dBm)

    if antenna_gain_dBi is not None:
        report['antenna_gain_dBi'] = float(antenna_gain_dBi)

    if noise_figure_dB is not None:
        report['noise_figure_dB'] = float(noise_figure_dB)

    if channel_estimate is not None:
        report['channel_estimate'] = np.array(channel_estimate, dtype=complex)
        report['channel_magnitude'] = np.abs(np.array(channel_estimate))
        report['channel_phase'] = np.angle(np.array(channel_estimate))

    if ris_phases is not None:
        report['ris_phases'] = np.array(ris_phases)

    if pilot_reliability is not None:
        report['pilot_reliability'] = float(np.clip(pilot_reliability, 0.0, 1.0))

    if modulation is not None:
        report['modulation'] = str(modulation)

    if coding_rate is not None:
        report['coding_rate'] = float(coding_rate)

    return report


def extract_channel_magnitude(channel_estimate: np.ndarray) -> np.ndarray:
    """
    Extract magnitude response from complex channel estimate.

    Args:
        channel_estimate: Complex channel coefficients

    Returns:
        Magnitude response (linear scale)
    """
    return np.abs(np.array(channel_estimate, dtype=complex))


def extract_channel_phase(channel_estimate: np.ndarray) -> np.ndarray:
    """
    Extract phase response from complex channel estimate.

    Args:
        channel_estimate: Complex channel coefficients

    Returns:
        Phase response in radians
    """
    return np.angle(np.array(channel_estimate, dtype=complex))


def compute_channel_power_delay_profile(
    channel_estimate: np.ndarray,
) -> Dict[str, float]:
    """
    Compute power delay profile statistics from channel estimate.

    Provides insights into multipath dispersion and coherence bandwidth.

    Args:
        channel_estimate: Complex channel coefficients (1D or 2D array)

    Returns:
        Dictionary with PDP statistics
    """
    magnitude = np.abs(np.array(channel_estimate, dtype=complex))

    if magnitude.ndim > 1:
        magnitude = magnitude.flatten()

    power = magnitude ** 2
    total_power = np.sum(power)

    if total_power == 0:
        return {
            'mean_delay': 0.0,
            'rms_delay_spread': 0.0,
            'max_excess_delay': 0.0,
            'coherence_bandwidth_approx_hz': 0.0,
        }

    # Delay bins (normalized to 0-1 for relative comparison)
    delays = np.arange(len(power))

    # Mean delay
    mean_delay = np.sum(delays * power) / total_power

    # RMS delay spread
    rms_delay_spread = np.sqrt(
        np.sum((delays - mean_delay) ** 2 * power) / total_power
    )

    # Max excess delay (where power drops below -30dB of peak)
    peak_power = np.max(power)
    threshold = peak_power / 1000  # -30dB
    max_excess_delay = 0
    for i in range(len(power) - 1, -1, -1):
        if power[i] > threshold:
            max_excess_delay = i
            break

    # Approximate coherence bandwidth: 1 / (5 * rms_delay_spread)
    if rms_delay_spread > 0:
        # This is a rough approximation; actual value depends on sample rate
        coherence_bw = 1.0 / (5 * rms_delay_spread)
    else:
        coherence_bw = 0.0

    return {
        'mean_delay': float(mean_delay),
        'rms_delay_spread': float(rms_delay_spread),
        'max_excess_delay': int(max_excess_delay),
        'coherence_bandwidth_approx_hz': float(coherence_bw),
    }


def compute_channel_condition_number(channel_estimate: np.ndarray) -> float:
    """
    Compute condition number of channel matrix.

    Indicates channel ill-conditioning (high condition number = poor conditioning).
    Useful for predicting equalization difficulty.

    Args:
        channel_estimate: Complex channel coefficients

    Returns:
        Condition number (linear scale)
    """
    h = np.array(channel_estimate, dtype=complex)

    if h.ndim == 1:
        # For 1D, use simple min/max magnitude ratio
        mag = np.abs(h)
        mag = mag[mag > 0]  # Exclude zeros
        if len(mag) < 2:
            return 1.0
        condition = np.max(mag) / np.min(mag)
    else:
        # For 2D matrix, use SVD
        try:
            U, S, Vh = np.linalg.svd(h)
            S = S[S > 0]
            if len(S) < 2:
                return 1.0
            condition = S[0] / S[-1]
        except np.linalg.LinAlgError:
            condition = float('inf')

    return float(condition)


def estimate_channel_capacity_bps_hz(
    snr_dB: float,
    bandwidth_mhz: float = 100.0,
) -> float:
    """
    Estimate Shannon channel capacity.

    Capacity = log2(1 + SNR) bits/second/Hz

    Args:
        snr_dB: SNR in dB
        bandwidth_mhz: Bandwidth in MHz (for reference only, capacity is per Hz)

    Returns:
        Capacity in bits/second/Hz
    """
    snr_linear = 10 ** (float(snr_dB) / 10)
    capacity_bps_hz = np.log2(1 + snr_linear)
    return float(capacity_bps_hz)


def compute_csi_quality_metrics(
    channel_estimate: np.ndarray,
    snr_dB: float,
) -> Dict[str, float]:
    """
    Compute overall CSI quality metrics.

    Provides a comprehensive quality assessment combining channel and SNR info.

    Args:
        channel_estimate: Complex channel coefficients
        snr_dB: Measured SNR in dB

    Returns:
        Dictionary with quality metrics
    """
    mag_response = extract_channel_magnitude(channel_estimate)
    power_response = mag_response ** 2

    # Channel metrics
    avg_power = float(np.mean(power_response))
    peak_power = float(np.max(power_response))
    min_power = float(np.min(power_response))

    # Dynamic range
    if min_power > 0:
        dynamic_range_db = 10 * np.log10(peak_power / min_power)
    else:
        dynamic_range_db = 0.0

    # Overall quality score (0-100)
    # Based on SNR and channel flatness
    snr_score = min(100.0, max(0.0, snr_dB + 20) / 50 * 100)  # -20 to +30 dB mapped to 0-100
    flatness_score = 100.0 / (1.0 + dynamic_range_db / 20)  # Flatter channels score higher

    overall_score = (snr_score * 0.6 + flatness_score * 0.4)

    return {
        'snr_dB': float(snr_dB),
        'avg_channel_power_dBm': 10 * np.log10(avg_power) if avg_power > 0 else -120.0,
        'peak_channel_power_dBm': 10 * np.log10(peak_power) if peak_power > 0 else -120.0,
        'dynamic_range_dB': float(dynamic_range_db),
        'snr_quality_score': float(snr_score),
        'flatness_quality_score': float(flatness_score),
        'overall_quality_score': float(overall_score),
        'estimated_capacity_bps_hz': estimate_channel_capacity_bps_hz(snr_dB),
        'condition_number': compute_channel_condition_number(channel_estimate),
    }


def aggregate_csi_history(
    csi_reports: List[Dict],
    window: Optional[int] = None,
) -> Dict:
    """
    Aggregate statistics over multiple CSI reports.

    Useful for tracking channel trends and quality over time.

    Args:
        csi_reports: List of CSI report dictionaries
        window: Number of recent reports to analyze (None = all)

    Returns:
        Dictionary with aggregated statistics
    """
    if not csi_reports:
        return {
            'num_reports': 0,
            'avg_snr_dB': None,
            'min_snr_dB': None,
            'max_snr_dB': None,
            'snr_variance_dB2': None,
        }

    reports = csi_reports[-window:] if window else csi_reports

    snr_values = [r['snr_dB'] for r in reports if 'snr_dB' in r]

    if not snr_values:
        return {
            'num_reports': len(reports),
            'avg_snr_dB': None,
            'min_snr_dB': None,
            'max_snr_dB': None,
            'snr_variance_dB2': None,
        }

    snr_array = np.array(snr_values)

    return {
        'num_reports': len(reports),
        'avg_snr_dB': float(np.mean(snr_array)),
        'min_snr_dB': float(np.min(snr_array)),
        'max_snr_dB': float(np.max(snr_array)),
        'snr_variance_dB2': float(np.var(snr_array)),
        'snr_std_dB': float(np.std(snr_array)),
        'time_span_seconds': float(
            reports[-1]['timestamp'] - reports[0]['timestamp']
        ) if len(reports) > 1 else 0.0,
    }


def format_csi_report_for_display(csi_report: Dict) -> str:
    """
    Format CSI report as human-readable string.

    Args:
        csi_report: CSI report dictionary

    Returns:
        Formatted string representation
    """
    lines = [
        f"CSI Report for {csi_report.get('ue_name', 'Unknown')}",
        f"  Timestamp: {csi_report.get('timestamp', 'N/A')}",
        f"  SNR: {csi_report.get('snr_dB', 'N/A'):.2f} dB",
    ]

    if 'rssi_dBm' in csi_report:
        lines.append(f"  RSSI: {csi_report['rssi_dBm']:.2f} dBm")

    if 'antenna_gain_dBi' in csi_report:
        lines.append(f"  Antenna Gain: {csi_report['antenna_gain_dBi']:.2f} dBi")

    if 'noise_figure_dB' in csi_report:
        lines.append(f"  Noise Figure: {csi_report['noise_figure_dB']:.2f} dB")

    if 'channel_estimate' in csi_report:
        channel = csi_report['channel_estimate']
        lines.append(f"  Channel Estimate: {len(channel)} coefficients")
        lines.append(
            f"    Magnitude range: {np.min(np.abs(channel)):.4f} to {np.max(np.abs(channel)):.4f}"
        )

    if 'pilot_reliability' in csi_report:
        lines.append(f"  Pilot Reliability: {csi_report['pilot_reliability']:.2f}")

    return '\n'.join(lines)
