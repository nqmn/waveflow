# Waveflow Test Suite Reference

> This document is the authoritative map of what is tested, what is not, and
> what each test file covers in the current Waveflow repository. Read before
> adding tests or making changes that affect validated behavior. Update
> whenever tests are added, removed, or significantly changed.

---

## 1. Test File Inventory

Three runner types are used. **pytest** files are discovered and run
automatically by `pytest tests/`. **dual-mode** files contain normal
`def test_*` functions and are also directly executable through an optional
`if __name__ == "__main__"` runner. **manual** files are diagnostics,
benchmarks, or dataset tools that are not intended for automated pytest runs.

| File | Runner | Tests | Category | Notes |
|---|---|---|---|---|
| `test_smoke.py` | pytest | 35 | Import, CLI, entry points | Includes bare `waveflow ui` native-shell entry smoke, stateful modern-shell coverage for add/status, native no-arg `connect` parity, lifted legacy `connect` grammar coverage (positional beam angle, unified `--sweep`, shell-native execution), modern Rich diagnostic-panel coverage for native `ui connect`, native CLI engine-selection coverage for `ui connect` fallback metadata and `demo-connect --channel-model simris`, native Rich parity coverage for `ui list` preserving full topology and coordinate detail with Rich-styled legend/ASCII map, native Rich parity coverage for `ui status` preserving full node/distance/active-link detail, native Rich parity coverage for `ui links` preserving full active-link detail, and Rich panelized wrapper coverage for legacy-backed `env`, `signal`, and `stream`; plus legacy-command passthrough on the same in-memory network; Typer/Rich `ui` smoke for status/list/add/connect/save/load/links/clear/plot/env/ap/ris/ue/signal/stream; `ui add random` count/distance/no-UE parsing; live sweep rendering smoke; topology-backed terminal connect coverage; bundled topology sweep smoke; invalid-node failure handling; interactive-shell RIS-aware fallback coverage; DE result-printer compatibility; and legacy `run` passthrough coverage |
| `test_connect_characterization.py` | pytest | 30 | `RISNetwork.connect()` contract and helper services | Includes focused tests for extracted internal `connect()` helpers plus coordinate-math validation for non-collinear connect geometry metadata (incident/reflected azimuth, target angle, and deflection consistency), explicit official-SimRIS selection/fallback behavior at the `connect()` boundary, official `lightris` selector coverage, rejection of the legacy `link_budget` selector, the default SimRIS-first contract, and boundary-origin line-geometry coverage that guards the SimRIS path against pathological scatterer-generation hangs |
| `test_physics_fixes.py` | dual-mode | 5 | Physics equations, SNR bounds | pytest-compatible `def test_*` with `assert` |
| `test_array_primitives.py` | pytest | 6 | Array geometry, steering vectors | |
| `test_array_quantization.py` | pytest | 7 | Phase quantization helpers | |
| `test_lightris_channel.py` | pytest | 12 | `LightRISChannel` adapter | Covers the renamed native lightweight adapter, including explicit coverage that it pins `channel_model="lightris"` under the official engine name, that the public LightRIS helper names stay aligned with the underlying geometry-evaluation utilities, and that `waveflow.channels.lightris` re-exports the official adapter |
| `test_lightris_theory.py` | pytest | 13 | LightRIS analytical guarantees | Verifies bounded/symmetric angular deviation, bounded monotone steering loss, additive non-negative correction composition, self-consistent analytical decomposition, configuration validation/assumption surfacing, and monotone LightRIS SNR trends versus transmit power, distance, RIS size, and phase-bit resolution |
| `test_simris_channel.py` | pytest | 52 | SimRIS engine | Verifies the additive deterministic SimRIS LOS engine against published-formula reference slices, compares its received-power math against the current Waveflow link-budget path across multiple published-style geometries, and covers seeded stochastic H/G/D plus MATLAB-style `h/g/h_SISO` tensor generation, deterministic published-geometry presets for all four GUI-recommended layouts, additive published-case helper wrappers including outdoor Scenario 2 end-to-end coverage, a published-network builder with deterministic channel execution and AP/RIS frequency consistency checks, deterministic and seeded stochastic helper-consistency parity across all four presets, additive published-case adapter helpers for full `ChannelEvaluation` parity, determinism, forced LOS-only reduction behavior, seeded direct-link NLOS generation, scenario 2, UPA terminal arrays, indoor RIS→Rx LOS seed sensitivity, outdoor stochastic determinism, frozen seeded regression signatures for indoor/outdoor cases, additive MATLAB-style validation checks, optional preflight raise/report behavior on adapters, published-case entrypoints, wrapper helpers, and base primitive SimRIS APIs, plus stochastic adapter `noise_power_dBm` contract parity, self-describing stochastic result metadata (`environment`, `scenario`, `array_type`, `frequency_GHz`, `num_realizations`), per-realization stochastic channel-gain summaries, symmetric hop-level LOS path-gain/distance metadata on both deterministic and stochastic helpers, NLOS cluster/sub-ray/active-scatterer count summaries for stochastic introspection, per-realization LOS-component summaries (`los_path_gain_*`, `los_path_loss_*`, `theta_*`, `ris_pattern_*`) with explicit `NaN` behavior when LOS is absent, and first-realization scalar alias parity on the public stochastic adapter result |
| `test_scenarios.py` | pytest | 22 | Headless scenario runner and shared service adoption | Includes shared execution-service equivalence, request validation failures, golden example topology loading, API routing through the shared scenario service, official LightRIS `connect()` passthrough, and official SimRIS `connect()` passthrough via scenario kwargs |
| `test_johari2025_ris_5ghz.py` | pytest | 20 | Johari et al. (IEEE Access 2025) — 5.8 GHz 1-bit RIS | 1-bit quantization states and bounds, quantization loss (1-bit vs 2-bit), array factor steering trend, EVM↔SNR↔BER formula verification against Table 2 SDR measurements (EVM OFF=57.30%, ON=24.39%) |
| `test_simris_paper_formulas.py` | pytest | 34 | SimRIS paper formula gaps | RIS element pattern G_e(θ), path gain monotonicity, N² gain scaling (RIS-only path), LOS probability boundary conditions, `evaluate_simris_los_reference` direct call, waveflow.channels re-export smoke |
| `test_basar2020_channel_model.py` | pytest | 47 | Basar & Yildirim (2020) — indoor/outdoor mmWave channel model | Table I path-loss parameters, Eq. 4 element-pattern energy conservation, Eq. 7 indoor LOS boundaries, Eq. 11 outdoor LOS probability (UMi), Eq. 13 achievable rate formula, outdoor Fig. 4 geometry evaluation, `summarize_simris_tensors` structure, 73 GHz band validity |
| `test_simris_physics_regression.py` | pytest | 28 | SimRIS frozen physics regression | Pins exact numerical values: path-loss parameter tuples, G_e(θ) at 5 angles, path gain dB at 4 (env,d,freq) combinations, outdoor p_LOS at 5 distances, channel_gain_dB for 8 (freq,N,env) combinations + N² diff, stochastic H/G Frobenius norms (seed=0) |
| `test_johari2025_physics_regression.py` | pytest | 24 | Johari 2025 frozen physics regression | Pins exact numerical values: SNR from EVM (4.837 dB OFF, 12.256 dB ON), BER values and ratio (1959.7×), 1-bit quantization loss (−1.671 dB), 2-bit (−0.745 dB), reflection loss 20·log10(0.84)=−1.514 dB, aperture gain drop 10°→60°=−2.944 dB |
| `test_toubal2025_beam_tracking.py` | pytest | 21 | Toubal et al. (EuCNC/6G Summit 2025) — 28 GHz adaptive RIS beam tracking | Two-hop FSPL distance scaling (Eq. 6: 12 dB per doubling of both hops), RIS size benefit (40×40 vs 18×18 gain gap ≥6.9 dB), angle mismatch bound (≤2° tracking error → <1 dB steering penalty), 1-bit binary phase quantization properties, frozen numerical regression: two-hop FSPL at d_tx=0.15 m / d_rx=1.0 m = 106.29 dB, array gain 1600-element at 28 GHz = 36.31 dBi, angle loss at 2° = −0.044 dB, 1-bit sinc² loss = −1.671 dB |
| `test_burtakov2023_qris.py` | pytest | 25 | Burtakov et al. (IEEE Access 2023) — QRIS QuaDRiGa-based RIS platform | COS-UC radiation pattern G_e(θ): broadside=π, end-fire≈0, monotone, hemisphere integral≈4π; N² gain scaling: 8→16 side gives +12.041 dB, 16→32 gives +12.041 dB; frequency ordering: 73 GHz < 28 GHz indoor, 5.3 GHz < 3.7 GHz outdoor; RIS position sweet-spot: near-Tx and near-Rx better than midpoint; indoor gain exceeds outdoor at same geometry; frozen regression: G_e(45°)=2.578, indoor 28 GHz N=16 = −100.12 dB, indoor 73 GHz = −116.77 dB, outdoor 3.7 GHz = −99.55 dB, outdoor 5.3 GHz = −105.80 dB |
| `test_side_lobes.py` | dual-mode | 1 | RIS sidelobe suppression | pytest-compatible `def test_*` with `assert` |
| `test_hybrid_mode.py` | dual-mode | 4 | Hybrid phase engine | pytest-compatible `def test_*` with `assert` |
| `test_de_localization_sweep.py` | dual-mode | 3 | DE beam sweep algorithm | pytest-compatible `def test_*` with `assert` |
| `test_de_accuracy_loop.py` | dual-mode | 1 | DE convergence loop | **No assertions** — prints results only; pytest passes vacuously |
| `test_fixes.py` | dual-mode | 3 | Legacy physics regression | pytest-compatible `def test_*` with `assert` |
| `test_adaptive_with_ml.py` | manual | 0 | ML adaptive beam tracking | `run_adaptive_comparison()` only — not pytest-discoverable |
| `test_sweep_with_ml.py` | manual | 0 | ML sweep comparison | `run_sweep_comparison()` only — not pytest-discoverable |
| `test_sweep_coarse_step.py` | manual | 0 | Sweep coarse step behavior | `run_coarse_sweep_comparison()` only — not pytest-discoverable |
| `test_custom_model.py` | — | 0 | Custom ML model | Empty — no functions |
| `test_new_model.py` | — | 0 | New ML model | Empty — no functions |
| `debug_ml.py` | manual | — | ML debug | Manual only |
| `debug_ml_detailed.py` | manual | — | ML debug | Manual only |
| `evaluate_model_performance.py` | manual | — | ML model benchmarks | Manual benchmark |
| `train_custom_dataset.py` | manual | — | ML dataset generation | Manual tool |

