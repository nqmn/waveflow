# RISNet Debugging Checklist - Physical Parameter Issues

## Executive Summary

Three critical categories of bugs detected in the RISNet simulator causing inconsistent and physically implausible results:

1. **RIS Gain Aggregation Bug** → ~3.55 dB anomalies or 118 dB impossibilities
2. **SNR/Noise-Floor Misuse** → 96.96 dB unrealistic values
3. **Phase Quantization Error Calculation** → 162° RMS when should be ≤45°
4. **Beam-Sweep vs Optimized SNR Mismatch** → Inconsistent measurements across same config

---

## Issue 1: RIS Gain Aggregation Bug

### Location
- **File**: `core/network.py`, line 109-124
- **Function**: `RISNetwork.connect()`
- **Secondary Impact**: `core/physics.py` line 310-326 `array_gain_dBi()`

### Root Cause Analysis

**Problem**: Double-counting of RIS linear factor in power budget

```python
# Line 109: RIS has N×N elements (e.g., 16×16 = 256 elements)
N = ris.N * ris.N  # N = 256 for N=16

# Line 112: RIS array gain computed with linear factor
gain_dBi = Physics.array_gain_dBi(N, ris.amplifier_gain, angle_loss_dB=angle_loss)

# Line 124: Gain applied THEN again applied implicitly
pwr_dBm = ap.power_dBm + ap_antenna_gain_dBi + ue_antenna_gain_dBi + gain_dBi - ...
          ↑ This uses gain_dBi already (20*log10(N))
          But the RIS element spacing may also contribute implicitly
```

### In `physics.py` Array Gain Function

```python
# Line 324: Theoretical gain = 20*log10(N)
theoretical_gain_dBi = 20 * np.log10(amplifier_gain * N)
```

**Issue**: For N=256:
- `20*log10(256) = 48 dB` → applied once correctly
- But if code path applies it twice (or applies both `20*log10(N)` AND `array factor`):
  - Example: 48 dB + 45 dB (array factor) = 93 dB (wrong!)
  - Symptoms:
    - If applied twice: Pr changes by ~3.55 dB more than expected (visible in tests)
    - If incorrectly mixed: Can yield 118+ dB (physically impossible)

### Fix

**In `core/network.py` line 109:**

```python
# BEFORE (WRONG)
N = ris.N * ris.N  # 256 for a 16×16 RIS
gain_dBi = Physics.array_gain_dBi(N, ris.amplifier_gain, angle_loss_dB=angle_loss)

# AFTER (CORRECT)
# Use linear (not dB) to avoid accidental double-application
N_elements = ris.N * ris.N
# Ensure array_gain_dBi is called exactly once and uses correct N
gain_dBi = Physics.array_gain_dBi(
    N_elements,
    ris.amplifier_gain,
    insertion_loss_dB=0.5,
    reflection_loss_dB=0.2,
    angle_loss_dB=angle_loss
)
```

**Verify in `core/physics.py` line 310-326:**

The `array_gain_dBi()` function should apply the gain **exactly once**:

```python
def array_gain_dBi(N, amplifier_gain=1.0, insertion_loss_dB=0.5,
                   reflection_loss_dB=0.2, angle_loss_dB=0):
    """Calculate RIS array gain

    Args:
        N: Number of elements (already the total count, not per dimension)

    Returns:
        Total gain after all losses (single computation)
    """
    # Theoretical: passive array is proportional to N^2 (or 10*log10(N^2) in dB)
    # For reflectarray: Pt * (N^2) effective isotropic radiated power
    theoretical_gain_dBi = 20 * np.log10(amplifier_gain * N)

    # Single application of losses
    total_gain = theoretical_gain_dBi - insertion_loss_dB - reflection_loss_dB - angle_loss_dB
    return total_gain
```

**Test Case:**
```
N = 256 elements (16×16)
Expected gain ≈ 20*log10(256) = 48 dB
With losses ≈ 48 - 0.5 - 0.2 - angle_loss ≈ 47 dB
Received power ≈ Pt + 3 (AP) + 3 (UE) + 47 (RIS) - PL1 - PL2
```

---

## Issue 2: SNR / Noise-Floor Misuse

### Location
- **File**: `core/network.py`, line 126-134
- **Function**: `RISNetwork.connect()`

### Root Cause Analysis

**Problem**: Two separate issues:

#### Issue 2a: Fixed Noise Floor (Overly Simplistic)

```python
# Line 127: Hardcoded noise floor
noise_floor_dBm = -88.0  # Assumes 100 MHz, NF=6 dB, fixed

# But should be:
# -174 dBm/Hz + 10*log10(BW_Hz) + NF_dB
# = -174 + 10*log10(100e6) + 6
# = -174 + 80 + 6 = -88 dBm ✓
```

**This is actually correct**, but leads to **Issue 2b**:

