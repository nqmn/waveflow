"""
Shared helpers for streaming real video bitstreams through a RIS link.

Used by both Example 15 and the interactive CLI `stream` command.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import numpy as np

from core import RISNetwork, Physics
from core.signal_processor import (
    SignalConfig,
    Modulator,
    RealChannel,
    RealSignalMeasurer,
)
from controller.waveform_controller import WaveformController
from controller.beamsweeping import SweepAlgorithmLoader


Printer = Callable[[str], None]


class VideoBitstreamSource:
    """Reads a binary file and exposes it as a bitstream."""

    def __init__(self, path: Path):
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        self.data = path.read_bytes()
        self.cursor = 0
        self.path = path

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
                   seed: Optional[int] = None) -> Dict:
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


def describe_topology(printer: Printer,
                      network: RISNetwork,
                      ap_name: str,
                      ris_name: str,
                      ue_name: str):
    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    printer("\nTopology:")
    printer(f"  AP  {ap.name}: pos={ap.pos}, freq={ap.freq/1e9:.1f} GHz, power={ap.power_dBm:.1f} dBm")
    printer(f"  RIS {ris.name}: pos={ris.pos}, elements={ris.N}x{ris.N}, bits={ris.bits}")
    printer(f"  UE  {ue.name}: pos={ue.pos}, NF={ue.noise_figure_dB:.1f} dB")


def align_ris_with_controller(printer: Printer,
                              network: RISNetwork,
                              controller: WaveformController,
                              ap_name: str,
                              ris_name: str,
                              ue_name: str,
                              sweep_fov: float,
                              sweep_step: float) -> Dict:
    printer("\n[1] System-level connect (AP→RIS→UE)")
    connect_metrics = network.connect(ap_name, ris_name, ue_name, compute_phases=True)
    printer(f"    SNR={connect_metrics['snr_dB']:.2f} dB, "
            f"Gain={connect_metrics['gain_dBi']:.2f} dBi, "
            f"Quant loss={connect_metrics['quant_loss_dB']:.2f} dB, "
            f"Beam angle={connect_metrics['beam_angle']:.2f}°")

    printer("\n[2] Waveform beam sweep to refine steering")
    sweep = controller.compute_beam_sweep_waveform(
        ap_name, ris_name, ue_name,
        angle_range=sweep_fov, angle_step=sweep_step
    )
    best_angle = sweep["best_angle"]
    printer(f"    Best angle={best_angle:.2f}°, "
            f"SNR={sweep['best_snr_dB']:.2f} dB, "
            f"Capacity={sweep['best_capacity_bps']/1e9:.3f} Gbps")

    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    printer("\n[3] Programming RIS phase pattern")
    ideal_phases = ris.compute_phases(ap.pos, ue.pos)
    quantized, _ = ris.quantize_phases()
    programmed_phases = quantized if quantized is not None else ideal_phases
    ris.set_beam_config(best_angle, phases=programmed_phases)

    phase_error_deg = None
    if quantized is not None:
        phase_error = np.angle(np.exp(1j * (ideal_phases - quantized)))
        phase_error_deg = np.degrees(np.sqrt(np.mean(phase_error**2)))
        printer(f"    Quantized {ris.bits}-bit pattern applied "
                f"(RMS error={phase_error_deg:.2f}° across {ris.N*ris.N} elements)")
    else:
        printer("    Phase quantizer unavailable, using ideal (unquantized) phases.")

    return {
        "connect": connect_metrics,
        "sweep": sweep,
        "phase_error_deg": phase_error_deg,
        "best_angle_deg": float(best_angle),
        "ris_elements": ris.N * ris.N,
    }


def run_beam_sweep_comparison(printer: Printer,
                              network: RISNetwork,
                              ap_name: str,
                              ris_name: str,
                              ue_name: str,
                              fov: float,
                              step: float,
                              top_k: int,
                              seed: int = 1) -> Dict:
    printer("\n[2b] Beam sweep comparison (linear vs ML)")

    linear_algo = SweepAlgorithmLoader.get_algorithm("linear", network)
    linear_result = linear_algo.sweep(
        ap_name, ris_name, ue_name,
        fov=fov, step=step, seed=seed,
        enable_feedback=False
    )
    lin_abs_angle = linear_result["base_angle"] + linear_result["best_local_fine"]
    printer(f"    Linear sweep → best local {linear_result['best_local_fine']:.2f}°, "
            f"absolute {lin_abs_angle:.2f}°, SNR={linear_result['best_snr_fine']:.2f} dB "
            f"(tested {linear_result['num_angles_tested']} angles)")

    ml_algo = SweepAlgorithmLoader.get_algorithm("ml", network)
    ml_result = ml_algo.sweep(
        ap_name, ris_name, ue_name,
        fov=fov, top_k=top_k, seed=seed,
        enable_feedback=False, ml_predictor="default"
    )
    printer(f"    ML sweep   → best local {ml_result['best_local']:.2f}°, "
            f"absolute {ml_result['best_angle']:.2f}°, SNR={ml_result['best_snr']:.2f} dB "
            f"(tested {ml_result['num_angles_tested']} ML angles)")

    return {
        "linear": {
            "best_local_deg": float(linear_result["best_local_fine"]),
            "best_absolute_deg": float(lin_abs_angle),
            "best_snr_dB": float(linear_result["best_snr_fine"]),
            "angles_tested": int(linear_result["num_angles_tested"]),
            "angles": linear_result["angles"],
            "snr": linear_result["snr"],
        },
        "ml": {
            "best_local_deg": float(ml_result["best_local"]),
            "best_absolute_deg": float(ml_result["best_angle"]),
            "best_snr_dB": float(ml_result["best_snr"]),
            "angles_tested": int(ml_result["num_angles_tested"]),
            "suggestions": ml_result["ml_suggestions"],
        }
    }


def compute_no_ris_baseline(network: RISNetwork,
                            ap_name: str,
                            ue_name: str) -> Dict:
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


@dataclass
class VideoStreamConfig:
    video_path: Path
    modulation: str = "16QAM"
    num_symbols: int = 2000
    symbol_rate: float = 2e6
    sample_rate: float = 20e6
    chunk_limit: int = 6
    sweep_fov: float = 80.0
    sweep_step: float = 5.0
    ml_top_k: int = 2
    waveform_symbols: int = 6
    ofdm_bandwidth: float = 80e6
    ofdm_subcarriers: int = 512


def run_video_stream_workflow(network: RISNetwork,
                              ap_name: str,
                              ris_name: str,
                              ue_name: str,
                              config: VideoStreamConfig,
                              printer: Printer = print) -> Dict:
    """End-to-end workflow reused by the example script and CLI."""
    controller = WaveformController(network)
    network.set_controller(controller)
    controller.set_ofdm_config(
        bandwidth=config.ofdm_bandwidth,
        num_subcarriers=config.ofdm_subcarriers,
        center_freq=network.get(ap_name).freq
    )

    printer("\n" + "=" * 72)
    printer("RIS VIDEO STREAMING DEMO")
    printer("=" * 72)
    printer(f"Video source: {config.video_path}")

    describe_topology(printer, network, ap_name, ris_name, ue_name)
    no_ris = compute_no_ris_baseline(network, ap_name, ue_name)
    printer("\n[0] Direct AP→UE baseline (no RIS)")
    printer(f"    Distance={no_ris['distance_m']:.1f} m | "
            f"Path loss={no_ris['path_loss_dB']:.2f} dB | "
            f"SNR={no_ris['snr_dB']:.2f} dB | "
            f"Capacity={no_ris['capacity_bps']/1e6:.2f} Mbps")

    link_state = align_ris_with_controller(
        printer, network, controller,
        ap_name, ris_name, ue_name,
        config.sweep_fov, config.sweep_step
    )
    sweep_compare = run_beam_sweep_comparison(
        printer, network, ap_name, ris_name, ue_name,
        fov=config.sweep_fov,
        step=config.sweep_step,
        top_k=config.ml_top_k
    )

    printer("\n[4] Waveform baseline at the selected configuration")
    baseline = controller.compute_waveform_snr(ap_name, ris_name, ue_name,
                                              num_symbols=config.waveform_symbols)
    snr_gain = baseline['snr_effective_dB'] - no_ris['snr_dB']
    capacity_gain = baseline['capacity_bps'] / max(no_ris['capacity_bps'], 1e-9)
    printer(f"    RIS SNR={baseline['snr_ris_dB']:.2f} dB | "
            f"Effective SNR={baseline['snr_effective_dB']:.2f} dB "
            f"(Δ {snr_gain:+.2f} dB vs no RIS) | "
            f"Capacity={baseline['capacity_bps']/1e9:.3f} Gbps "
            f"(×{capacity_gain:.1f} of no RIS) | "
            f"PAPR={baseline['papr_dB']:.2f} dB")

    video_source = VideoBitstreamSource(config.video_path)
    signal_cfg = SignalConfig(
        modulation=config.modulation,
        symbol_rate=config.symbol_rate,
        sample_rate=config.sample_rate,
        num_symbols=config.num_symbols,
    )
    modulator = Modulator(signal_cfg.modulation)
    bits_per_chunk = modulator.bits_per_symbol * signal_cfg.num_symbols

    ap = network.get(ap_name)
    ris = network.get(ris_name)
    ue = network.get(ue_name)

    path_loss_dB = estimate_ris_path_loss(ap, ris, ue) - link_state["connect"]["quant_loss_dB"]
    noise_power_dB = -92.0  # Approximate thermal noise for 100 MHz + NF margin

    chunk_idx = 0
    chunk_duration = signal_cfg.num_symbols / signal_cfg.symbol_rate
    delivered_bits = 0
    printer("\n[5] Streaming chunks with programmed RIS phases:")
    while video_source.has_data() and chunk_idx < config.chunk_limit:
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

        printer(
            f"  Chunk {chunk_idx+1:02d}: "
            f"SNR={metrics['snr_dB']:.2f} dB | "
            f"SER={metrics['ser_percent']:.3f} % | "
            f"Errors={metrics['bit_errors']} | "
            f"Throughput={throughput_mbps:.2f} Mbps"
        )

        chunk_idx += 1

    total_time = chunk_idx * chunk_duration
    avg_throughput = (delivered_bits / total_time) / 1e6 if total_time > 0 else 0.0
    printer("\nSummary:")
    printer(f"  Chunks sent:        {chunk_idx}")
    printer(f"  Delivered bits:     {delivered_bits}")
    printer(f"  Total time (s):     {total_time:.3f}")
    printer(f"  Avg throughput:     {avg_throughput:.2f} Mbps")
    printer(f"  Config modulation:  {signal_cfg.modulation}")
    printer(f"  RIS angle used:     {link_state['best_angle_deg']:.2f}°")
    if link_state["phase_error_deg"] is not None:
        printer(f"  Phase RMS error:    {link_state['phase_error_deg']:.2f}° "
                f"({link_state['ris_elements']} elements)")
    improvement_pct = (baseline['snr_effective_dB'] - no_ris['snr_dB'])
    capacity_pct = (capacity_gain - 1.0) * 100 if no_ris['capacity_bps'] > 0 else float('nan')
    printer(f"  Waveform baseline:  {baseline['snr_effective_dB']:.2f} dB effective SNR "
            f"(+{improvement_pct:.2f} dB vs no RIS)")
    printer(f"  Capacity gain:      {capacity_gain:.2f}× | +{capacity_pct:.1f}% vs no RIS\n")
    printer("  Beam sweep recap:")
    printer(f"    Linear brute-force best: {sweep_compare['linear']['best_absolute_deg']:.2f}° "
            f"({sweep_compare['linear']['best_snr_dB']:.2f} dB, "
            f"{sweep_compare['linear']['angles_tested']} angles)")
    printer(f"    ML-only best:            {sweep_compare['ml']['best_absolute_deg']:.2f}° "
            f"({sweep_compare['ml']['best_snr_dB']:.2f} dB, "
            f"{sweep_compare['ml']['angles_tested']} suggestions)\n")

    return {
        "no_ris": no_ris,
        "waveform_baseline": baseline,
        "link_state": link_state,
        "sweep_comparison": sweep_compare,
        "streaming": {
            "chunks_sent": chunk_idx,
            "delivered_bits": delivered_bits,
            "avg_throughput_mbps": avg_throughput,
            "path_loss_dB": path_loss_dB,
            "noise_power_dB": noise_power_dB,
        },
        "config": {
            "video_path": str(config.video_path),
            "signal_config": signal_cfg.__dict__,
        }
    }