**Issues requiring attention**:

1. `test_de_accuracy_loop.py` — `test_de_accuracy_multiple_positions()` has no
   `assert` statements. pytest collects and runs it but cannot fail on wrong
   results. It is a print-only diagnostic masquerading as a test.

2. `test_adaptive_with_ml.py`, `test_sweep_with_ml.py`, `test_sweep_coarse_step.py`
   — named `test_*.py` but contain no pytest-discoverable `def test_*` functions.
   pytest silently collects zero tests from them. They are manual benchmark scripts.

3. `test_custom_model.py`, `test_new_model.py` — empty files. Placeholder or
   leftover. Not providing any coverage.

4. `test_physics_fixes.py`, `test_hybrid_mode.py`, `test_side_lobes.py`,
   `test_fixes.py`, `test_de_localization_sweep.py` — use `def test_*` with
   `assert` but also have `if __name__ == "__main__"` runners. They work under
   both pytest and direct execution. Keep this dual-mode pattern.

## 2. Coverage by Validation Category

### 2.1 Geometry

**Covered**:
- Euclidean distance and position consistency (`test_array_primitives.py`)
- Angle convention (azimuth, `atan2`) (`test_array_primitives.py`)
- RIS element position layout (planar grid) (`test_array_primitives.py`)
- FOV rejection for opposite-direction geometry (`test_connect_characterization.py`)
- Beam miss reporting (`test_connect_characterization.py`)

