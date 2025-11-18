"""Project-wide utilities

Provides shared utilities used across the RIS network simulator:
- snr: Advanced SNR calculations with beam alignment and RIS gains
- rssi: Received Signal Strength Indicator calculations and conversions
- csi: Channel State Information generation and analysis
"""

from .snr import compute_snr
from .rssi import (
    compute_rssi_dBm,
    compute_rssi_linear,
    rssi_from_snr,
    rssi_from_noise_figure,
    convert_rssi_dBm_to_linear,
    convert_rssi_linear_to_dBm,
    rssi_to_power_level,
    compute_snr_from_rssi_and_noise,
)
from .csi import (
    generate_csi_report,
    extract_channel_magnitude,
    extract_channel_phase,
    compute_channel_power_delay_profile,
    compute_channel_condition_number,
    estimate_channel_capacity_bps_hz,
    compute_csi_quality_metrics,
    aggregate_csi_history,
    format_csi_report_for_display,
)
from .metric_selector import (
    MetricType,
    MetricSelector,
    create_metric_selector,
    SNR_SELECTOR,
    RSSI_SELECTOR,
    CSI_QUALITY_SELECTOR,
    HYBRID_SELECTOR,
)

__all__ = [
    'compute_snr',
    'compute_rssi_dBm',
    'compute_rssi_linear',
    'rssi_from_snr',
    'rssi_from_noise_figure',
    'convert_rssi_dBm_to_linear',
    'convert_rssi_linear_to_dBm',
    'rssi_to_power_level',
    'compute_snr_from_rssi_and_noise',
    'generate_csi_report',
    'extract_channel_magnitude',
    'extract_channel_phase',
    'compute_channel_power_delay_profile',
    'compute_channel_condition_number',
    'estimate_channel_capacity_bps_hz',
    'compute_csi_quality_metrics',
    'aggregate_csi_history',
    'format_csi_report_for_display',
    'MetricType',
    'MetricSelector',
    'create_metric_selector',
    'SNR_SELECTOR',
    'RSSI_SELECTOR',
    'CSI_QUALITY_SELECTOR',
    'HYBRID_SELECTOR',
]
