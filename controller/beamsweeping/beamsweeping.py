"""
SNR Utility Re-exports (Backward Compatibility)

This module re-exports the compute_snr function from utils.snr for backward
compatibility with code that imports from this module.

New code should import directly from:
- utils.snr (for compute_snr)
"""

# Re-export SNR utility for backward compatibility
from utils.snr import compute_snr

__all__ = [
    'compute_snr',
]