**Not covered**:
- 3D coordinate transforms
- RIS normal vector in non-zero `normal_angle_deg` configurations
- Obstacle intersection geometry

---

### 2.2 Path Loss (Propagation)

**Covered**:
- FSPL consistency at multiple distances (`test_physics_fixes.py`)
- SNR noise floor and bandwidth scaling (`test_physics_fixes.py`)
- Link budget reproducibility under seeded fading (`test_connect_characterization.py`)
- `LightRISChannel` adapter reproduces `connect()` metrics (`test_lightris_channel.py`)
- Public `LightRIS` helper names (`build_lightris_config*`, `evaluate_lightris_*`) remain numerically aligned with the underlying utility layer (`test_lightris_channel.py`)
- Blocked-path propagation via environment walls (`test_lightris_channel.py`)
- Deterministic published SimRIS LOS path-gain slices for indoor Scenario 1, indoor Scenario 2, and outdoor Scenario 1, including coherent cascaded gain scaling against the current Waveflow path (`test_simris_channel.py`)
- Published SimRIS GUI geometry presets for indoor/outdoor Scenarios 1 and 2 are now exposed as a production helper and validated against MATLAB-style geometry checks (`test_simris_channel.py`)
- Published-case helper wrappers now drive deterministic and stochastic SimRIS evaluation directly from the production presets, including outdoor Scenario 2 end-to-end coverage (`test_simris_channel.py`)
- Published SimRIS network builder now constructs a `RISNetwork` directly from a GUI preset and is checked against the indoor Scenario 1 reference network plus deterministic channel execution (`test_simris_channel.py`)
- Published SimRIS network builder now also guarantees AP/RIS frequency parity for both 28 GHz and 73 GHz presets (`test_simris_channel.py`)
- Deterministic LOS helper consistency is now enforced across the published-case helper, the published-network builder, and node-level evaluation for all four GUI presets (`test_simris_channel.py`)
- Seeded stochastic helper consistency is now enforced across the published-case helper, the published-network builder, and node-level evaluation for all four GUI presets, including stable LOS-indicator metadata parity (`test_simris_channel.py`)
- Published-case adapter helpers now return full deterministic and stochastic `ChannelEvaluation` results and are checked for parity against the standard adapters on top of a built published network (`test_simris_channel.py`)
- Seeded SimRIS stochastic H/G/D tensor generation with deterministic replay and LOS-only reduction controls (`test_simris_channel.py`)
- Additive MATLAB-style `h/g` aliases now mirror deterministic and stochastic `H/G` data with shape/transposition parity checks (`test_simris_channel.py`)
- Seeded SimRIS stochastic `h_SISO` alias/output parity with the direct-channel tensor (`test_simris_channel.py`)
- Indoor RIS→Rx LOS branch now explicitly validates MATLAB-style random Rx AoA seed sensitivity (`test_simris_channel.py`)
- Additive SimRIS validation helpers now cover published-style indoor acceptance, multi-error outdoor rejection, and non-reference-frequency warnings (`test_simris_channel.py`)
- SimRIS stochastic adapter preflight now covers both failure-on-invalid and non-blocking validation-report behavior when `validate_preflight` is enabled (`test_simris_channel.py`)
- Raw SimRIS deterministic/stochastic helper APIs and published-case wrappers now mirror that optional preflight behavior, including invalid-geometry raises, non-blocking validation payloads, and published-band warning surfacing (`test_simris_channel.py`)
- Base SimRIS LOS/stochastic primitive helpers now also expose the same optional preflight raise/report behavior, including published-band warnings on the deterministic formula helper and invalid-geometry raises on the seeded tensor generator (`test_simris_channel.py`)
- Published-case adapter helpers now explicitly cover preflight warning/error reporting on their public `ChannelEvaluation` entrypoints, not just parity against built-network adapters (`test_simris_channel.py`)
- SimRIS stochastic adapters now explicitly expose `noise_power_dBm` and preserve the `snr_dB = pwr_dBm - noise_power_dBm` contract just like the deterministic adapter (`test_simris_channel.py`)
- Seeded stochastic SimRIS results now also preserve self-describing configuration metadata (`environment`, `scenario`, `array_type`, `frequency_GHz`, `num_realizations`) on the raw helper output (`test_simris_channel.py`)
- Seeded stochastic SimRIS helpers now expose per-realization `channel_gain_linear` / `channel_gain_dB` summaries, and the stochastic adapter reuses the first realization instead of recomputing it independently (`test_simris_channel.py`)
- Deterministic and LOS-only stochastic SimRIS helpers now both carry per-hop `distance_m` plus LOS path-gain summaries for Tx→RIS, RIS→Rx, and Tx→Rx, and those summaries are checked for parity (`test_simris_channel.py`)
- Stochastic SimRIS metadata now also surfaces NLOS structure summaries (`nlos_cluster_count`, `nlos_subray_count`, `nlos_active_scatterer_count`) for indoor shared-cluster and outdoor scattered branches (`test_simris_channel.py`)
- Stochastic SimRIS helpers now also expose LOS-component per-realization summaries (`los_path_gain_*`, `los_path_loss_*`, `theta_*`, `ris_pattern_*`) and explicitly report `NaN` when a LOS component is forced off (`test_simris_channel.py`)
- The public stochastic SimRIS adapter now exposes first-realization scalar aliases for path gain/loss, RIS angles, and RIS pattern summaries, and these are tested for deterministic parity and no-LOS `NaN` semantics (`test_simris_channel.py`)
- Seeded SimRIS indoor direct-link NLOS generation when LOS is forced off, plus zero-direct-path behavior when both LOS and NLOS are disabled (`test_simris_channel.py`)
- SimRIS scenario 2 branch, square-antenna UPA terminal arrays, and outdoor stochastic replay under fixed seeds (`test_simris_channel.py`)
- Frozen indoor/outdoor seeded SimRIS tensor signatures guard against unintended drift in the current Python port (`test_simris_channel.py`)

