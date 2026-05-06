"""Channel model interfaces and compatibility adapters."""

from .base import ChannelEvaluation, ChannelModel
from .link_budget import LinkBudgetChannel

__all__ = [
    "ChannelEvaluation",
    "ChannelModel",
    "LinkBudgetChannel",
]
