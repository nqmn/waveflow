"""CLI helpers for RISNet."""

from .test_suite import run_testall
from .physics_suite import run_testphysics

__all__ = [
    'run_testall',
    'run_testphysics',
]
