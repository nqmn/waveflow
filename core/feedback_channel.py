"""
Feedback Channel System for UE-to-Controller Communication

Implements a real-time CSI feedback channel that allows UEs to send measured SNR
and channel state information back to the RIS controller for dynamic adaptation.

This enables Option 3: RIS controller queries measured SNR from UE via feedback channel.
"""

from typing import Dict, List, Optional
import time
from dataclasses import dataclass, asdict
from collections import deque


@dataclass
class CSIReport:
    """Channel State Information report from UE"""
    timestamp: float
    sequence_num: int
    ue_name: str
    snr_dB: float
    snr_linear: Optional[float] = None
    rssi_dBm: Optional[float] = None
    channel_estimate: Optional[List[float]] = None
    antenna_gain_dBi: Optional[float] = None
    noise_figure_dB: Optional[float] = None
    pilot_reliability: Optional[float] = None  # 0-1 confidence score
    modulation: Optional[str] = None
    coding_rate: Optional[float] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)


class FeedbackChannel:
    """
    Real-time feedback channel for CSI reports from UE to Controller.

    Acts as a message queue with:
    - Historical storage (circular buffer)
    - Timestamp tracking
    - Sequence numbering for ordering
    - Query interface for controller

    Example usage:
        # Controller creates channel
        channel = FeedbackChannel(ue_name='UE1', ris_name='RIS1', history_size=100)

        # UE pushes reports
        report = CSIReport(timestamp=..., ue_name='UE1', snr_dB=15.5, ...)
        channel.push_report(report)

        # Controller queries
        latest = channel.get_latest_report()
        history = channel.get_history(last_n=10)
        avg_snr = channel.get_average_snr(window=5)
    """

    def __init__(self, ue_name: str, ris_name: str, history_size: int = 100):
        """
        Initialize feedback channel.

        Args:
            ue_name: Source UE node name
            ris_name: Destination RIS node name
            history_size: Maximum number of reports to keep (circular buffer)
        """
        self.ue_name = ue_name
        self.ris_name = ris_name
        self.history_size = history_size

        # Report storage
        self.reports: deque = deque(maxlen=history_size)
        self.sequence_num = 0
        self.created_at = time.time()

        # Statistics
        self.total_reports_received = 0
        self.last_update_time = None

    def push_report(self, report: CSIReport) -> None:
        """
        Push a CSI report to the channel.

        Args:
            report: CSIReport object with measurement data
        """
        # Validate report
        if report.ue_name != self.ue_name:
            raise ValueError(
                f"Report UE mismatch: expected {self.ue_name}, got {report.ue_name}"
            )

        # Update sequence number
        self.sequence_num += 1
        report.sequence_num = self.sequence_num

        # Update timestamp if not set
        if report.timestamp is None or report.timestamp == 0:
            report.timestamp = time.time()

        # Store report
        self.reports.append(report)
        self.total_reports_received += 1
        self.last_update_time = time.time()

    def get_latest_report(self) -> Optional[CSIReport]:
        """
        Get the most recent CSI report.

        Returns:
            Latest CSIReport or None if no reports
        """
        if not self.reports:
            return None
        return self.reports[-1]

    def get_latest_snr_dB(self) -> Optional[float]:
        """
        Get the latest SNR measurement in dB.

        Returns:
            SNR in dB or None if no reports
        """
        latest = self.get_latest_report()
        return latest.snr_dB if latest else None

    def get_latest_snr_linear(self) -> Optional[float]:
        """
        Get the latest SNR in linear scale.

        Returns:
            SNR linear or None if no reports
        """
        latest = self.get_latest_report()
        if not latest:
            return None

        # Convert from dB if linear not available
        if latest.snr_linear is not None:
            return latest.snr_linear
        elif latest.snr_dB is not None:
            return 10 ** (latest.snr_dB / 10)
        return None

    def get_history(self, last_n: Optional[int] = None) -> List[CSIReport]:
        """
        Get historical CSI reports.

        Args:
            last_n: Number of recent reports to return. None = all available.

        Returns:
            List of CSIReport objects
        """
        if last_n is None:
            return list(self.reports)
        return list(self.reports)[-last_n:]

    def get_history_dicts(self, last_n: Optional[int] = None) -> List[Dict]:
        """
        Get history as list of dictionaries.

        Args:
            last_n: Number of recent reports to return

        Returns:
            List of report dictionaries
        """
        return [r.to_dict() for r in self.get_history(last_n)]

    def get_average_snr_dB(self, window: Optional[int] = None) -> Optional[float]:
        """
        Get average SNR over recent reports.

        Args:
            window: Number of recent reports to average. None = all.

        Returns:
            Average SNR in dB
        """
        history = self.get_history(last_n=window)
        if not history:
            return None

        snr_values = [r.snr_dB for r in history if r.snr_dB is not None]
        if not snr_values:
            return None

        return sum(snr_values) / len(snr_values)

    def get_snr_trend(self, window: int = 5) -> Optional[str]:
        """
        Determine if SNR is improving, stable, or degrading.

        Args:
            window: Number of recent reports to analyze

        Returns:
            'improving', 'stable', 'degrading', or None
        """
        history = self.get_history(last_n=window)
        if len(history) < 2:
            return None

        snr_values = [r.snr_dB for r in history if r.snr_dB is not None]
        if len(snr_values) < 2:
            return None

        # Compare first and last values
        snr_change = snr_values[-1] - snr_values[0]

        threshold = 1.0  # dB
        if snr_change > threshold:
            return 'improving'
        elif snr_change < -threshold:
            return 'degrading'
        else:
            return 'stable'

    def get_statistics(self) -> Dict:
        """
        Get channel statistics.

        Returns:
            Dictionary with statistics
        """
        history = self.get_history()
        if not history:
            return {
                'ue_name': self.ue_name,
                'ris_name': self.ris_name,
                'total_reports': 0,
                'latest_snr_dB': None,
                'average_snr_dB': None,
                'status': 'no_reports'
            }

        snr_values = [r.snr_dB for r in history if r.snr_dB is not None]

        return {
            'ue_name': self.ue_name,
            'ris_name': self.ris_name,
            'total_reports': self.total_reports_received,
            'stored_reports': len(history),
            'latest_snr_dB': self.get_latest_snr_dB(),
            'average_snr_dB': self.get_average_snr_dB(),
            'min_snr_dB': min(snr_values) if snr_values else None,
            'max_snr_dB': max(snr_values) if snr_values else None,
            'snr_trend': self.get_snr_trend(),
            'last_update': self.last_update_time,
            'uptime': time.time() - self.created_at,
            'status': 'active'
        }

    def clear_history(self) -> None:
        """Clear all stored reports but keep channel active"""
        self.reports.clear()

    def reset(self) -> None:
        """Reset channel to initial state"""
        self.clear_history()
        self.sequence_num = 0
        self.total_reports_received = 0
        self.last_update_time = None
        self.created_at = time.time()


