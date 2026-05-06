#!/usr/bin/env python3
"""
Example 15: Streaming a Real Video Bitstream Through a Configured RIS Link

This script now reuses the shared helpers in cli/video_stream.py so that the
interactive CLI command offers the exact same workflow.
"""

from pathlib import Path

from core import RISNetwork
from cli.video_stream import VideoStreamConfig, run_video_stream_workflow


def build_network() -> RISNetwork:
    """Set up the canonical AP→RIS→UE topology used throughout the docs."""
    network = RISNetwork()
    network.add_ap("ap1", 0, 0, 3, power_dBm=30, freq=28e9, bandwidth_MHz=100)
    network.add_ris("ris1", 40, 0, 6, N=16, bits=1, freq=28e9, max_angle_deg=90)
    network.add_ue("ue1", 90, 10, 1.5)
    return network


def run_video_stream_demo():
    repo_root = Path(__file__).parent.parent.parent
    video_path = repo_root / "streaming" / "video.mp4"

    network = build_network()
    network.connect("ap1", "ris1", "ue1")
    config = VideoStreamConfig(video_path=video_path)
    run_video_stream_workflow(network, "ap1", "ris1", "ue1", config)


if __name__ == "__main__":
    run_video_stream_demo()