- SimRIS Table I path-loss parameters (n, σ, b, f₀) for all four scenarios pinned as exact regression values (`test_simris_physics_regression.py`)
- SimRIS path gain dB at canonical (env, d, freq) combinations, no shadow (`test_simris_physics_regression.py`)
- Outdoor UMi LOS probability formula (Eq. 11) numerical values at 5 distances (`test_basar2020_channel_model.py`, `test_simris_physics_regression.py`)
- Indoor LOS probability boundary values at d=1.2 m and d=6.5 m (Eq. 7) (`test_basar2020_channel_model.py`)
- EVM↔SNR formula (SNR = −20·log10(EVM_rms)) verified against Johari 2025 Table 2 through production `Physics.evm_to_snr_dB()` / `Physics.snr_to_evm()` utilities (`test_johari2025_ris_5ghz.py`, `test_johari2025_physics_regression.py`)
- BER from EVM for QPSK (Eq. 10 Johari 2025 approximation) verified through production `Physics.ber_qpsk_from_evm()` (`test_johari2025_ris_5ghz.py`, `test_johari2025_physics_regression.py`)
- Reflection loss from measured |Γ|=0.84 (`test_johari2025_physics_regression.py`)
- Aperture gain drop cos(θ) law from 10°→60° (`test_johari2025_physics_regression.py`)

