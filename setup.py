#!/usr/bin/env python3
"""Legacy setuptools entry point.

The canonical project metadata lives in ``pyproject.toml``. This file keeps
older setuptools workflows working and mirrors the package discovery/console
entry point needed for editable installs.
"""

from setuptools import setup, find_packages

BASE_REQUIRES = [
    "numpy",
    "scipy",
    "pyyaml",
]

EXTRAS_REQUIRE = {
    "web": [
        "flask",
        "waitress",
    ],
    "vision": [
        "opencv-python",
    ],
    "optimization": [
        "cvxpy",
        "scs",
    ],
    "plot": [
        "matplotlib",
    ],
    "ml": [
        "torch>=1.9.0",
        "scikit-learn",
    ],
    "dev": [
        "pytest>=6.0",
        "pytest-cov",
        "black",
        "flake8",
        "matplotlib",
        "mypy",
    ],
}
EXTRAS_REQUIRE["all"] = sorted(
    {dependency for dependencies in EXTRAS_REQUIRE.values() for dependency in dependencies}
)

setup(
    install_requires=BASE_REQUIRES,
    extras_require=EXTRAS_REQUIRE,
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