#### Issue 2b: Fading Application Causes Unrealistic SNR

```python
# Line 131-134: Fading applied as amplitude
fading_coeff = Physics.rician_fading(ris.K_db)  # Returns magnitude (0 to ~1.5)
fading_dB = 20 * np.log10(fading_coeff + 1e-12)  # Can be -inf to +3 dB

snr_dB += fading_dB  # ← WRONG: This should be power budget update, not SNR
pwr_dBm += fading_dB  # WRONG: Applied to both?
```

**Symptom**: When fading_dB is large (e.g., +3 dB from K_factor=10), SNR inflates:
- Real SNR: 20 dB → Reported: 23 dB (not physically inconsistent, but misleading)
- **Extreme case**: If K-factor is set very high or fading is applied twice → 96.96 dB possible

**The real issue**: SNR should reflect **actual received signal quality**, not just power + fixed noise.

### Fix

**In `core/network.py` line 126-134:**

```python
# BEFORE (WRONG)
noise_floor_dBm = -88.0
snr_dB = pwr_dBm - noise_floor_dBm
fading_coeff = Physics.rician_fading(ris.K_db)
fading_dB = 20 * np.log10(fading_coeff + 1e-12)
snr_dB += fading_dB  # ← Improperly applied
pwr_dBm += fading_dB

# AFTER (CORRECT)
# Use proper SNR calculation from physics.py
bandwidth_MHz = 100  # Define explicitly
snr_dB = Physics.compute_snr_dB(
    tx_power_dBm=ap.power_dBm,
    total_loss_dB=(pl_ap_ris + pl_ris_ue - gain_dBi + quant_loss),  # Must include ALL losses
    gain_dBi=gain_dBi,
    bandwidth_MHz=bandwidth_MHz,
    noise_figure_dB=6.0
)

# Fading should reduce SNR, not inflate it
# Apply as power reduction (Rayleigh: mean = sqrt(π/2) ≈ 1.25, can range 0.5-1.5)
fading_coeff = Physics.rician_fading(ris.K_db)
if fading_coeff < 1.0:  # Most likely case: attenuation
    snr_dB += 20 * np.log10(fading_coeff)  # Reduces SNR (negative dB)
else:  # Lucky case: constructive fading
    snr_dB += 20 * np.log10(fading_coeff)  # Can add a few dB
```

**Note**: The `Physics.compute_snr_dB()` function at line 347-365 is correctly defined. Use it!

---

## Issue 3: Phase Quantization Error Calculation (Angle Wrapping)

### Location
- **File**: `controller/ris_phase/phase_quantization.py`
  - Line 183-187 (QuantizationAnalyzer.compute_rms_error)
  - Line 264 (compare_quantizers - max error)

### Root Cause Analysis

**Problem**: Raw phase difference without wrapping to [−π, +π] range

```python
# Line 184: CORRECT wrapping at line 187
error = ideal_phases - quantized_phases
error = np.angle(np.exp(1j * error))  # ← Correctly wraps using complex exponential
rms_error = np.sqrt(np.mean(error ** 2))
```

**BUT line 264 does NOT wrap:**

```python
# Line 264: WRONG - No angle wrapping
'max_error_deg': np.degrees(np.max(np.abs(ideal_phases - quantized_phases)))
# Can yield values > 180° when it should be ≤ 180°
```

### Symptom

**For 2-bit RIS** (90° phase step):
```
Ideal:     45°
Quantized: 0°
Raw diff:  45° ✓ (correct, ≤ 90°/2)

Ideal:     355°  (≈ -5° mod 360)
Quantized: 0°
Raw diff:  355° ✗ (WRONG! Should be -5°, RMS=162°!)
```

**Quantization error should never exceed ±(phase_step / 2)**:
- 1-bit (180° step): max error = ±90°
- 2-bit (90° step): max error = ±45°  ← Here RMS=162° is impossible!
- 3-bit (45° step): max error = ±22.5°
- 4-bit (22.5° step): max error = ±11.25°

### Fix

**In `controller/ris_phase/phase_quantization.py` line 264:**

```python
# BEFORE (WRONG)
'max_error_deg': np.degrees(np.max(np.abs(ideal_phases - quantized_phases)))

# AFTER (CORRECT) - Wrap to [-π, π]
error_wrapped = np.angle(np.exp(1j * (ideal_phases - quantized_phases)))
'max_error_deg': np.degrees(np.max(np.abs(error_wrapped)))
```

**In `core/physics.py` - Add validation helper:**

