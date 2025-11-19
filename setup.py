#!/usr/bin/env python3
"""
Minimal setup.py for PyPI compatibility.
Modern Python packaging should use pyproject.toml instead.
This file is kept for backward compatibility.

LATEST FEATURES (v1.0+):
- Array Factor Integration: Physics-based SNR calculations for RIS beam sweeps
  * Replaces binary beam_hits_ue cutoff with realistic sidelobe patterns
  * Supports element tapering for sidelobe control
  * Fully documented with test suite and examples
  * See: ARRAY_FACTOR_INTEGRATION.md, test_array_factor_integration.py
"""

from setuptools import setup, find_packages

setup()
