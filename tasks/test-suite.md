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
| `test_smoke.py` | pytest | 7 | Import, CLI, entry points | |
| `test_connect_characterization.py` | pytest | 13 | `RISNetwork.connect()` contract | |
| `test_physics_fixes.py` | dual-mode | 5 | Physics equations, SNR bounds | pytest-compatible `def test_*` with `assert` |
| `test_array_primitives.py` | pytest | 6 | Array geometry, steering vectors | |
| `test_array_quantization.py` | pytest | 7 | Phase quantization helpers | |
| `test_link_budget_channel.py` | pytest | 8 | `LinkBudgetChannel` adapter | |
| `test_scenarios.py` | pytest | 11 | Headless scenario runner | |
| `test_side_lobes.py` | dual-mode | 1 | RIS sidelobe suppression | pytest-compatible `def test_*` with `assert` |
| `test_hybrid_mode.py` | dual-mode | 4 | Hybrid phase engine | pytest-compatible `def test_*` with `assert` |
| `test_de_localization_sweep.py` | dual-mode | 3 | DE beam sweep algorithm | pytest-compatible `def test_*` with `assert` |
| `test_de_accuracy_loop.py` | dual-mode | 1 | DE convergence loop | **No assertions** — prints results only; pytest passes vacuously |
| `test_fixes.py` | dual-mode | 3 | Legacy physics regression | pytest-compatible `def test_*` with `assert`; TEST 3 stale |
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

**Known stale failure**: `test_fixes.py` TEST 3 (RMS Phase Error with Angle
Wrapping) has a stale expected value. One failure is expected until Phase 1
resolves it. Do not suppress with `xfail`; fix the expectation.

---

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
- `LinkBudgetChannel` adapter reproduces `connect()` metrics (`test_link_budget_channel.py`)
- Blocked-path propagation via environment walls (`test_link_budget_channel.py`)

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

**Not covered**:
- Beam peak angle vs analytical array factor — direct numerical comparison
- Coherent gain scaling: verify G ∝ N² across N values
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

**Not covered**:
- Rician fading PDF matches target K-factor distribution
- Rayleigh fading (not yet implemented)
- Nakagami fading (not yet implemented)
- Noise figure scaling with bandwidth

---

### 2.7 Channel Adapter (LinkBudgetChannel)

**Covered**:
- Reproduces `connect()` SNR, power, RSSI, gain, quant_loss
- Phase payload shape preserved
- Deterministic for seeded links
- No active-link mutation by default
- Legacy active-link mutation opt-in
- Missing-node error propagation
- FOV rejection propagation
- Environment-blocked path behavior

---

### 2.8 Scenario Runner

**Covered**:
- JSON topology loads without Flask or CLI
- Auto-resolves first AP/RIS/UE by type
- Explicit name resolution
- Reports missing node type clearly
- `ScenarioRequest` from dict
- `ScenarioRequest` from JSON file
- `ScenarioRequest` from YAML file
- Mixed connect + sweep action list on shared network
- Missing `connect`/`actions` raises `ValueError`
- Sweep via `run_sweep()` and via request schema

---

### 2.9 Connect Contract

**Covered**:
- Public result shape (all expected keys present)
- Deterministic under fixed seed
- `active_links` and `last_connect_result` updated by default
- `store_in_active_links=False` skips link mutation
- `compute_phases=True` persists phase data to RIS node
- `compute_phases=False` omits phase payload
- Missing-node error message format
- FOV rejection for collinear (opposite-direction) geometry
- Beam miss reporting with directional-loss SNR

---

### 2.10 Import and CLI Smoke

**Covered**:
- `from waveflow import RISnet` and `from risnet import RISnet` succeed
- `python -m risnet --help` and `waveflow --help` exit cleanly
- `waveflow ui status` and `waveflow ui demo-connect` run from outside repo root
- Minimal `RISNetwork.connect()` smoke run

---

## 3. Not Yet Tested (Validation Gaps)

The following items are intended validation targets for Waveflow but do not yet
have automated test coverage in the current repo:

| Area | Gap |
|---|---|
| Friis equation cross-check | No test computes FSPL analytically and compares at specific GHz frequencies |
| Coherent gain G ∝ N² | No test verifies gain scaling across N values |
| Near-field transition | Fraunhofer boundary detection is implemented; behavior not tested |
| OFDM orthogonality | No subcarrier leakage test |
| EVM under ideal channel | No EVM measurement in tests |
| Rician PDF distribution | Statistical PDF test not implemented |
| Doppler shift | Not implemented in core |
| Mobility/temporal coherence | Not implemented in core |
| Multi-hop RIS (BS→RIS1→RIS2→UE) | Not implemented in core |
| Localization RMSE/CDF metrics | No systematic localization accuracy test |
| `waveflow validate` CLI | Not implemented |
| Cross-simulator comparison | Manual/aspirational only |
| Measurement validation | Manual/aspirational only |

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
       tests/test_link_budget_channel.py \
       tests/test_scenarios.py -v
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

### Full pytest run (collects all discoverable automated tests)

```bash
pip install -e ".[all]"
pytest tests/ -v
# Note: test_adaptive_with_ml, test_sweep_with_ml, test_sweep_coarse_step
# will show "no tests ran" — expected, they are script-mode benchmarks.
```

### Known expected failure

`tests/test_fixes.py` TEST 3 (`test_rms_phase_error`) — stale expected value.
One failure is expected until Phase 1 resolves it. Do not suppress with
`xfail`; fix the expectation.

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
