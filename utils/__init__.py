"""Project-wide utilities

Provides shared utilities used across the RIS network simulator:
- snr: Advanced SNR calculations with beam alignment and RIS gains
"""

from .snr import compute_snr

__all__ = [
    'compute_snr',
]