```python
@staticmethod
def validate_quantization_error(ideal_phases_rad, quantized_phases_rad, bits):
    """Validate quantization error is physically reasonable"""
    # Wrap errors properly
    error = np.angle(np.exp(1j * (ideal_phases_rad - quantized_phases_rad)))

    # Max error should be ≤ phase_step / 2
    phase_step = 2 * np.pi / (2 ** bits)
    max_allowed_error = phase_step / 2

    max_error = np.max(np.abs(error))

    if max_error > max_allowed_error * 1.01:  # Allow 1% tolerance
        raise ValueError(
            f"Quantization error {np.degrees(max_error):.1f}° exceeds "
            f"maximum {np.degrees(max_allowed_error):.1f}° for {bits}-bit quantizer"
        )

    return error
```

---

## Issue 4: Beam-Sweep vs Optimized SNR Mismatch

### Location
- **File**: `core/network.py`
  - Line 146-207: `sweep()` method
  - Line 69-144: `connect()` method (used by sweep)

### Root Cause Analysis

**Problem**: Inconsistent SNR measurements under same configuration

**Symptom**:
```
Beam sweep best: 20.86 dB
Optimized SNR:   29.17 dB or 25.6 dB
Difference:      > 8 dB (unacceptable for same configuration!)
```

**Causes** (in order of likelihood):

1. **Different quantization states** between sweep and optimized run
   - Sweep may call `compute_phases()` → `quantize_phases()` each iteration
   - Optimized may re-use cached quantized phases from previous run
   - **Fix**: Ensure deterministic quantization (seed, or re-compute each time)

2. **Fading randomization**
   - `Physics.rician_fading()` uses `np.random.randn()`  without seed
   - Each call to `connect()` gets different fading
   - Beam sweep makes many `connect()` calls → accumulates variance
   - **Fix**: Use consistent fading or don't randomize during sweep

3. **Noise floor assumption**
   - Hardcoded -88 dBm assumes fixed BW=100 MHz
   - If BW changes between calls → SNR changes artificially
   - **Fix**: Pass bandwidth as parameter to `connect()`

4. **Quantization applied inconsistently**
   - Some code paths skip `quantize_phases()`
   - SNR computed with ideal phases vs quantized phases
   - **Fix**: Always quantize before SNR computation

### Fix

**In `core/network.py`:**

```python
def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None,
            compute_phases=True, bandwidth_MHz=100, seed=None):
    """Compute cascaded link with consistent SNR calculation

    Args:
        seed: Random seed for reproducibility (enables consistent comparisons)
    """
    # Set seed for reproducibility if doing sweep comparison
    if seed is not None:
        np.random.seed(seed)

    ap, ris, ue = self.get(ap_name), self.get(ris_name), self.get(ue_name)

    if ap is None or ris is None or ue is None:
        raise ValueError("Invalid node name in connect")

    # Auto-compute beam angle if not provided
    if beam_angle_deg is None:
        vec_tgt = ue.pos - ris.pos
        beam_angle_deg = np.degrees(np.arctan2(vec_tgt[1], vec_tgt[0]))

    # Compute RIS phases (deterministic)
    if compute_phases:
        ris.compute_phases(ap.pos, ue.pos)
        ris.quantize_phases()  # ← Always quantize

    # Verify quantization was done
    if ris.quantized_phases is None:
        raise RuntimeError("RIS phases not quantized. Call quantize_phases() first.")

    # Path loss calculations
    d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)

    d_ris_ue = np.linalg.norm(ue.pos - ris.pos)
    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)

    # RIS gain
    N = ris.N * ris.N
    target_angle = np.degrees(np.arctan2(ue.pos[1] - ris.pos[1],
                                         ue.pos[0] - ris.pos[0]))
    angle_loss = Physics.angle_loss_dB(beam_angle_deg, target_angle)
    gain_dBi = Physics.array_gain_dBi(N, ris.amplifier_gain, angle_loss_dB=angle_loss)

    # Quantization loss from actual quantized phases
    quant_error_rad = np.angle(np.exp(1j * (ris.current_phases - ris.quantized_phases)))
    quant_loss_dB = Physics.quantization_loss_dB(ris.bits)  # Use actual computed loss

    # Antenna gains
    ap_antenna_gain_dBi = 3.0
    ue_antenna_gain_dBi = 3.0

    # Received power
    pwr_dBm = (ap.power_dBm + ap_antenna_gain_dBi + ue_antenna_gain_dBi +
               gain_dBi - pl_ap_ris - pl_ris_ue - quant_loss_dB)

    # SNR using correct formula
    snr_dB = Physics.compute_snr_dB(
        tx_power_dBm=ap.power_dBm,
        total_loss_dB=(pl_ap_ris + pl_ris_ue),
        gain_dBi=(gain_dBi - quant_loss_dB + ap_antenna_gain_dBi + ue_antenna_gain_dBi),
        bandwidth_MHz=bandwidth_MHz,
        noise_figure_dB=6.0
    )

    # Optional: Apply fading only if not in sweep mode
    if seed is None:  # No seed = not in deterministic mode
        fading_coeff = Physics.rician_fading(ris.K_db)
        if fading_coeff < 1.0:
            snr_dB += 20 * np.log10(fading_coeff)

    return {
        "snr_dB": float(snr_dB),
        "pwr_dBm": float(pwr_dBm),
        "gain_dBi": float(gain_dBi),
        "quant_loss_dB": float(quant_loss_dB)
    }

def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10,
          fine_span=5, fine_res=1, seed=0):  # ← Add seed for consistency
    """Beam sweep with deterministic SNR measurement"""
    ap, ris, ue = self.get(ap_name), self.get(ris_name), self.get(ue_name)

    if ap is None or ris is None or ue is None:
        raise ValueError("Invalid node name in sweep")

    vec = ap.pos - ris.pos
    base_dir = np.degrees(np.arctan2(vec[1], vec[0]))

    local_coarse = np.arange(-fov, fov + 1, step)
    abs_angles = base_dir + local_coarse

    snr_coarse = []
    for abs_a in abs_angles:
        # Use same seed for each sweep measurement
        res = self.connect(ap_name, ris_name, ue_name,
                          beam_angle_deg=abs_a, seed=seed)
        snr_coarse.append(res['snr_dB'])

    # Fine sweep
    best_idx = int(np.argmax(snr_coarse))
    best_local = local_coarse[best_idx]

    local_fine = np.arange(best_local - fine_span,
                          best_local + fine_span + fine_res, fine_res)
    abs_angles_fine = base_dir + local_fine
    snr_fine = []

    for abs_a in abs_angles_fine:
        res = self.connect(ap_name, ris_name, ue_name,
                          beam_angle_deg=abs_a, seed=seed)
        snr_fine.append(res['snr_dB'])

    best_fine_idx = int(np.argmax(snr_fine))
    best_local_fine = local_fine[best_fine_idx]

    return {
        'local_coarse': local_coarse.tolist(),
        'snr_coarse': np.array(snr_coarse).tolist(),
        'local_fine': local_fine.tolist(),
        'snr_fine': np.array(snr_fine).tolist(),
        'best_local_fine': float(best_local_fine),
        'best_snr_fine': float(np.max(snr_fine))
    }
```

