#!/usr/bin/env python3
"""
Example: Streaming a Real Video Bitstream Through a Configured RIS Link

Pipeline:
1. Instantiate AP/RIS/UE nodes and attach the waveform controller.
2. Run the system-level connect + waveform beam sweep to pick the steering angle.
3. Program the RIS with the quantized phase pattern derived from the geometry.
4. Use waveform-level metrics as a baseline, then stream real video bits through the link.
5. Report chunk-level SNR/SER/throughput and compare to the RIS-assisted baseline.
"""

import math
import sys
from pathlib import Path
from typing import Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core import RISNetwork, Physics  # noqa: E402
from core.signal_processor import (  # noqa: E402
    SignalConfig,
    Modulator,
    RealChannel,
    RealSignalMeasurer,
)
from controller.waveform_controller import WaveformController  # noqa: E402


class VideoBitstreamSource:
    """Reads a video file and exposes it as a bitstream."""

    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        self.data = path.read_bytes()
        self.cursor = 0

    def has_data(self) -> bool:
        return self.cursor < len(self.data)

    def next_bits(self, target_bits: int) -> Tuple[np.ndarray, int]:
        """Return a bit array of length `target_bits` (zero padded if needed)."""
        if not self.has_data():
            return np.zeros(target_bits, dtype=np.uint8), 0

        num_bytes = math.ceil(target_bits / 8)
        chunk = self.data[self.cursor : self.cursor + num_bytes]
        self.cursor += len(chunk)

        payload_bits = len(chunk) * 8
        bit_array = np.unpackbits(np.frombuffer(chunk, dtype=np.uint8))

        if len(bit_array) < target_bits:
            bit_array = np.pad(bit_array, (0, target_bits - len(bit_array)))
        else:
            bit_array = bit_array[:target_bits]

        return bit_array.astype(np.uint8), payload_bits


def estimate_ris_path_loss(ap, ris, ue) -> float:
    """Rough AP→RIS→UE path loss with RIS gain compensation."""
    d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
    d_ris_ue = np.linalg.norm(ue.pos - ris.pos)
    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)
    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)
    ris_gain = 20 * np.log10(ris.N)  # Ideal array gain
    return pl_ap_ris + pl_ris_ue - ris_gain


def transmit_chunk(bits: np.ndarray,
                   payload_bits: int,
                   config: SignalConfig,
                   path_loss_dB: float,
                   noise_power_dB: float,
                   seed: int | None = None) -> dict:
    """Run one chunk through the baseband link."""
    modulator = Modulator(config.modulation)
    symbols = modulator.modulate(bits)
    tx_samples = np.repeat(symbols, config.samples_per_symbol)

    channel = RealChannel(path_loss_dB, noise_power_dB, seed=seed)
    rx_samples = channel.apply(
        tx_samples,
        K_factor=5.0,
        phase_noise_std=0.002,
        cfo_hz=100,
        sample_rate=config.sample_rate,
    )

    rx_symbols = rx_samples[::config.samples_per_symbol]
    channel_envelope = channel.last_channel_envelope
    if channel_envelope is not None:
        ce = channel_envelope[::config.samples_per_symbol]
        ce = ce[: len(rx_symbols)]
        ce = np.where(np.abs(ce) < 1e-9, 1.0 + 0j, ce)
        rx_symbols = rx_symbols / ce

    rx_bits, _ = modulator.demodulate(rx_symbols)

    valid_tx = bits[:payload_bits]
    valid_rx = rx_bits[:payload_bits]

    ser = RealSignalMeasurer.measure_ser(valid_tx, valid_rx)
    bit_errors = int(np.sum(valid_tx != valid_rx))

    signal_power = channel.last_signal_power or float(np.mean(np.abs(tx_samples) ** 2))
    noise_power = channel.last_noise_power or 10 ** (noise_power_dB / 10)
    snr_linear = max(signal_power / max(noise_power, 1e-12), 1e-12)
    snr_dB = 10 * np.log10(snr_linear)

    return {
        "snr_dB": float(snr_dB),
        "ser_percent": float(ser),
        "bit_errors": bit_errors,
        "payload_bits": payload_bits,
        "total_bits": int(payload_bits),
    }


def build_network() -> Tuple[RISNetwork, WaveformController]:
    """Set up a minimal AP→RIS→UE topology and controller."""
    network = RISNetwork()
    network.add_ap("ap1", 0, 0, 3, power_dBm=30, freq=28e9, bandwidth_MHz=100)
    network.add_ris("ris1", 40, 0, 6, N=16, bits=1, freq=28e9)
    network.add_ue("ue1", 90, 10, 1.5)

    controller = WaveformController(network)
    network.set_controller(controller)
    controller.set_ofdm_config(bandwidth=80e6, num_subcarriers=512, center_freq=28e9)
    return network, controller


