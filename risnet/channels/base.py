"""Channel abstraction interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol


@dataclass(frozen=True)
class ChannelEvaluation:
    """Normalized view of a channel evaluation result."""

    result: Mapping[str, Any]

    @property
    def snr_dB(self) -> float:
        return float(self.result["snr_dB"])

    @property
    def pwr_dBm(self) -> float:
        return float(self.result["pwr_dBm"])

    @property
    def rssi_dBm(self) -> float:
        return float(self.result["rssi_dBm"])

    @property
    def gain_dBi(self) -> float:
        return float(self.result["gain_dBi"])

    @property
    def quant_loss_dB(self) -> float:
        return float(self.result["quant_loss_dB"])


class ChannelModel(Protocol):
    """Protocol for channel models that evaluate an AP-RIS-UE path."""

    def evaluate(
        self,
        network: Any,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        **kwargs: Any,
    ) -> ChannelEvaluation:
        """Evaluate a link and return normalized channel metrics."""
        ...
