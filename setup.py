#!/usr/bin/env python3
"""Legacy setuptools entry point.

The canonical project metadata lives in ``pyproject.toml``. This file keeps
older setuptools workflows working and mirrors the package discovery/console
entry point needed for editable installs.
"""

from setuptools import setup, find_packages

setup(
    packages=find_packages(
        include=[
            "app*",
            "cli*",
            "config*",
            "controller*",
            "core*",
            "risnet*",
            "utils*",
        ],
        exclude=[
            "tests*",
            "examples*",
            "docs*",
        ],
    ),
    entry_points={
        "console_scripts": [
            "risnet=risnet.__main__:main",
        ],
    },
)
