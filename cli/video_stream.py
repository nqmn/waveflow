"""
Shared helpers for streaming real video bitstreams through a RIS link.

Used by both Example 15 and the interactive CLI `stream` command.
"""

from __future__ import annotations

import math
import time
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

    ser = RealSignalMeasurer.measure_ser(
        valid_tx,
        valid_rx,
        bits_per_symbol=modulator.bits_per_symbol
    )
    bit_errors = int(np.sum(valid_tx != valid_rx))
    ber = (bit_errors / max(payload_bits, 1)) * 100.0

    # SNR after equalization but before FEC decoding (post-CE, pre-FEC)
    # Measured as signal_power / noise_power in symbol domain
    signal_power = channel.last_signal_power or float(np.mean(np.abs(tx_samples) ** 2))
    noise_power = channel.last_noise_power or 10 ** (noise_power_dB / 10)
    snr_linear = max(signal_power / max(noise_power, 1e-12), 1e-12)
    snr_dB = 10 * np.log10(snr_linear)

    return {
        "snr_dB": float(snr_dB),  # Post-equalization, pre-decoder SNR in symbol domain
        "ser_percent": float(ser),
        "ber_percent": float(ber),
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
                              ue_name: str) -> Dict:
    printer("\n[1] System-level connect (AP→RIS→UE)")

    # Find an active link for this path (may have been created by connect or connect_sweep)
    active_links = network.get_active_links()
    active_link_key = None

    # Look for any link matching this path (different sources may use different key formats)
    for key in active_links:
        if ap_name in key and ris_name in key and ue_name in key:
            active_link_key = key
            break

    if active_link_key is None:
        raise ValueError(f"Active link not found for {ap_name}→{ris_name}→{ue_name}. "
                        f"Run 'connect' or 'connect_sweep' command first to establish the link.")

    # Use active link configuration
    active_link = active_links[active_link_key]
    printer(f"    Using active link configuration:")
    printer(f"    SNR={active_link['snr_dB']:.2f} dB, "
            f"Gain={active_link['gain_dBi']:.2f} dBi, "
            f"Quantization penalty={abs(active_link['quant_loss_dB']):.2f} dB "
            f"(ΔSNR={active_link['quant_loss_dB']:.2f} dB), "
            f"Beam angle (absolute)={active_link['beam_angle_absolute']:.2f}° "
            f"(local={active_link['beam_angle_local']:.2f}°)")

    # Create connect_metrics from active link
    connect_metrics = {
        'snr_dB': active_link['snr_dB'],
        'pwr_dBm': active_link['pwr_dBm'],
        'gain_dBi': active_link['gain_dBi'],
        'quant_loss_dB': active_link['quant_loss_dB'],
        'beam_angle': active_link['beam_angle_absolute'],
        'current_phases': active_link.get('current_phases'),
        'quantized_phases': active_link.get('quantized_phases'),
    }

    # Use the active link's angle
    best_angle = active_link['beam_angle_absolute']
    local_angle = active_link['beam_angle_local']

    # Use isolated copies of nodes to prevent state pollution
    # (modifications to phases and beam config won't affect the original network)
    ap = network.get(ap_name).clone()
    ris = network.get(ris_name).clone()
    ue = network.get(ue_name).clone()

    printer("\n[2] Programming RIS phase pattern")
    ideal_phases = ris.compute_phases(ap.pos, ue.pos)
    quantized, _ = ris.quantize_phases()
    programmed_phases = quantized if quantized is not None else ideal_phases
    ris.set_beam_config(best_angle, phases=programmed_phases)

    phase_error_deg = None
    if quantized is not None:
        phase_error = np.angle(np.exp(1j * (ideal_phases - quantized)))
        phase_error_deg = np.degrees(np.sqrt(np.mean(phase_error**2)))
        printer(f"    Quantized {ris.bits}-bit pattern applied "
                f"(RMS error={phase_error_deg:.2f}° across {ris.N*ris.N} elements, "
                f"local={local_angle:.2f}°)")
    else:
        printer("    Phase quantizer unavailable, using ideal (unquantized) phases.")

    return {
        "connect": connect_metrics,
        "phase_error_deg": phase_error_deg,
        "best_angle_deg": float(best_angle),
        "ris_elements": ris.N * ris.N,
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
    waveform_symbols: int = 6
    ofdm_bandwidth: float = 80e6
    ofdm_subcarriers: int = 512
    quality_metrics: bool = False
    beam_adaptive: bool = False


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
            f"SNR (direct, ideal receiver)={no_ris['snr_dB']:.2f} dB | "
            f"Capacity={no_ris['capacity_bps']/1e6:.2f} Mbps")

    link_state = align_ris_with_controller(
        printer, network, controller,
        ap_name, ris_name, ue_name
    )

    printer("\n[3] Waveform baseline at the selected configuration")
    baseline = controller.compute_waveform_snr(ap_name, ris_name, ue_name,
                                              num_symbols=config.waveform_symbols)
    snr_gain = baseline['snr_effective_dB'] - no_ris['snr_dB']
    capacity_gain = baseline['capacity_bps'] / max(no_ris['capacity_bps'], 1e-9)
    printer(f"    RIS SNR (pre-combiner)={baseline['snr_ris_dB']:.2f} dB | "
            f"Effective SNR (post-equalization, with waveform impairments)={baseline['snr_effective_dB']:.2f} dB "
            f"(Δ {snr_gain:+.2f} dB vs direct) | "
            f"Capacity={baseline['capacity_bps']/1e9:.3f} Gbps "
            f"({capacity_gain:.1f}× of direct) | "
            f"PAPR={baseline['papr_dB']:.2f} dB")
    if snr_gain < 0:
        printer(f"    Note: Effective SNR reduced by waveform impairments (phase quantization error, "
                f"symbol-level distortion). Pre-combiner SNR ({baseline['snr_ris_dB']:.2f} dB) is the "
                f"RIS-beamformed path quality before post-equalization processing.")

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
    path_gain_linear = 10 ** (-path_loss_dB / 10)
    target_snr_dB = baseline['snr_effective_dB']
    target_snr_linear = max(10 ** (target_snr_dB / 10), 1e-12)
    tx_symbol_power = float(np.mean(np.abs(modulator.constellation) ** 2))
    received_symbol_power = max(tx_symbol_power * path_gain_linear, 1e-15)
    noise_power_linear = max(received_symbol_power / target_snr_linear, 1e-15)
    noise_power_dB = 10 * np.log10(noise_power_linear)

    chunk_idx = 0
    chunk_duration = signal_cfg.num_symbols / signal_cfg.symbol_rate
    delivered_bits = 0
    snr_warning_thresholds = {
        "QPSK": 6.0,
        "16QAM": 12.0,
        "64QAM": 18.0,
    }
    modulation_upper = signal_cfg.modulation.upper()
    snr_guard_threshold = snr_warning_thresholds.get(modulation_upper, 10.0)
    snr_warning_emitted = False

    # Adaptive beam steering framework
    adaptive_beam_history = []
    adaptive_beam_check_interval = 2  # Check every N chunks
    current_beam_angle = link_state.get('best_angle_deg', 0)

    if config.beam_adaptive:
        printer("\n[5] Streaming chunks with adaptive beam steering enabled:")
        printer(f"    Initial beam angle: {current_beam_angle:.2f}°")
    else:
        printer("\n[5] Streaming chunks with programmed RIS phases:")

    stream_start_time = time.time()
    while video_source.has_data() and chunk_idx < config.chunk_limit:
        chunk_start_time = time.time()
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
        chunk_elapsed_time = time.time() - chunk_start_time

        useful_bits = payload_bits - metrics["bit_errors"]
        throughput_mbps = (useful_bits / chunk_duration) / 1e6
        delivered_bits += useful_bits

        # Format: SNR post-equalization (before FEC), SER %, bit errors, throughput, elapsed time
        ber_desc = (f"{metrics['bit_errors']:,d}/{metrics['payload_bits']:,d} bits")
        printer(
            f"  Chunk {chunk_idx+1:02d}: "
            f"SNR_postEQ={metrics['snr_dB']:.2f} dB | "
            f"BER={metrics['ber_percent']:.3f}% ({ber_desc}) | "
            f"SER={metrics['ser_percent']:.3f}% | "
            f"Tput={throughput_mbps:.2f} Mbps | "
            f"Time={chunk_elapsed_time:.3f}s"
        )

        # Enhanced quality metrics if requested
        if config.quality_metrics:
            snr_dB = metrics['snr_dB']
            ber = metrics['ber_percent']
            ser = metrics['ser_percent']

            # Quality classification
            quality = "EXCELLENT"
            if snr_dB < snr_guard_threshold:
                quality = "POOR"
            elif snr_dB < snr_guard_threshold + 2:
                quality = "MARGINAL"
            elif snr_dB < snr_guard_threshold + 5:
                quality = "GOOD"

            printer(f"    [QUALITY] SNR={snr_dB:.2f}dB | BER={ber:.4f}% | SER={ser:.4f}% | Status={quality}")

        # Adaptive beam steering if enabled
        if config.beam_adaptive and (chunk_idx + 1) % adaptive_beam_check_interval == 0:
            snr_dB = metrics['snr_dB']
            adaptive_beam_history.append({
                'chunk': chunk_idx,
                'snr_dB': snr_dB,
                'angle_deg': current_beam_angle
            })

            # Simple hill-climbing: try ±5° to see if we can improve SNR
            trial_angles = [current_beam_angle - 5.0, current_beam_angle + 5.0]
            best_snr = snr_dB
            best_angle = current_beam_angle

            for trial_angle in trial_angles:
                try:
                    # Quick SNR measurement at trial angle (simplified)
                    trial_result = network.connect(
                        ap_name, ris_name, ue_name,
                        beam_angle_deg=trial_angle,
                        compute_phases=False,
                        use_isolated_copy=True,
                        store_in_active_links=False
                    )
                    trial_snr = trial_result.get('snr_dB', snr_dB)
                    if trial_snr > best_snr:
                        best_snr = trial_snr
                        best_angle = trial_angle
                except:
                    pass  # Keep current angle if trial fails

            if best_angle != current_beam_angle:
                current_beam_angle = best_angle
                improvement = best_snr - snr_dB
                printer(f"    [ADAPT] Adjusted beam to {current_beam_angle:.2f}° (SNR improved by {improvement:.2f} dB)")

        if (not snr_warning_emitted) and metrics['snr_dB'] < snr_guard_threshold:
            printer(f"    [warn] Post-EQ SNR {metrics['snr_dB']:.2f} dB is below the typical "
                    f"{signal_cfg.modulation} operating point (~{snr_guard_threshold:.1f} dB). "
                    f"Check noise normalization or modulation settings.")
            snr_warning_emitted = True

        chunk_idx += 1

    stream_elapsed_time = time.time() - stream_start_time

    total_time = chunk_idx * chunk_duration
    avg_throughput = (delivered_bits / total_time) / 1e6 if total_time > 0 else 0.0
    printer("\nSummary:")
    printer(f"  Chunks sent:        {chunk_idx:,d}")
    printer(f"  Delivered bits:     {delivered_bits:,d}")
    printer(f"  Simulation time:    {total_time:.3f}s (chunk duration × count)")
    printer(f"  Wall-clock time:    {stream_elapsed_time:.3f}s (actual elapsed)")
    printer(f"  Avg throughput:     {avg_throughput:.2f} Mbps")
    printer(f"  Payload/chunk:      {bits_per_chunk:,d} bits ({bits_per_chunk/8:,.0f} bytes)")
    printer(f"  Config modulation:  {signal_cfg.modulation} @ {signal_cfg.symbol_rate/1e6:.1f} MSym/s")
    printer(f"  RIS angle used:     {link_state['best_angle_deg']:.2f}°")
    if link_state["phase_error_deg"] is not None:
        printer(f"  Phase RMS error:    {link_state['phase_error_deg']:.2f}° "
                f"({link_state['ris_elements']:,d} elements)")
    improvement_pct = (baseline['snr_effective_dB'] - no_ris['snr_dB'])
    capacity_pct = (capacity_gain - 1.0) * 100 if no_ris['capacity_bps'] > 0 else float('nan')
    printer(f"  Waveform baseline:  {baseline['snr_effective_dB']:.2f} dB effective SNR "
            f"(+{improvement_pct:.2f} dB vs direct)")
    printer(f"  Capacity gain:      {capacity_gain:.2f}× | +{capacity_pct:.1f}% vs direct")
    bw_mhz = getattr(ap, 'bandwidth_MHz', 100.0) if ap else 100.0
    printer(f"  Capacity model:     Shannon (C = BW × log₂(1+SNR)) with {bw_mhz:.0f} MHz BW\n")

    return {
        "no_ris": no_ris,
        "waveform_baseline": baseline,
        "link_state": link_state,
        "streaming": {
            "chunks_sent": chunk_idx,
            "delivered_bits": delivered_bits,
            "avg_throughput_mbps": avg_throughput,
            "path_loss_dB": path_loss_dB,
            "noise_power_dB": noise_power_dB,
            "target_snr_dB": target_snr_dB,
        },
        "config": {
            "video_path": str(config.video_path),
            "signal_config": signal_cfg.__dict__,
        }
    }
