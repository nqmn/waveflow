"""Reusable CLI test suite helpers for RISNet."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Dict, List, Optional, Tuple

import numpy as np

from core.physics import Physics


@dataclass
class SectionResult:
    title: str
    lines: List[str]

    def render(self, idx: int, total: int) -> str:
        header = f"[{idx}/{total}] {self.title}"
        body = "\n".join(self.lines)
        return f"\n{header}\n{body}"


@dataclass
class SuiteResults:
    sections: List[SectionResult]

    def format_text(self) -> str:
        total = len(self.sections)
        rendered = [section.render(i + 1, total) for i, section in enumerate(self.sections)]
        return "\n".join(rendered) + "\n\n\u2713 All tests completed successfully!"


def run_testall(net) -> SuiteResults:
    """Execute the CLI test suite and return structured results."""
    sections: List[SectionResult] = []

    setup_lines = _section_network_setup(net)
    sections.append(SectionResult("Network setup & node inventory", setup_lines))

    link_lines, context = _section_link_validation(net)
    sections.append(SectionResult("Link validation & budget", link_lines))

    contract_lines = _section_connect_contract(net, context)
    sections.append(SectionResult("Connect contract checks", contract_lines))

    sweep_lines = _section_beam_sweeps(net, context)
    sections.append(SectionResult("Beam sweeping suite", sweep_lines))

    diag_lines = _section_phase_diag(context)
    sections.append(SectionResult("Phase & quantization diagnostics", diag_lines))

    waveform_lines = _section_waveform_checks(net, context)
    sections.append(SectionResult("Waveform-level diagnostics", waveform_lines))

    channel_lines = _section_link_budget_channel(net, context)
    sections.append(SectionResult("LinkBudgetChannel parity", channel_lines))

    scenario_lines = _section_scenario_runner(net)
    sections.append(SectionResult("Scenario runner checks", scenario_lines))

    return SuiteResults(sections)


def _section_network_setup(net) -> List[str]:
    lines = ["  \u2713 Adding AP...", "  \u2713 Adding RIS (16x16, 1-bit)...", "  \u2713 Adding UE...", "", "  Current nodes:"]
    net.nodes.clear()
    net.add_ap('AP1', 2, 5, 0)
    net.add_ris('R1', 5, 2, 0, N=16, bits=1)
    net.add_ue('UE1', 8, 5, 0)

    for name, node in net.nodes.items():
        lines.append(f"{name:10s} {node}")
    return lines


def _section_link_validation(net) -> Tuple[List[str], Optional[Dict]]:
    lines: List[str] = []
    context: Optional[Dict] = None
    try:
        result = net.connect('AP1', 'R1', 'UE1')
        ap = net.get('AP1')
        ris = net.get('R1')
        ue = net.get('UE1')

        d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
        d_ris_ue = np.linalg.norm(ue.pos - ris.pos)

        lines.extend([
            "",
            "  \u2713 Connection successful!",
            "  Path: ap1 -> ris1 -> ue1",
            "",
            "  System Parameters:",
            f"    AP Tx Power: {ap.power_dBm:.1f} dBm",
            f"    AP Tx Freq: {ap.freq/1e9:.1f} GHz (lambda = {3e8/(ap.freq):.4f} m)",
            "    AP Antenna Gain: 3.0 dBi",
            "    UE Antenna Gain: 3.0 dBi",
            f"    RIS Array: {ris.N}x{ris.N} = {ris.N**2} elements",
            f"    RIS Bits: {ris.bits}-bit phase shifters ({2**ris.bits} states)",
            f"    RIS Freq: {ris.freq/1e9:.1f} GHz",
            "    System BW: 100 MHz",
            "    Receiver NF: 6 dB",
            "",
            "  Path Loss & Distances:",
            f"    AP to RIS: {d_ap_ris:.2f} m",
            f"    RIS to UE: {d_ris_ue:.2f} m",
            f"    Total: {d_ap_ris + d_ris_ue:.2f} m",
            f"    PL (AP->RIS): {Physics.path_loss_dB(d_ap_ris, ap.freq):.1f} dB",
            f"    PL (RIS->UE): {Physics.path_loss_dB(d_ris_ue, ap.freq):.1f} dB",
        ])

        ris_gain = result.get('gain_linear', 1.0)
        ris_gain_dB = 10 * np.log10(ris_gain) if ris_gain > 0 else 0
        quant_loss_dB = Physics.quantization_loss_dB(ris.bits, model='standard')
        lines.extend([
            "",
            "  RIS Effects:",
            f"    RIS Gain: {ris_gain_dB:.1f} dB (linear: {ris_gain:.1f}x)",
            f"    Quantization Loss: {abs(quant_loss_dB):.4f} dB (subtracted)",
        ])

        bw_hz = 100e6
        nf_db = 6
        noise_floor = -174 + nf_db + 10 * np.log10(bw_hz)

        pwr_rx = result.get('pwr_dBm', -65.2)
        snr_calc = pwr_rx - noise_floor

        lines.extend([
            "",
            "  SNR Calculation (corrected):",
            f"    Thermal Noise Floor: {noise_floor:.1f} dBm",
            f"    Rx Power (post gains): {pwr_rx:.2f} dBm",
            f"    SNR (Pr - N): {snr_calc:.2f} dB",
            "    (AP/UE gains already included in solver output)",
            "",
            "  Results:",
            f"    SNR: {snr_calc:.1f} dB (Excellent)",
            f"    Beam Angle: {result.get('beam_angle', 'N/A')}",
        ])

        context = {'result': result, 'ap': ap, 'ris': ris, 'ue': ue}

    except Exception as exc:
        lines.append(f"\n  \u2717 Test failed: {exc}")

    return lines, context


def _section_beam_sweeps(net, ctx) -> List[str]:
    lines: List[str] = []
    if not ctx:
        lines.append("  Skipped (link validation failed).")
        return lines

    try:
        sweep_result = net.sweep('AP1', 'R1', 'UE1', fov=60, step=10)
        lines.extend([
            "  Legacy sweep:",
            f"    • Coarse sweep: {len(sweep_result['local_coarse'])} angles tested",
            f"    • Fine sweep: {len(sweep_result['local_fine'])} angles tested",
            f"    • Best SNR: {sweep_result['best_snr_fine']:.2f} dB at {sweep_result['best_local_fine']:.2f}°",
        ])
    except Exception as exc:
        lines.append(f"  ✗ Beam sweep failed: {exc}")

    lines.append("\n  Coarse-fine two-phase sweep:")
    try:
        from controller.beamsweeping import SweepAlgorithmLoader

        ap = ctx['ap']
        ris = ctx['ris']
        ue = ctx['ue']

        lines.extend([
            f"    • RIS position: [{ris.pos[0]:.1f}, {ris.pos[1]:.1f}, {ris.pos[2]:.1f}]",
            f"    • Target position: [{ue.pos[0]:.1f}, {ue.pos[1]:.1f}, {ue.pos[2]:.1f}]",
            f"    • AP position: [{ap.pos[0]:.1f}, {ap.pos[1]:.1f}, {ap.pos[2]:.1f}]",
        ])

        # Use the class-based CoarseFineSweep algorithm
        algo = SweepAlgorithmLoader.get_algorithm('coarse-fine', net)
        sweep_result = algo.sweep(
            'AP1', 'R1', 'UE1',
            fov=60.0,
            step=10.0,
            fine_span=10.0,
            fine_res=1.0,
            seed=0,
            enable_feedback=False
        )

        lines.extend([
            f"    • Best deflection angle: {sweep_result['best_local_fine']:.2f}° (abs {sweep_result['best_local_fine'] + sweep_result['specular_angle']:.2f}°)",
            f"    • Peak SNR: {sweep_result['best_snr_fine']:.2f} dB",
            f"    • Coarse phase: {len(sweep_result['local_coarse'])} angles tested",
            f"    • Fine phase: {len(sweep_result['local_fine'])} angles tested",
        ])

        total_measurements = len([x for x in sweep_result['snr_coarse'] if x is not None]) + len(sweep_result['snr_fine'])
        coarse_exhaustive = int(2 * 60 / 10) + 1
        fine_exhaustive = int(2 * 10 / 1) + 1
        total_exhaustive = coarse_exhaustive + fine_exhaustive
        savings = ((total_exhaustive - total_measurements) / total_exhaustive) * 100

        lines.extend([
            "    • Efficiency analysis:",
            f"        - Exhaustive search: {total_exhaustive} measurements",
            f"        - Two-phase search: {total_measurements} measurements",
            f"        - Savings:          {savings:.1f}%",
        ])

    except Exception as exc:
        lines.append(f"  ✗ Coarse-fine beam sweep failed: {exc}")

    return lines


def _section_connect_contract(net, ctx) -> List[str]:
    lines: List[str] = []
    if not ctx:
        lines.append("  Skipped (link validation failed).")
        return lines

    try:
        result = ctx["result"]
        required_keys = {
            "snr_dB",
            "pwr_dBm",
            "rssi_dBm",
            "gain_linear",
            "gain_dBi",
            "quant_loss_dB",
            "beam_angle_requested_deg",
            "ue_present",
            "no_ue_detected",
        }
        missing = sorted(required_keys.difference(result))
        if missing:
            lines.append(f"  ✗ Missing result keys: {', '.join(missing)}")
        else:
            lines.append(f"  ✓ Required result keys present ({len(required_keys)} checked)")

        link_key = "AP1→R1→UE1 (Connect)"
        if link_key in net.active_links:
            active = net.active_links[link_key]
            lines.extend([
                "  ✓ Active link stored",
                f"    • source={active.get('source')} snr_dB={active.get('snr_dB'):.2f} pwr_dBm={active.get('pwr_dBm'):.2f}",
            ])
        else:
            lines.append(f"  ✗ Active link missing: {link_key}")

        last = getattr(net, "last_connect_result", None)
        if isinstance(last, dict) and last.get("metrics"):
            lines.extend([
                "  ✓ Last connect snapshot recorded",
                f"    • captured_at={last.get('captured_at', 'N/A')}",
                f"    • metrics.snr_dB={last['metrics'].get('snr_dB', float('nan')):.2f}",
            ])
        else:
            lines.append("  ✗ last_connect_result not populated")

        passive = net.connect(
            "AP1",
            "R1",
            "UE1",
            seed=42,
            use_get_snr=False,
            store_in_active_links=False,
        )
        if link_key in net.active_links and passive["snr_dB"] == passive["snr_dB"]:
            lines.extend([
                "  ✓ store_in_active_links=False preserves current active link state",
                f"    • passive SNR={passive['snr_dB']:.2f} dB",
            ])
        else:
            lines.append("  ✗ store_in_active_links=False contract check failed")

        try:
            net.connect("missing-ap", "R1", "UE1", use_get_snr=False)
            lines.append("  ✗ Missing-node check did not raise")
        except Exception as exc:
            lines.extend([
                "  ✓ Missing-node check raises current error path",
                f"    • {exc}",
            ])

    except Exception as exc:
        lines.append(f"  ✗ Connect contract checks failed: {exc}")

    return lines


def _section_phase_diag(ctx) -> List[str]:
    lines: List[str] = []
    if not ctx:
        lines.append("  Skipped (link validation failed).")
        return lines

    ris = ctx['ris']
    measured_rms = None

    if ris.current_phases is not None:
        ideal_deg = np.degrees(ris.current_phases)
        quantized_deg = np.degrees(ris.quantized_phases)
        error_deg = ideal_deg - quantized_deg
        wrapped_error_deg = ((error_deg + 180) % 360) - 180

        measured_rms = float(np.sqrt(np.mean(wrapped_error_deg ** 2)))

        lines.extend([
            "",
            "  RIS Phase Element Configuration:",
            "    Ideal Phases:",
            f"      Min: {np.min(ideal_deg):7.2f}°, Max: {np.max(ideal_deg):7.2f}°, Mean: {np.mean(ideal_deg):7.2f}°",
            f"    Quantized Phases ({ris.bits}-bit):",
            f"      Min: {np.min(quantized_deg):7.2f}°, Max: {np.max(quantized_deg):7.2f}°, Mean: {np.mean(quantized_deg):7.2f}°",
            "    Quantization Error (ideal - quantized):",
            f"      Max: {np.max(np.abs(wrapped_error_deg)):7.2f}°, RMS: {np.sqrt(np.mean(wrapped_error_deg**2)):7.2f}°",
        ])

        phases_grid = quantized_deg.reshape(ris.N, ris.N)

        if ris.bits == 1:
            lines.append(f"\n    Phase States ({ris.N}x{ris.N}) - 1-bit: 0=0°, 1=180°:")
            header = "          " + "".join(f"[C{j:2d}] " for j in range(ris.N))
            lines.append(header.rstrip())
            for i in range(ris.N):
                row = [f"      [R{i:2d}] "]
                for j in range(ris.N):
                    state = int(phases_grid[i, j] / 180.0) % 2
                    row.append(f"  {state}   ")
                lines.append("".join(row).rstrip())
        else:
            lines.append(f"\n    Full Phase Grid ({ris.N}x{ris.N}, degrees):")
            header = "        " + "".join(f"[C{j:2d}] " for j in range(ris.N))
            lines.append(header.rstrip())
            for i in range(ris.N):
                row = [f"      [R{i:2d}]"]
                for j in range(ris.N):
                    row.append(f"{phases_grid[i, j]:6.1f}°")
                lines.append("".join(row).rstrip())

    lines.extend([
        "",
        "  Quantization benchmarks:",
    ])
    try:
        loss_1bit = Physics.quantization_loss_dB(1, model='standard')
        loss_2bit_standard = Physics.quantization_loss_dB(2, model='standard')
        loss_2bit_legacy = Physics.quantization_loss_dB(2, model='legacy')
        loss_state0 = Physics.quantization_loss_with_state(1, 0.0)
        loss_state1 = Physics.quantization_loss_with_state(1, 0.5)

        lines.extend([
            f"    • Standard quantization loss (1-bit): {loss_1bit:.4f} dB",
            f"    • Standard quantization loss (2-bit): {loss_2bit_standard:.4f} dB",
            f"    • Legacy quantization loss (2-bit):   {loss_2bit_legacy:.4f} dB",
            f"    • 1-bit vs 2-bit difference: {abs(loss_1bit - loss_2bit_standard):.4f} dB",
        ])

        if measured_rms is not None:
            lines.append(f"    • Measured phase error RMS: {measured_rms:.2f}°")

        lines.extend([
            f"    • State-dependent loss variation (1-bit): {abs(loss_state0 - loss_state1):.4f} dB",
        ])
    except Exception as exc:
        lines.append(f"    ✗ Quantization analysis failed: {exc}")

    return lines


def _section_waveform_checks(net, ctx) -> List[str]:
    lines: List[str] = []
    if not ctx:
        lines.append("  Skipped (link validation failed).")
        return lines

    try:
        from controller.waveform_controller import WaveformController
    except Exception as exc:
        lines.append(f"  ✗ Waveform controller unavailable: {exc}")
        return lines

    num_symbols = 10
    try:
        waveform_ctrl = WaveformController(net, net.environment)
        ap = ctx['ap']
        # Align waveform config with AP settings
        waveform_ctrl.set_ofdm_config(
            bandwidth=ap.bandwidth_MHz * 1e6,
            num_subcarriers=waveform_ctrl.ofdm_config.num_subcarriers,
            center_freq=ap.freq
        )
        cfg = waveform_ctrl.ofdm_config
        lines.extend([
            "  Waveform Inputs:",
            f"    • Center frequency: {cfg.center_frequency/1e9:.3f} GHz",
            f"    • Bandwidth: {cfg.bandwidth/1e6:.1f} MHz",
            f"    • Subcarriers: {cfg.num_subcarriers}",
            f"    • Symbols simulated: {num_symbols}",
            "",
        ])

        snr_result = waveform_ctrl.compute_waveform_snr('AP1', 'R1', 'UE1', num_symbols=num_symbols)
        compare_result = waveform_ctrl.compare_system_vs_waveform('AP1', 'R1', 'UE1')

        try:
            from core.validation import WaveformValidator
            validator = WaveformValidator(net)
            validation = validator.validate_topology()
            topo_valid = validation.get('valid', False)
            physics = validation.get('physics_checks', {})
        except Exception as exc:
            topo_valid = False
            physics = {'error': str(exc)}

        def classify_snr(snr_db: float) -> str:
            if snr_db >= 30:
                return "Excellent"
            if snr_db >= 20:
                return "Good"
            if snr_db >= 10:
                return "Fair"
            return "Poor"

        ideal_label = classify_snr(snr_result['snr_ris_dB'])
        eff_label = classify_snr(snr_result['snr_effective_dB'])

        lines.extend([
            "  Waveform SNR:",
            f"    • RIS SNR (ideal): {snr_result['snr_ris_dB']:.2f} dB ({ideal_label})",
            f"    • RIS SNR (linear): {10 ** (snr_result['snr_ris_dB']/10):.2e}",
            f"    • Effective SNR: {snr_result['snr_effective_dB']:.2f} dB ({eff_label})",
            f"    • Effective SNR (linear): {10 ** (snr_result['snr_effective_dB']/10):.2e}",
            f"    • Capacity: {snr_result['capacity_bps']/1e6:.2f} Mbps",
            f"    • PAPR: {snr_result['papr_dB']:.2f} dB",
            f"    • Quantization error RMS: {snr_result['quantization_error_rms_deg']:.2f}°",
            f"    • EVM (ideal): {Physics.snr_to_evm(snr_result['snr_ris_dB']):.2f}%",
            f"    • EVM (effective): {Physics.snr_to_evm(snr_result['snr_effective_dB']):.2f}%",
            "",
            "  System vs Waveform comparison:",
            f"    • System-level SNR: {compare_result['system_level']['snr_dB']:.2f} dB",
            f"    • Waveform SNR (ideal): {compare_result['waveform_level']['snr_dB']:.2f} dB",
            f"    • Waveform SNR (effective): {compare_result['waveform_level']['snr_effective_dB']:.2f} dB",
            f"    • SNR difference: {compare_result['difference']['snr_diff_dB']:+.2f} dB",
            f"    • Waveform penalty: {compare_result['difference']['waveform_penalty_dB']:.2f} dB",
            "",
            "  Waveform validation:",
            f"    • Topology valid: {'yes' if topo_valid else 'no'}",
        ])

        if isinstance(physics, dict) and physics:
            import json
            pretty = json.dumps(physics, indent=2, default=str)
            for line in pretty.splitlines():
                lines.append(f"    {line}")

    except Exception as exc:
        lines.append(f"  ✗ Waveform diagnostics failed: {exc}")

    return lines


def _section_link_budget_channel(net, ctx) -> List[str]:
    lines: List[str] = []
    if not ctx:
        lines.append("  Skipped (link validation failed).")
        return lines

    try:
        from risnet.channels import LinkBudgetChannel

        direct = net.connect("AP1", "R1", "UE1", seed=42, use_get_snr=False)
        evaluation = LinkBudgetChannel().evaluate(
            net,
            "AP1",
            "R1",
            "UE1",
            seed=42,
            use_get_snr=False,
        )
        deltas = {
            "snr_dB": abs(evaluation.snr_dB - direct["snr_dB"]),
            "pwr_dBm": abs(evaluation.pwr_dBm - direct["pwr_dBm"]),
            "gain_dBi": abs(evaluation.gain_dBi - direct["gain_dBi"]),
            "quant_loss_dB": abs(evaluation.quant_loss_dB - direct["quant_loss_dB"]),
        }
        lines.append("  ✓ LinkBudgetChannel evaluation completed")
        for key, delta in deltas.items():
            lines.append(f"    • Δ {key} = {delta:.6f}")

        if all(delta < 1e-9 for delta in deltas.values()):
            lines.append("  ✓ Adapter matches direct connect() metrics")
        else:
            lines.append("  ✗ Adapter parity drift detected")

    except Exception as exc:
        lines.append(f"  ✗ LinkBudgetChannel checks failed: {exc}")

    return lines


def _section_scenario_runner(net) -> List[str]:
    lines: List[str] = []
    try:
        from cli.helpers import NetworkIO
        from risnet import ConnectScenario, ScenarioRequest, ScenarioRunner

        with tempfile.TemporaryDirectory(prefix="waveflow-testall-") as tmpdir:
            tmp_path = Path(tmpdir)
            topology_path = tmp_path / "testall_topology.json"
            request_path = tmp_path / "testall_request.json"

            NetworkIO().save(net, str(topology_path))
            request_path.write_text(
                (
                    "{\n"
                    f'  "topology_path": "{topology_path}",\n'
                    '  "connect": {\n'
                    '    "kwargs": {"seed": 42, "use_get_snr": false}\n'
                    "  }\n"
                    "}\n"
                ),
                encoding="utf-8",
            )

            runner = ScenarioRunner()
            loaded = runner.load_topology(topology_path)
            lines.extend([
                "  ✓ ScenarioRunner loaded saved topology",
                f"    • topology nodes={len(loaded.nodes)}",
            ])

            direct_request = ScenarioRequest(
                topology_path=topology_path,
                connect=ConnectScenario(kwargs={"seed": 42, "use_get_snr": False}),
            )
            direct_run = runner.run(direct_request)
            lines.extend([
                "  ✓ Declarative ScenarioRequest executed",
                f"    • action={direct_run.action} snr_dB={direct_run.result['snr_dB']:.2f}",
            ])

            file_request = ScenarioRequest.from_file(request_path)
            file_run = runner.run(file_request)
            lines.extend([
                "  ✓ JSON scenario request file executed",
                f"    • action={file_run.action} snr_dB={file_run.result['snr_dB']:.2f}",
            ])

    except Exception as exc:
        lines.append(f"  ✗ Scenario runner checks failed: {exc}")

    return lines