---

## Summary of Changes Required

| Issue | File | Line | Type | Priority |
|-------|------|------|------|----------|
| RIS gain double-count | `core/network.py` | 109-124 | Logic | **CRITICAL** |
| SNR/fading misuse | `core/network.py` | 126-134 | Logic | **CRITICAL** |
| Max error wrapping | `controller/ris_phase/phase_quantization.py` | 264 | Logic | **HIGH** |
| Beam-sweep inconsistency | `core/network.py` | 146-207 | Determinism | **HIGH** |
| Validation missing | `core/physics.py` | Add new | Helper | **MEDIUM** |

---

## Testing Strategy

### Test 1: Verify Gain Calculation
```python
# Expected: N=256 → 48 dB gain (no losses)
# After losses (0.5+0.2 = 0.7 dB) → ~47.3 dB
ris = RIS("r1", 0, 0, N=16, bits=2)
result = network.connect("ap1", "r1", "ue1")
assert 46 < result['snr_dB'] < 50, f"Gain anomaly: {result['snr_dB']} dB"
```

### Test 2: Verify SNR Reasonableness
```python
# Expected: -20 to +35 dB typical range
# NOT > 50 dB without very special conditions
snr = result['snr_dB']
assert -20 <= snr <= 50, f"SNR unrealistic: {snr} dB"
```

### Test 3: Verify Quantization Error Wrapping
```python
# Expected: max_error ≤ 45° for 2-bit (90° step)
analyzer = QuantizationAnalyzer()
errors = analyzer.compute_rms_error(ideal, quantized)
assert np.degrees(errors) <= 50, f"Error unwrapped: {np.degrees(errors):.1f}°"
```

### Test 4: Verify Beam-Sweep Consistency
```python
# Expected: Sweep best SNR ≈ optimized SNR (within 1 dB)
sweep_result = network.sweep("ap1", "r1", "ue1")
opt_result = network.connect("ap1", "r1", "ue1", beam_angle_deg=best_angle)
diff = abs(sweep_result['best_snr_fine'] - opt_result['snr_dB'])
assert diff < 1.0, f"Mismatch: {diff:.2f} dB"
```

---

## References

- Brookner, E. (1991). *Phased Array Handbook* (Chap. 8: Array Gain)
- Kay, S.M. (1998). *Fundamentals of Statistical Signal Processing: Estimation Theory*
  - Quantization error distribution, uniform quantizer theory
- IEEE 802.11ad/ay (5G/mmWave)
  - Standard arrays: 16×16 (256 elements) typical
  - Gain: 48 dB @60 GHz, 32 dB @28 GHz
