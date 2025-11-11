"""Shared helpers for beam sweep algorithms."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

try:  # Centralize waveform availability handling
    from core.signal_processor import (
        SignalConfig,
        SignalLevelLink,
        apply_signal_level_realism,
    )

    WAVEFORM_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    SignalConfig = SignalLevelLink = apply_signal_level_realism = None  # type: ignore
    WAVEFORM_AVAILABLE = False


@dataclass(frozen=True)
class WaveformSettings:
    """Configuration for optional waveform realism."""

    modulation: str = "QPSK"
    symbol_rate: float = 1e6
    sample_rate: float = 10e6
    num_symbols: int = 1000
    pilot_ratio: Optional[float] = None


def compute_specular_angle(ris, ue) -> float:
    """Return the specular UE direction relative to the RIS."""
    ue_vec = ue.pos - ris.pos
    return float(np.degrees(np.arctan2(ue_vec[1], ue_vec[0])))


def create_waveform_link(
    enable_waveform: bool, settings: WaveformSettings
) -> Optional["SignalLevelLink"]:
    """Create a waveform simulator instance when the dependency is available."""
    if not enable_waveform or not WAVEFORM_AVAILABLE:
        return None

    config_kwargs = {
        "modulation": settings.modulation,
        "symbol_rate": settings.symbol_rate,
        "sample_rate": settings.sample_rate,
        "num_symbols": settings.num_symbols,
    }
    if settings.pilot_ratio is not None:
        config_kwargs["pilot_ratio"] = settings.pilot_ratio

    return SignalLevelLink(SignalConfig(**config_kwargs))


def apply_waveform_realism(
    measurement: Dict,
    link_simulator: Optional["SignalLevelLink"],
    *,
    seed: Optional[int] = None,
) -> Tuple[float, Optional[float]]:
    """Convert physics-level measurement into signal-level SNR/SER."""
    if not link_simulator or not apply_signal_level_realism:
        return float(measurement["snr_dB"]), None

    signal_result = apply_signal_level_realism(
        measurement,
        link_simulator,
        seed=seed,
    )
    return float(signal_result["snr_dB"]), signal_result.get("ser_percent")
