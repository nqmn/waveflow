"""Link-budget channel adapter and compatibility re-exports."""

from __future__ import annotations

from typing import Any

from utils.link_budget import (
    DEFAULT_RIS_LINK_CONFIG,
    build_link_budget_config,
    build_link_budget_config_from_nodes,
    evaluate_ris_link_from_nodes,
    evaluate_ris_link_metrics,
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