def describe_topology(network: RISNetwork, ap_name: str, ris_name: str, ue_name: str):
    """Print the basic node information before running any controller logic."""
    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    print("\nTopology:")
    print(f"  AP  {ap.name}: pos={ap.pos}, freq={ap.freq/1e9:.1f} GHz, power={ap.power_dBm:.1f} dBm")
    print(f"  RIS {ris.name}: pos={ris.pos}, elements={ris.N}x{ris.N}, bits={ris.bits}")
    print(f"  UE  {ue.name}: pos={ue.pos}, NF={ue.noise_figure_dB:.1f} dB")


def align_ris_with_controller(network: RISNetwork,
                              controller: WaveformController,
                              ap_name: str,
                              ris_name: str,
                              ue_name: str) -> dict:
    """Run connect + waveform sweep and program the RIS phases."""
    print("\n[1] System-level connect (AP→RIS→UE)")
    connect_metrics = network.connect(ap_name, ris_name, ue_name, compute_phases=True)
    print(f"    SNR={connect_metrics['snr_dB']:.2f} dB, "
          f"Gain={connect_metrics['gain_dBi']:.2f} dBi, "
          f"Quant loss={connect_metrics['quant_loss_dB']:.2f} dB, "
          f"Beam angle={connect_metrics['beam_angle']:.2f}°")

    print("\n[2] Waveform beam sweep to refine steering")
    sweep = controller.compute_beam_sweep_waveform(ap_name, ris_name, ue_name,
                                                   angle_range=80.0, angle_step=5.0)
    best_angle = sweep["best_angle"]
    print(f"    Best angle={best_angle:.2f}°, "
          f"SNR={sweep['best_snr_dB']:.2f} dB, "
          f"Capacity={sweep['best_capacity_bps']/1e9:.3f} Gbps")

    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    print("\n[3] Programming RIS phase pattern")
    ideal_phases = ris.compute_phases(ap.pos, ue.pos)
    quantized, _ = ris.quantize_phases()
    programmed_phases = quantized if quantized is not None else ideal_phases
    ris.set_beam_config(best_angle, phases=programmed_phases)

    phase_error_deg = None
    if quantized is not None:
        phase_error = np.angle(np.exp(1j * (ideal_phases - quantized)))
        phase_error_deg = np.degrees(np.sqrt(np.mean(phase_error**2)))
        print(f"    Quantized {ris.bits}-bit pattern applied "
              f"(RMS error={phase_error_deg:.2f}° across {ris.N*ris.N} elements)")
    else:
        print("    Phase quantizer unavailable, using ideal (unquantized) phases.")

    return {
        "connect": connect_metrics,
        "sweep": sweep,
        "phase_error_deg": phase_error_deg,
        "best_angle_deg": float(best_angle),
        "ris_elements": ris.N * ris.N,
    }


def compute_no_ris_baseline(network: RISNetwork,
                            ap_name: str,
                            ue_name: str) -> dict:
    """Compute direct AP→UE link budget without RIS assistance."""
    ap = network.get(ap_name)
    ue = network.get(ue_name)

    distance = np.linalg.norm(ue.pos - ap.pos)
    path_loss = Physics.path_loss_dB(distance, ap.freq)
    ap_gain = getattr(ap, "antenna_gain_dBi", 3.0)
    ue_gain = getattr(ue, "antenna_gain_dBi", 3.0)
    noise_figure = getattr(ue, "noise_figure_dB", 6.0)
    bandwidth_MHz = getattr(ap, "bandwidth_MHz", 100.0)

    snr_dB = Physics.compute_snr_dB(
        tx_power_dBm=ap.power_dBm,
        total_loss_dB=path_loss,
        gain_dBi=ap_gain + ue_gain,
        bandwidth_MHz=bandwidth_MHz,
        noise_figure_dB=noise_figure,
    )

    capacity = Physics.compute_channel_capacity_bps(
        snr_dB,
        bandwidth_MHz * 1e6
    )

    return {
        "snr_dB": float(snr_dB),
        "path_loss_dB": float(path_loss),
        "distance_m": float(distance),
        "capacity_bps": float(capacity),
        "bandwidth_MHz": float(bandwidth_MHz),
    }


