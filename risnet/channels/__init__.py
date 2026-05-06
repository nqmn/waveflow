"""Channel model interfaces and compatibility adapters."""

from .base import ChannelEvaluation, ChannelModel
from .link_budget import (
    DEFAULT_RIS_LINK_CONFIG,
    LinkBudgetChannel,
    build_link_budget_config,
    build_link_budget_config_from_nodes,
    evaluate_ris_link_from_nodes,
    evaluate_ris_link_metrics,
)

__all__ = [
    "ChannelEvaluation",
    "ChannelModel",
    "DEFAULT_RIS_LINK_CONFIG",
    "LinkBudgetChannel",
    "build_link_budget_config",
    "build_link_budget_config_from_nodes",
    "evaluate_ris_link_from_nodes",
    "evaluate_ris_link_metrics",
]
