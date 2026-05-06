# Waveflow Test Suite Reference

> This document is the authoritative map of what is tested, what is not, and
> what each test file covers. Read before adding tests or making changes that
> affect validated behavior. Update whenever tests are added, removed, or
> significantly changed.

---

## 1. Test File Inventory

| File | Category | Status |
|---|---|---|
| `test_smoke.py` | Import, CLI, entry points | Active |
| `test_connect_characterization.py` | `RISNetwork.connect()` contract | Active |
| `test_physics_fixes.py` | Physics equations, SNR bounds | Active |
| `test_array_primitives.py` | Array geometry and steering vectors | Active |
| `test_array_quantization.py` | Phase quantization helpers | Active |
| `test_link_budget_channel.py` | `LinkBudgetChannel` adapter | Active |
| `test_scenarios.py` | Headless scenario runner | Active |
| `test_side_lobes.py` | RIS sidelobe suppression | Active |
| `test_hybrid_mode.py` | Hybrid phase engine | Active |
| `test_de_localization_sweep.py` | DE beam sweep algorithm | Active |
| `test_de_accuracy_loop.py` | DE convergence loop | Active |
| `test_fixes.py` | Legacy physics regression | Active (TEST 3 stale — see note) |
| `test_adaptive_with_ml.py` | ML adaptive beam tracking | Active (ML extras required) |
| `test_sweep_with_ml.py` | ML sweep algorithms | Active (ML extras required) |
| `test_sweep_coarse_step.py` | Sweep coarse step behavior | Active |
| `debug_ml.py` | ML debug scripts | Not a test runner — manual only |
| `debug_ml_detailed.py` | ML debug scripts | Not a test runner — manual only |
| `evaluate_model_performance.py` | ML model benchmarks | Manual benchmark — not CI |
| `train_custom_dataset.py` | ML dataset generation | Manual tool — not CI |
| `test_custom_model.py` | Custom ML model | Active (ML extras required) |
| `test_new_model.py` | New ML model | Active (ML extras required) |

**Known stale failure**: `test_fixes.py` TEST 3 (RMS Phase Error with Angle
Wrapping) has a stale expected value. It reports one failure in the current
implementation. Fix target: Phase 1 (see `FUTURE.md`).

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

The following items appear in `VALIDATION.md` but have no automated test coverage:

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

### Minimum (no extras required)

```bash
# Compile check
python3 -m compileall core controller cli risnet waveflow config utils

# Physics regression
PYTHONPATH=. python3 tests/test_physics_fixes.py

# Full baseline
pip install -e ".[dev]"
pytest tests/test_smoke.py tests/test_connect_characterization.py \
       tests/test_physics_fixes.py tests/test_array_primitives.py \
       tests/test_array_quantization.py tests/test_link_budget_channel.py \
       tests/test_scenarios.py -v
```

### Terminal UI

```bash
waveflow ui testall
```

### Full suite (all extras)

```bash
pip install -e ".[all]"
pytest tests/ -v
```

### Known expected failure

`tests/test_fixes.py::test_rms_phase_error` — stale expected value. One failure
is expected until Phase 1 resolves it. Do not suppress with `xfail`; fix the
expectation.

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

From `VALIDATION.md` — current targets:

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
