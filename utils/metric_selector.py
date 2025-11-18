"""Metric Selector for Beam Sweep Optimization

Provides abstraction layer for selecting best beam based on different metrics:
- SNR (Signal-to-Noise Ratio) - current default
- RSSI (Received Signal Strength Indicator) - received power
- CSI Quality Score - comprehensive channel quality
- Hybrid metrics - combinations of above

Used by beam sweep algorithms to flexibly select optimal beams.
"""

import numpy as np
from typing import List, Dict, Optional, Callable
from enum import Enum


class MetricType(Enum):
    """Available metrics for beam selection"""
    SNR = "snr"                    # Signal-to-Noise Ratio (dB)
    RSSI = "rssi"                  # Received Signal Strength (dBm)
    CSI_QUALITY = "csi_quality"   # Overall CSI quality score (0-100)
    SER = "ser"                    # Symbol Error Rate (%)
    EVM = "evm"                    # Error Vector Magnitude (%)
    CAPACITY = "capacity"          # Shannon capacity (bps/Hz)
    HYBRID_SNR_RSSI = "hybrid_snr_rssi"  # Weighted average of SNR and RSSI
    CUSTOM = "custom"              # User-provided custom metric


class MetricSelector:
    """
    Selects best beam angle based on configurable metric.

    Provides unified interface for sweep algorithms to evaluate and compare
    different beams using various metrics.

    Example:
        selector = MetricSelector(metric_type=MetricType.SNR)
        best_idx = selector.find_best_index(snr_values)

        selector = MetricSelector(metric_type=MetricType.CSI_QUALITY, threshold=70)
        best_idx = selector.find_best_index(quality_scores)
    """

    def __init__(
        self,
        metric_type: MetricType = MetricType.SNR,
        threshold: Optional[float] = None,
        weights: Optional[Dict[str, float]] = None,
        custom_comparator: Optional[Callable] = None,
    ):
        """
        Initialize metric selector.

        Args:
            metric_type: Which metric to use for selection
            threshold: Minimum acceptable metric value (optional)
            weights: For hybrid metrics, weights for each component
            custom_comparator: User-provided comparison function (for CUSTOM type)
        """
        self.metric_type = metric_type
        self.threshold = threshold
        self.weights = weights or {}
        self.custom_comparator = custom_comparator

        # Validate custom metric
        if metric_type == MetricType.CUSTOM and custom_comparator is None:
            raise ValueError("CUSTOM metric type requires custom_comparator function")

    def find_best_index(self, metric_values: List[float]) -> int:
        """
        Find index of best beam based on metric values.

        Args:
            metric_values: List of metric values for each angle

        Returns:
            Index of best beam
        """
        if not metric_values:
            raise ValueError("No metric values provided")

        metric_array = np.array(metric_values, dtype=float)

        # Filter by threshold if specified
        if self.threshold is not None:
            valid_indices = np.where(metric_array >= self.threshold)[0]
            if len(valid_indices) == 0:
                # No values meet threshold, use best overall
                return int(np.argmax(metric_array))
            metric_array = metric_array[valid_indices]
            best_in_valid = int(np.argmax(metric_array))
            return int(valid_indices[best_in_valid])

        # Return index of maximum metric value
        return int(np.argmax(metric_array))

    def find_best_value(self, metric_values: List[float]) -> float:
        """
        Find best metric value.

        Args:
            metric_values: List of metric values

        Returns:
            Best metric value
        """
        best_idx = self.find_best_index(metric_values)
        return float(metric_values[best_idx])

    def rank_beams(self, metric_values: List[float], top_k: int = 5) -> List[tuple]:
        """
        Rank beams by metric value (descending).

        Args:
            metric_values: List of metric values
            top_k: Number of top beams to return

        Returns:
            List of (index, value) tuples, sorted by value (best first)
        """
        metric_array = np.array(metric_values, dtype=float)
        sorted_indices = np.argsort(-metric_array)  # Descending order

        result = []
        for i in sorted_indices[:top_k]:
            result.append((int(i), float(metric_array[i])))

        return result

    def compare_metrics(self, value1: float, value2: float) -> int:
        """
        Compare two metric values.

        Returns:
            1 if value1 > value2 (value1 is better)
            -1 if value1 < value2 (value2 is better)
            0 if equal
        """
        if value1 > value2:
            return 1
        elif value1 < value2:
            return -1
        else:
            return 0

    def compute_hybrid_metric(
        self,
        snr_db: Optional[float] = None,
        rssi_dbm: Optional[float] = None,
    ) -> float:
        """
        Compute hybrid metric from SNR and RSSI.

        For hybrid metrics, normalizes and combines SNR and RSSI.

        Args:
            snr_db: SNR in dB
            rssi_dbm: RSSI in dBm

        Returns:
            Normalized hybrid metric value
        """
        if self.metric_type != MetricType.HYBRID_SNR_RSSI:
            raise ValueError("Only use compute_hybrid_metric for HYBRID_SNR_RSSI type")

        if snr_db is None or rssi_dbm is None:
            raise ValueError("Both SNR and RSSI required for hybrid metric")

        # Normalize SNR: assume range -10 to +40 dB
        snr_normalized = np.clip((snr_db + 10) / 50, 0, 1)

        # Normalize RSSI: assume range -120 to -30 dBm
        rssi_normalized = np.clip((rssi_dbm + 120) / 90, 0, 1)

        # Get weights (default equal weighting)
        w_snr = self.weights.get('snr', 0.5)
        w_rssi = self.weights.get('rssi', 0.5)
        w_sum = w_snr + w_rssi

        # Weighted combination
        hybrid = (snr_normalized * w_snr + rssi_normalized * w_rssi) / w_sum
        return float(hybrid)

    def get_metric_name(self) -> str:
        """Get human-readable metric name"""
        metric_names = {
            MetricType.SNR: "SNR (dB)",
            MetricType.RSSI: "RSSI (dBm)",
            MetricType.CSI_QUALITY: "CSI Quality Score (0-100)",
            MetricType.SER: "Symbol Error Rate (%)",
            MetricType.EVM: "Error Vector Magnitude (%)",
            MetricType.CAPACITY: "Capacity (bps/Hz)",
            MetricType.HYBRID_SNR_RSSI: "Hybrid SNR+RSSI",
            MetricType.CUSTOM: "Custom Metric",
        }
        return metric_names.get(self.metric_type, "Unknown")

    def get_optimization_direction(self) -> str:
        """
        Get optimization direction for this metric.

        Returns:
            "maximize" for metrics where higher is better
            "minimize" for metrics where lower is better
        """
        # For most metrics, higher is better
        minimize_metrics = [MetricType.SER, MetricType.EVM]

        if self.metric_type in minimize_metrics:
            return "minimize"
        else:
            return "maximize"

    def __repr__(self) -> str:
        return (
            f"MetricSelector(type={self.metric_type.value}, "
            f"threshold={self.threshold}, "
            f"direction={self.get_optimization_direction()})"
        )