**Not covered**:
- Analytical Friis equation cross-check at specific frequencies (2.4/5.8/28/60 GHz)
- Atmospheric loss verification against ITU model
- Multi-hop cascaded path loss

---

### 2.3 RIS Beamforming

**Covered**:
- Beam sweep consistency — best angle is reproducible (`test_physics_fixes.py`)
- RIS gain no double-count (`test_physics_fixes.py`)
- Linear steering phases match existing phase engine (`test_array_primitives.py`)
- Phase quantization error and RMS (`test_array_quantization.py`, `test_fixes.py`)
- Quantization loss matches `Physics.quantization_loss_dB()` (`test_array_quantization.py`)
- Sidelobe suppression behavior (`test_side_lobes.py`)
- Hybrid phase engine selection and RIS node integration (`test_hybrid_mode.py`)
- DE sweep finds valid beam angle (`test_de_localization_sweep.py`)

- RIS element pattern G_e(θ) = π·cos(θ)^(2·0.285) at 5 angles including endfire (`test_simris_paper_formulas.py`, `test_simris_physics_regression.py`)
- Element-pattern energy-conservation normalization — hemisphere integral ≈ 4π, broadside gain ≈ 5 dBi (`test_basar2020_channel_model.py`)
- N² gain scaling (RIS-only path, N_side 8→16 gives ~12.04 dB) (`test_simris_paper_formulas.py`, `test_simris_physics_regression.py`)
- 1-bit quantization states {0, π} and max error bound = 90° (`test_johari2025_ris_5ghz.py`, `test_johari2025_physics_regression.py`)
- channel_gain_dB frozen for 8 (freq, N_side, env) combinations at published paper geometries (`test_simris_physics_regression.py`)

**Not covered**:
- Beam peak angle vs analytical array factor — direct numerical comparison
- Beamwidth vs element count
- Near-field focusing accuracy (Fraunhofer transition)

---

### 2.4 Phase Quantization

**Covered**:
- Uniform phase levels match existing quantizer (`test_array_quantization.py`)
- Phase state mapping consistency (`test_array_quantization.py`)
- Uniform quantization matches `Physics.quantization_loss_dB()` (`test_array_quantization.py`)
- Wrapped phase error convention (`test_array_quantization.py`)
- Quantization loss at 1–4 bits (`test_physics_fixes.py`)