def run_video_stream_demo():
    repo_root = Path(__file__).parent.parent.parent
    video_path = repo_root / "streaming" / "video.mp4"

    network, controller = build_network()
    ap_name, ris_name, ue_name = "ap1", "ris1", "ue1"

    print("\n" + "=" * 72)
    print("RIS VIDEO STREAMING DEMO")
    print("=" * 72)
    print(f"Video source: {video_path}")

    describe_topology(network, ap_name, ris_name, ue_name)
    no_ris = compute_no_ris_baseline(network, ap_name, ue_name)
    print("\n[0] Direct AP→UE baseline (no RIS)")
    print(f"    Distance={no_ris['distance_m']:.1f} m | "
          f"Path loss={no_ris['path_loss_dB']:.2f} dB | "
          f"SNR={no_ris['snr_dB']:.2f} dB | "
          f"Capacity={no_ris['capacity_bps']/1e6:.2f} Mbps")
    link_state = align_ris_with_controller(network, controller, ap_name, ris_name, ue_name)

    print("\n[4] Waveform baseline at the selected configuration")
    baseline = controller.compute_waveform_snr(ap_name, ris_name, ue_name, num_symbols=6)
    snr_gain = baseline['snr_effective_dB'] - no_ris['snr_dB']
    capacity_gain = baseline['capacity_bps'] / max(no_ris['capacity_bps'], 1e-9)
    print(f"    RIS SNR={baseline['snr_ris_dB']:.2f} dB | "
          f"Effective SNR={baseline['snr_effective_dB']:.2f} dB "
          f"(Δ {snr_gain:+.2f} dB vs no RIS) | "
          f"Capacity={baseline['capacity_bps']/1e9:.3f} Gbps "
          f"(×{capacity_gain:.1f} of no RIS) | "
          f"PAPR={baseline['papr_dB']:.2f} dB")

    video_source = VideoBitstreamSource(video_path)
    signal_cfg = SignalConfig(
        modulation="16QAM",
        symbol_rate=2e6,
        sample_rate=20e6,
        num_symbols=2000,
    )
    modulator = Modulator(signal_cfg.modulation)
    bits_per_chunk = modulator.bits_per_symbol * signal_cfg.num_symbols

    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    # Include quantization penalty in the link-budget-derived path loss.
    path_loss_dB = estimate_ris_path_loss(ap, ris, ue) - link_state["connect"]["quant_loss_dB"]
    noise_power_dB = -92.0  # Approximate thermal noise for 100 MHz + NF margin

    chunk_idx = 0
    max_chunks = 6
    chunk_duration = signal_cfg.num_symbols / signal_cfg.symbol_rate
    delivered_bits = 0

    print("\n[5] Streaming chunks with programmed RIS phases:")
    while video_source.has_data() and chunk_idx < max_chunks:
        bits, payload_bits = video_source.next_bits(bits_per_chunk)
        if payload_bits == 0:
            break

        metrics = transmit_chunk(
            bits,
            payload_bits,
            signal_cfg,
            path_loss_dB,
            noise_power_dB,
            seed=chunk_idx,
        )

        useful_bits = payload_bits - metrics["bit_errors"]
        throughput_mbps = (useful_bits / chunk_duration) / 1e6
        delivered_bits += useful_bits

        print(
            f"  Chunk {chunk_idx+1:02d}: "
            f"SNR={metrics['snr_dB']:.2f} dB | "
            f"SER={metrics['ser_percent']:.3f} % | "
            f"Errors={metrics['bit_errors']} | "
            f"Throughput={throughput_mbps:.2f} Mbps"
        )

        chunk_idx += 1

    total_time = chunk_idx * chunk_duration
    avg_throughput = (delivered_bits / total_time) / 1e6 if total_time > 0 else 0.0
    print("\nSummary:")
    print(f"  Chunks sent:        {chunk_idx}")
    print(f"  Delivered bits:     {delivered_bits}")
    print(f"  Total time (s):     {total_time:.3f}")
    print(f"  Avg throughput:     {avg_throughput:.2f} Mbps")
    print(f"  Config modulation:  {signal_cfg.modulation}")
    print(f"  RIS angle used:     {link_state['best_angle_deg']:.2f}°")
    if link_state["phase_error_deg"] is not None:
        print(f"  Phase RMS error:    {link_state['phase_error_deg']:.2f}° "
              f"({link_state['ris_elements']} elements)")
    improvement_pct = (baseline['snr_effective_dB'] - no_ris['snr_dB'])
    capacity_pct = (capacity_gain - 1.0) * 100 if no_ris['capacity_bps'] > 0 else float('nan')
    print(f"  Waveform baseline:  {baseline['snr_effective_dB']:.2f} dB effective SNR "
          f"(+{improvement_pct:.2f} dB vs no RIS)")
    print(f"  Capacity gain:      {capacity_gain:.2f}× | +{capacity_pct:.1f}% vs no RIS\n")


if __name__ == "__main__":
    run_video_stream_demo()