def create_metric_selector(metric_str: str) -> MetricSelector:
    """
    Factory function to create metric selector from string.

    Args:
        metric_str: Metric type as string (e.g., "snr", "rssi", "csi")

    Returns:
        MetricSelector instance

    Raises:
        ValueError: If metric_str is not recognized
    """
    metric_map = {
        "snr": MetricType.SNR,
        "rssi": MetricType.RSSI,
        "csi": MetricType.CSI_QUALITY,
        "csi_quality": MetricType.CSI_QUALITY,  # Backward compatibility
        "ser": MetricType.SER,
        "evm": MetricType.EVM,
        "capacity": MetricType.CAPACITY,
        "hybrid": MetricType.HYBRID_SNR_RSSI,
    }

    metric_str = metric_str.lower().strip()
    if metric_str not in metric_map:
        available = ", ".join(metric_map.keys())
        raise ValueError(
            f"Unknown metric: {metric_str}. "
            f"Available: {available}"
        )

    return MetricSelector(metric_type=metric_map[metric_str])


# Convenience instances for common use cases
SNR_SELECTOR = MetricSelector(metric_type=MetricType.SNR)
RSSI_SELECTOR = MetricSelector(metric_type=MetricType.RSSI)
CSI_QUALITY_SELECTOR = MetricSelector(metric_type=MetricType.CSI_QUALITY, threshold=70)
HYBRID_SELECTOR = MetricSelector(
    metric_type=MetricType.HYBRID_SNR_RSSI,
    weights={"snr": 0.6, "rssi": 0.4}  # Prefer SNR slightly
)