- Quantization loss at 1-bit (−1.671 dB) and 2-bit (−0.745 dB) frozen as regression values (`test_johari2025_physics_regression.py`)
- 1-bit phase state mapping verified for canonical 5-element input (`test_johari2025_physics_regression.py`)
- `validate_quantization_error` status and max_allowed_deg bound for 1-bit (`test_johari2025_physics_regression.py`)

**Not covered**:
- Quantization loss against closed-form formula:
  `L_q = (π / 2^b)² / 3` (dB equivalence)

---

### 2.5 OFDM / Waveform

**Covered**:
- Waveform SNR computation runs without error (implicit via `test_smoke.py`)

**Not covered**:
- Subcarrier orthogonality (leakage < −40 dB)
- FFT/IFFT round-trip consistency
- PAPR distribution
- EVM under ideal channel
- Per-subcarrier SNR variance

---

### 2.6 Statistical Fading / Noise

**Covered**:
- SNR noise floor formula (`test_physics_fixes.py`)
- Seeded fading determinism (`test_connect_characterization.py`)
- LightRIS steering-mismatch loss is bounded, symmetric, and monotone in angular deviation; the aggregate analytical correction term is non-negative and additive (`test_lightris_theory.py`)
- LightRIS SNR trends are monotone in transmit power, distance, RIS element count, and phase-bit resolution on the supported analytical model (`test_lightris_theory.py`)

**Not covered**:
- Rician fading PDF matches target K-factor distribution
- Rayleigh fading (not yet implemented)
- Nakagami fading (not yet implemented)
- Noise figure scaling with bandwidth

---

### 2.7 Channel Adapter (LightRISChannel)

**Covered**:
- Reproduces `connect()` SNR, power, RSSI, gain, quant_loss
- Pins `channel_model="lightris"` explicitly so the native lightweight adapter remains on the official non-SimRIS engine even though `connect()` now prefers SimRIS by default
- Phase payload shape preserved
- Deterministic for seeded links
- No active-link mutation by default
- Legacy active-link mutation opt-in
- Missing-node error propagation
- FOV rejection propagation
- Environment-blocked path behavior
- Shared `utils.lightris` helper/re-export compatibility with `risnet.channels`
- Additive deterministic SimRIS LOS adapter returns channel matrices (`H`, `G`, `D`) and matches the published-formula reference slice more closely than the current link-budget path for the covered geometry
- Additive stochastic SimRIS adapter returns seeded `H`, `G`, `D` tensors and preserves deterministic replay under fixed seeds

---

### 2.8 Scenario Runner

**Covered**:
- JSON topology loads without Flask or CLI
- Golden example topology loading for simple, obstacle, and grid examples
- Auto-resolves first AP/RIS/UE by type
- Explicit name resolution
- Reports missing node type clearly
- Scenario `connect` kwargs can now select the official `lightris` or `simris` engine and receive the corresponding metadata/payload back through the shared service layer
- `ScenarioRequest` from dict
- `ScenarioRequest` from JSON file
- `ScenarioRequest` from YAML file
- Rejects mixed `actions` with top-level `connect`/`sweep`
- Rejects malformed `kwargs` payloads
- Rejects empty `topology_path`
- Mixed connect + sweep action list on shared network
- Missing `connect`/`actions` raises `ValueError`
- Sweep via `run_sweep()` and via request schema
- `ScenarioExecutionService` matches `ScenarioRunner` connect/sweep behavior
- Flask API `connect` and `sweep` routes execute via the shared scenario service layer

---

### 2.9 Connect Contract

**Covered**:
- Public result shape (all expected keys present)
- Default `connect()` now requests the official SimRIS engine first and falls back explicitly to `lightris` when the request is unsupported
- Explicit `channel_model="lightris"` requests now route through the official native lightweight engine name
- Legacy `channel_model="link_budget"` requests are rejected at the `connect()` boundary as part of the LightRIS refactor
- Explicit `channel_model="simris"` requests now route through the official SimRIS engine when the request is supported and expose `channel_model_requested` / `channel_model_used` metadata
- Unsupported explicit SimRIS requests now fall back to the official `lightris` path with an explicit `channel_model_fallback_reason`
- Deterministic under fixed seed
- `active_links` and `last_connect_result` updated by default
- `store_in_active_links=False` skips link mutation
- `compute_phases=True` persists phase data to RIS node
- `compute_phases=False` omits phase payload
- Missing-node error message format
- FOV rejection for collinear (opposite-direction) geometry
- Beam miss reporting with directional-loss SNR
- Non-collinear geometry metadata matches direct coordinate math for incident azimuth, reflected azimuth, target angle, and signed deflection
- Extracted helper services for node resolution, geometry/FOV prep, phase
  computation, phase payload persistence, result assembly, feedback persistence,
  metadata persistence, messaging override resolution, active-link persistence,
  last-result persistence, link-budget prep, and SNR evaluation