class FeedbackChannelManager:
    """
    Manages multiple feedback channels for a network.

    Provides:
    - Channel creation and lifecycle management
    - Channel discovery and querying
    - Network-wide feedback statistics
    """

    def __init__(self):
        """Initialize channel manager"""
        self.channels: Dict[str, FeedbackChannel] = {}
        self.created_at = time.time()

    def create_channel(self, ue_name: str, ris_name: str,
                      history_size: int = 100) -> FeedbackChannel:
        """
        Create or get a feedback channel.

        Args:
            ue_name: Source UE name
            ris_name: Destination RIS name
            history_size: Maximum reports to keep

        Returns:
            FeedbackChannel instance
        """
        channel_key = f"{ue_name}→{ris_name}"

        if channel_key not in self.channels:
            self.channels[channel_key] = FeedbackChannel(
                ue_name=ue_name,
                ris_name=ris_name,
                history_size=history_size
            )

        return self.channels[channel_key]

    def get_channel(self, ue_name: str, ris_name: str) -> Optional[FeedbackChannel]:
        """
        Get an existing feedback channel.

        Args:
            ue_name: Source UE name
            ris_name: Destination RIS name

        Returns:
            FeedbackChannel or None if not found
        """
        channel_key = f"{ue_name}→{ris_name}"
        return self.channels.get(channel_key)

    def has_channel(self, ue_name: str, ris_name: str) -> bool:
        """Check if channel exists"""
        channel_key = f"{ue_name}→{ris_name}"
        return channel_key in self.channels

    def list_channels(self) -> Dict[str, Dict]:
        """
        Get all channels with their statistics.

        Returns:
            Dictionary of channel_key -> statistics
        """
        return {
            key: channel.get_statistics()
            for key, channel in self.channels.items()
        }

    def get_network_statistics(self) -> Dict:
        """
        Get network-wide feedback statistics.

        Returns:
            Dictionary with aggregated statistics
        """
        if not self.channels:
            return {
                'total_channels': 0,
                'total_reports': 0,
                'status': 'no_channels'
            }

        total_reports = sum(c.total_reports_received for c in self.channels.values())

        # Calculate average SNR across all channels
        all_snr_values = []
        for channel in self.channels.values():
            history = channel.get_history()
            all_snr_values.extend([r.snr_dB for r in history if r.snr_dB is not None])

        avg_snr = sum(all_snr_values) / len(all_snr_values) if all_snr_values else None

        return {
            'total_channels': len(self.channels),
            'total_reports': total_reports,
            'average_snr_dB': avg_snr,
            'uptime': time.time() - self.created_at,
            'status': 'active'
        }

    def reset_all(self) -> None:
        """Reset all channels"""
        for channel in self.channels.values():
            channel.reset()

    def clear_all_history(self) -> None:
        """Clear history on all channels"""
        for channel in self.channels.values():
            channel.clear_history()
