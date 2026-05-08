"""LightRIS channel adapter and native-engine helper exports."""

from __future__ import annotations

from typing import Any

from utils.lightris import (
    DEFAULT_LIGHTRIS_CONFIG,
    build_lightris_config as _build_lightris_config,
    build_lightris_config_from_nodes as _build_lightris_config_from_nodes,
    evaluate_lightris_from_nodes as _evaluate_lightris_from_nodes,
    evaluate_lightris_metrics as _evaluate_lightris_metrics,
)

from .base import ChannelEvaluation


class LightRISChannel:
    """Preferred native lightweight channel adapter for Waveflow/RISNet.

    It delegates to ``RISNetwork.connect`` while preserving the current native
    physics, waveform, metadata, and validation behavior under the official
    `lightris` engine name.
    """

    channel_model_name = "lightris"

    def __init__(self, *, store_in_active_links: bool = False):
        self.store_in_active_links = store_in_active_links

    def evaluate(
        self,
        network: Any,
        ap_name: str,
        ris_name: str,
        ue_name: str,
        **kwargs: Any,
    ) -> ChannelEvaluation:
        """Evaluate the AP-RIS-UE link through the existing network facade."""
        connect_kwargs = dict(kwargs)
        connect_kwargs.setdefault("store_in_active_links", self.store_in_active_links)
        connect_kwargs.setdefault("channel_model", self.channel_model_name)

        result = network.connect(ap_name, ris_name, ue_name, **connect_kwargs)
        return ChannelEvaluation(result=result)


def build_lightris_config(*args, **kwargs):
    """Build the official LightRIS helper configuration."""
    return _build_lightris_config(*args, **kwargs)


def build_lightris_config_from_nodes(*args, **kwargs):
    """Build the official LightRIS helper configuration from repository nodes."""
    return _build_lightris_config_from_nodes(*args, **kwargs)


def evaluate_lightris_from_nodes(*args, **kwargs):
    """Evaluate LightRIS helper metrics from repository node objects."""
    return _evaluate_lightris_from_nodes(*args, **kwargs)


def evaluate_lightris_metrics(*args, **kwargs):
    """Evaluate LightRIS helper metrics from explicit geometry/config inputs."""
    return _evaluate_lightris_metrics(*args, **kwargs)

__all__ = [
    "DEFAULT_LIGHTRIS_CONFIG",
    "LightRISChannel",
    "build_lightris_config",
    "build_lightris_config_from_nodes",
    "evaluate_lightris_from_nodes",
    "evaluate_lightris_metrics",
]