---

### 2.10 Import and CLI Smoke

**Covered**:
- `from waveflow import RISnet` and `from risnet import RISnet` succeed
- `python -m risnet --help` and `waveflow --help` exit cleanly
- bare `waveflow ui` opens the native interactive shell and accepts commands over stdin
- `waveflow ui shell` keeps modern-command state in memory and can still delegate unsupported commands through the legacy handler on that same state
- native `waveflow ui shell` `connect` accepts zero explicit node arguments, auto-detects AP/RIS/UE, and renders the modern link-result path without Typer missing-argument failures
- `waveflow ui status`, `list`, and `demo-connect` run from outside repo root
- `waveflow ui status` natively reproduces the legacy node, distance, and active-link detail with Rich tables instead of a shortened summary
- `waveflow ui list` natively reproduces the legacy topology ASCII view and node-coordinate detail with Rich output, without shortening the content
- native `waveflow ui list` styles the legacy-parity ASCII topology map and legend through Rich while preserving the original map shape
- `waveflow ui links` natively reproduces the active-link listing with Rich tables; only `links plot ...` remains on the legacy-backed plot path
- `waveflow ui env` reports environment details from a loaded topology
- legacy-backed `waveflow ui` wrappers such as `env`, `signal`, `stream`, and `links` render their captured output inside Rich panels instead of raw legacy text
- `waveflow ui ap|ris|ue ... show` surfaces node details through explicit UI wrappers
- `waveflow ui add random` creates a one-AP/one-RIS/one-UE topology from outside repo root
- `waveflow ui add random` accepts AP/RIS/UE counts, `--distance min-max`, and `--no-ue`
- `waveflow ui connect` runs against a topology file through the shared scenario service path
- `waveflow ui connect` accepts lifted legacy positional beam-angle and seed syntax while rendering the modern link-result table
- native `waveflow ui connect` renders Rich diagnostic panels for geometry, context, and RIS steering recommendation
- `waveflow ui shell` accepts legacy `connect --sweep ...` grammar through the native command path without dropping back to legacy narrated output
- `waveflow ui signal` exposes per-hop breakdowns through an explicit UI wrapper
- `waveflow ui stream` delegates through the explicit UI wrapper and surfaces file errors cleanly
- `waveflow ui save` and `load` round-trip a topology JSON
- `waveflow ui links` renders stored active links from a saved state file
- `waveflow ui demo-connect` now accepts `--channel-model simris` and surfaces engine metadata in its output table
- native `waveflow ui connect` now surfaces requested/used/fallback engine metadata when a SimRIS request falls back to `lightris`
- `waveflow ui clear links` executes against a saved state file
- `waveflow ui plot ... --type connect --out ...` saves a connect-metrics plot from a saved state file
- `waveflow ui sweep` renders the Rich live/table UX from outside repo root
- `examples/json/example_1_simple.json` remains sweep-safe for `waveflow ui sweep`
- `waveflow ui sweep` fails cleanly on missing AP/RIS/UE names before opening the live Rich UI
- `waveflow ui run` passes legacy trailing flags like `--breakdown` through to the interactive-shell command handler
- Interactive shell RIS-aware UE placement falls back to unconstrained placement when the AP is outside the RIS deflection capability
- Legacy unified sweep result printing accepts DE-style NumPy measurement payloads without ambiguous truth-value failures
- Minimal `RISNetwork.connect()` smoke run
- `examples/script/example_19_hog_human_detection.py` imports successfully and builds a demo network using current public APIs

---

## 3. Not Yet Tested (Validation Gaps)

The following items are intended validation targets for Waveflow but do not yet
have automated test coverage in the current repo:

| Area | Gap |
|---|---|
| SimRIS parity | Full MATLAB v18 parity incomplete: exact branch-by-branch numerical equivalence and true MATLAB/Octave golden-output comparison remain unvalidated |
| Friis equation cross-check | No test computes FSPL analytically and compares at specific GHz frequencies |
| Near-field transition | Fraunhofer boundary detection is implemented; behavior not tested |
| OFDM orthogonality | No subcarrier leakage test |
| EVM under ideal channel | No EVM measurement under simulated AWGN/Rician channel (only from paper SDR measurements) |
| Rician PDF distribution | Statistical PDF test not implemented |
| Doppler shift | Not implemented in core |
| Mobility/temporal coherence | Not implemented in core |
| Multi-hop RIS (BS→RIS1→RIS2→UE) | Not implemented in core |
| Localization RMSE/CDF metrics | No systematic localization accuracy test |
| `waveflow validate` CLI | Not implemented |
| Live sweep progress contract | Only smoke-covered for `linear`; broader event compatibility across sweep algorithms is not yet validated |
| Cross-simulator comparison | Manual/aspirational only |

These are future test targets, ordered by proximity to current implementation.

---

## 4. Running the Test Suite

### Compile check (no extras required)

```bash
python3 -m compileall core controller cli risnet waveflow config utils
```

### Baseline automated suite (dev extras required)

These files are fully pytest-native and will fail correctly on wrong results:

```bash
pip install -e ".[dev]"
pytest tests/test_smoke.py \
       tests/test_connect_characterization.py \
       tests/test_physics_fixes.py \
       tests/test_array_primitives.py \
       tests/test_array_quantization.py \
       tests/test_lightris_channel.py \
       tests/test_scenarios.py \
       tests/test_johari2025_ris_5ghz.py \
       tests/test_simris_paper_formulas.py \
       tests/test_basar2020_channel_model.py \
       tests/test_simris_physics_regression.py \
       tests/test_johari2025_physics_regression.py -v
```

### Direct-execution checks (no optional extras required)

```bash
PYTHONPATH=. python3 tests/test_physics_fixes.py
PYTHONPATH=. python3 tests/test_hybrid_mode.py
PYTHONPATH=. python3 tests/test_side_lobes.py
PYTHONPATH=. python3 tests/test_de_localization_sweep.py
PYTHONPATH=. python3 tests/test_fixes.py
```

### Manual benchmark scripts (not for CI)

```bash
PYTHONPATH=. python3 tests/test_sweep_coarse_step.py
PYTHONPATH=. python3 tests/test_adaptive_with_ml.py   # requires [ml]
PYTHONPATH=. python3 tests/test_sweep_with_ml.py      # requires [ml]
PYTHONPATH=. python3 tests/test_de_accuracy_loop.py   # prints only, no assertions
```

### Terminal UI test suite

```bash
waveflow ui testall
```

`waveflow ui testall` is a built-in diagnostic suite, not a replacement for the
full pytest matrix. It now exercises:

- network setup and node inventory
- AP→RIS→UE link validation and link budget reporting
- connect-contract health checks (`active_links`, `last_connect_result`,
  required result keys, missing-node error path)
- beam sweep diagnostics
- phase and quantization diagnostics
- waveform diagnostics
- `LightRISChannel` parity against direct `connect()`
- `ScenarioRunner` loading plus declarative request execution

### Full pytest run (collects all discoverable automated tests)

```bash
pip install -e ".[all]"
pytest tests/ -v
# Note: test_adaptive_with_ml, test_sweep_with_ml, test_sweep_coarse_step
# will show "no tests ran" — expected, they are script-mode benchmarks.
```

### Known expected failure

No known expected failures are documented in the current baseline suite.

---

## 5. Adding New Tests

1. Place test files in `tests/` following the naming pattern `test_<area>.py`.
2. Update the **File Inventory** table in this document.
3. Update the **Coverage** section for the relevant validation category.
4. Remove the gap from **Section 3** if it is now covered.
5. If the test requires optional extras, mark it in the inventory with
   `(ML extras required)` or equivalent.

---

## 6. Tolerance Reference

Current Waveflow validation targets referenced by this document:

| Metric | Target |
|---|---|
| Path loss | < 0.5 dB error |
| RIS beam peak angle | < 1° |
| Phase accumulation | < 0.01 rad |
| OFDM orthogonality leakage | < −40 dB |
| CSI amplitude error | < 1% |
| Delay estimation | < 1 ns |
| Doppler shift | < 1 Hz |

Tolerances for path loss and phase quantization are enforced in
`test_physics_fixes.py` and `test_array_quantization.py`. Others are not yet
enforced.
