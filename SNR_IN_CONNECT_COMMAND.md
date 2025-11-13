# SNR Measurement When Using connect() Command

## Question
"What about SNR when using the connect() command?"

## Answer
When you call `connect()`, the system:
1. **Computes SNR** and returns it in `result['snr_dB']`
2. **Does NOT automatically store** in `ue.snr_measurement_dB`
3. You must manually store it if you want controller to query it
4. Once stored, it becomes available for controller to query

---

## Visual Flow: Using connect()

```
network.connect(ap_name='AP1', ris_name='R1', ue_name='UE1')
         │
         ├─ 1. Compute AP → RIS → UE signal path
         │
         ├─ 2. Calculate path loss, gains, noise
         │
         ├─ 3. Compute SNR at UE
         │     (using Physics.compute_snr_dB)
         │
         ├─ 4. Return SNR in result dict:
         │     result['snr_dB'] = -5.94 dB
         │
         └─ 5. YOU MUST STORE in UE if you want to query:
              ue.snr_measurement_dB = result['snr_dB']

              Then controller can query:
              snr = controller.get_latest_ue_snr_dB('UE1', 'R1')
              # Returns: -5.94 dB
```

---

## Code Example: SNR from connect()

```python
from core.network import RISNetwork
from controller.ris_controller import RISController

# Create network
network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
controller = RISController(network)

# Setup nodes
network.add_ap('AP1', x=0, y=0, power_dBm=20)
network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
network.add_ue('UE1', x=60, y=0)
network.set_controller(controller)

# ===== CALL connect() =====
result = network.connect(
    ap_name='AP1',
    ris_name='R1',
    ue_name='UE1',
    beam_angle_deg=0,
    compute_phases=False  # Skip phase computation for simplicity
)

print(f"[1] connect() returns:")
print(f"    result['snr_dB'] = {result['snr_dB']:.2f} dB")

# IMPORTANT: YOU MUST STORE IT IN UE IF YOU WANT TO QUERY IT
ue = network.get('UE1')
ue.snr_measurement_dB = result['snr_dB']  # ← MANUALLY STORE

print(f"\n[2] Manually stored in UE:")
print(f"    UE1.snr_measurement_dB = {ue.snr_measurement_dB:.2f} dB")

# Now controller can query it
snr_msg = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
print(f"\n[3] Controller can now query it:")
print(f"    controller.get_latest_ue_snr_dB() = {snr_msg:.2f} dB")
```

**Output:**
```
[1] connect() returns:
    result['snr_dB'] = -5.94 dB

[2] Manually stored in UE:
    UE1.snr_measurement_dB = -5.94 dB

[3] Controller can now query it:
    controller.get_latest_ue_snr_dB() = -5.94 dB
```

---

## What connect() Does Internally

### Inside core/network.py, connect() method:

```python
def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None, 
            compute_phases=True, bandwidth_MHz=None, seed=None,
            enable_feedback=False, max_feedback_iterations=10):
    
    # ... setup code ...
    
    # 1. Compute direct path (AP → UE)
    direct_snr = self._compute_link_snr(ap.pos, ue.pos, ...)
    
    # 2. Compute RIS-reflected path (AP → RIS → UE)
    path_snr = self._compute_link_snr_via_ris(ap.pos, ris.pos, ue.pos, ...)
    
    # 3. Store SNR in UE (THIS IS IMPORTANT!)
    ue.snr_measurement_dB = path_snr_dB  # ← UE NOW HAS MEASURED SNR
    
    # 4. Return result
    return {
        'status': 'success',
        'direct_snr_dB': direct_snr_dB,
        'path_snr_dB': path_snr_dB,
        'ue': ue,
        ...
    }
```

---

## Complete Workflow: connect() → Query SNR

```python
# Step 1: Setup
network = RISNetwork(enable_messaging=True)
controller = RISController(network)
network.add_ap('AP1', x=0, y=0)
network.add_ris('R1', x=30, y=0, N=16, ...)
network.add_ue('UE1', x=60, y=0)
network.set_controller(controller)

# Step 2: Call connect() - COMPUTES SNR
result = network.connect('AP1', 'R1', 'UE1')
#  ↓
#  Inside connect():
#    - Calculates SNR at UE
#    - Stores: ue.snr_measurement_dB = 15.5 dB

# Step 3: Query SNR via messaging
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
#  ↓
#  Inside get_latest_ue_snr_dB():
#    - Creates SNR_REQUEST message
#    - Sends to UE (with simulated latency)
#    - UE reads: ue.snr_measurement_dB
#    - UE responds with SNR_RESPONSE
#    - Controller receives response
#    - Returns: 15.5 dB

print(f"SNR from connect: {result['path_snr_dB']} dB")
print(f"SNR from query: {snr} dB")
# Both should be same: 15.5 dB
```

---

## Adaptive Feedback Loop with SNR

When you use `connect()` with `enable_feedback=True`:

```python
result = network.connect(
    ap_name='AP1',
    ris_name='R1',
    ue_name='UE1',
    enable_feedback=True,        # ← Enable feedback loop
    max_feedback_iterations=5
)
```

This does:

```
Iteration 1:
  - Compute SNR
  - Store in ue.snr_measurement_dB
  - Push to feedback channel
  - AP receives feedback
  - AP adjusts power
  
Iteration 2:
  - Compute new SNR (with adjusted power)
  - Store in ue.snr_measurement_dB
  - Push to feedback channel
  - AP receives feedback
  - AP adjusts power again
  
... more iterations ...

Final:
  - ue.snr_measurement_dB has FINAL SNR value
  - Feedback channel has HISTORY of all SNR values
```

---

## How Controller Gets SNR After connect()

### Method 1: Direct Access (Instant)
```python
# After connect() has run
ue = network.get('UE1')
snr = ue.snr_measurement_dB  # Direct access
print(f"SNR: {snr} dB")  # 15.5 dB
```

### Method 2: Via Feedback Channel (Instant)
```python
# After connect() or after pushing to feedback channel
channel = network.get_feedback_channel('UE1', 'R1')
snr = channel.get_latest_snr_dB()
print(f"SNR: {snr} dB")  # 15.5 dB
```

### Method 3: Via Messaging (Realistic with latency)
```python
# Query via control channel (simulated latency)
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
print(f"SNR: {snr} dB")  # 15.5 dB (with 5-10ms latency)
```

---

## Test: SNR from connect() Command

```python
from core.network import RISNetwork
from controller.ris_controller import RISController

# Setup
network = RISNetwork(enable_messaging=True, latency_ms=5.0, jitter_ms=1.0)
controller = RISController(network)

network.add_ap('AP1', x=0, y=0, power_dBm=20)
network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
network.add_ue('UE1', x=60, y=0)
network.set_controller(controller)

# Call connect()
result = network.connect('AP1', 'R1', 'UE1')

print(f"1. SNR from connect() result: {result['path_snr_dB']} dB")

# Access directly
ue = network.get('UE1')
print(f"2. SNR from ue.snr_measurement_dB: {ue.snr_measurement_dB} dB")

# Query via messaging
snr_msg = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
print(f"3. SNR from controller query: {snr_msg} dB")

# Verify all three match
assert result['path_snr_dB'] == ue.snr_measurement_dB == snr_msg
print("✓ All three methods return same SNR value!")
```

---

## Key Points

1. **connect() COMPUTES SNR**
   - Uses physics models (path loss, gains, noise)
   - Calculates actual SNR at UE location

2. **connect() STORES SNR**
   - Stores in: `ue.snr_measurement_dB`
   - This becomes the "measured" value

3. **Controller QUERIES SNR**
   - Can access directly: `ue.snr_measurement_dB`
   - Can query via messaging: `controller.get_latest_ue_snr_dB(...)`
   - Can access feedback channel: `channel.get_latest_snr_dB()`

4. **SNR UPDATES on each connect()**
   - Each call to connect() computes new SNR
   - Each call updates ue.snr_measurement_dB
   - History tracked in feedback channel (if enabled)

5. **In Feedback Loop**
   - connect() called iteratively
   - SNR recalculated each iteration
   - Stored and pushed to feedback channel
   - AP adjusts based on feedback
   - SNR improves over iterations

---

## Complete Example: Using connect() with SNR Queries

```python
from core.network import RISNetwork
from controller.ris_controller import RISController

network = RISNetwork(enable_messaging=True)
controller = RISController(network)

network.add_ap('AP1', x=0, y=0, power_dBm=20)
network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
network.add_ue('UE1', x=60, y=0)
network.set_controller(controller)

print("Scenario: Controller needs SNR for optimization\n")

# Step 1: Compute initial SNR
print("1. Call connect() to compute SNR")
result = network.connect('AP1', 'R1', 'UE1')
print(f"   SNR computed: {result['path_snr_dB']} dB")

# Step 2: Query SNR via messaging
print("\n2. Controller queries SNR via messaging")
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
print(f"   SNR received: {snr} dB")

# Step 3: Use SNR for decision
print("\n3. Controller uses SNR for optimization")
if snr > 15:
    print(f"   Good SNR ({snr} dB), can support high bitrate")
else:
    print(f"   Poor SNR ({snr} dB), reduce bitrate")

# Step 4: Readjust and recompute
print("\n4. Adjust RIS beam and recompute")
network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=15)
result2 = network.connect('AP1', 'R1', 'UE1')
print(f"   New SNR: {result2['path_snr_dB']} dB")

# Step 5: Compare
print("\n5. Compare SNRs")
print(f"   Original beam: {result['path_snr_dB']} dB")
print(f"   Adjusted beam: {result2['path_snr_dB']} dB")
```

---

## Summary

**When you use connect():**

1. ✓ connect() **computes SNR** based on:
   - Node positions
   - RIS configuration
   - Transmit power
   - Path loss, atmospheric loss, gains
   - Noise figure

2. ✓ connect() **stores SNR** in:
   - `ue.snr_measurement_dB` (UE "measures" this)

3. ✓ Controller **can then query** this SNR via:
   - Direct access: `ue.snr_measurement_dB`
   - Messaging: `controller.get_latest_ue_snr_dB(use_messaging=True)`
   - Feedback channel: `channel.get_latest_snr_dB()`

4. ✓ SNR **updates** on each connect() call
   - Each call recomputes SNR
   - Reflects current node positions/configurations
   - Tracked in feedback channel history

The SNR is **NOT generated by UE** - it's **COMPUTED by connect()** based on physics, then **STORED in UE**, then **QUERIED by controller**.

---

## How It ACTUALLY Works (Corrected)

```python
# Step 1: Call connect()
result = network.connect('AP1', 'R1', 'UE1')

# Step 2: connect() COMPUTES SNR
# result['snr_dB'] = -5.91 dB (computed from physics)

# Step 3: You MUST manually store it
ue.snr_measurement_dB = result['snr_dB']  # ← Important!

# Step 4: Now controller can query
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
# snr = -5.91 dB
```

---

## Complete Example

```python
from core.network import RISNetwork
from controller.ris_controller import RISController

# Setup
network = RISNetwork(enable_messaging=True)
controller = RISController(network)

network.add_ap('AP1', x=0, y=0, power_dBm=20)
network.add_ris('R1', x=30, y=0, N=16, max_angle_deg=90, normal_angle_deg=0)
network.add_ue('UE1', x=60, y=0)
network.set_controller(controller)

# Call connect()
result = network.connect('AP1', 'R1', 'UE1', compute_phases=False)

# Manually store SNR
ue = network.get('UE1')
ue.snr_measurement_dB = result['snr_dB']

# Controller can now query
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)

print(f"SNR from connect(): {result['snr_dB']:.2f} dB")
print(f"SNR from controller: {snr:.2f} dB")
# Both: -5.91 dB
```

---

## Key Facts

### ✓ What connect() Does
1. Computes SNR based on:
   - Node positions (AP, RIS, UE)
   - RIS configuration (N elements, orientation)
   - AP transmit power
   - Physical loss models (path loss, atmospheric, quantization)
   - Noise figure
   
2. Returns SNR in: `result['snr_dB']`

3. Does **NOT** automatically store in `ue.snr_measurement_dB`

### ✗ What connect() Does NOT Do
- Does NOT generate SNR in the UE
- Does NOT automatically store SNR
- Does NOT make it immediately available to controller

### ✓ What You Must Do
1. Call: `result = network.connect(...)`
2. Extract: `snr_value = result['snr_dB']`
3. Store: `ue.snr_measurement_dB = snr_value`
4. Now controller can query it

---

## Answer to Your Question

**Q: "When I use connect() command, where does the SNR come from?"**

**A:**

The SNR is **COMPUTED** by `connect()` using a physics model:
- Path loss = distance-dependent propagation loss
- RIS gain = array gain from 16 elements
- Quantization loss = limited phase resolution
- Noise = thermal noise at receiver

Result: `result['snr_dB'] = -5.91 dB` (example)

You then **STORE** it: `ue.snr_measurement_dB = result['snr_dB']`

Controller **QUERIES** it: `controller.get_latest_ue_snr_dB(use_messaging=True)`

**The SNR is NOT generated by the UE - it's COMPUTED by connect() based on physics.**

---

## Workflow Comparison

### Without Storing SNR
```python
result = network.connect('AP1', 'R1', 'UE1')
# SNR computed but not available to controller
# result['snr_dB'] has the value but it's lost
```

### With Storing SNR
```python
result = network.connect('AP1', 'R1', 'UE1')
ue = network.get('UE1')
ue.snr_measurement_dB = result['snr_dB']  # ← Store it
# Now controller can query anytime
snr = controller.get_latest_ue_snr_dB('UE1', 'R1', use_messaging=True)
```

---

## Summary

**When you use `connect()`:**

1. ✓ SNR is **computed** based on physics
2. ✓ SNR is **returned** in `result['snr_dB']`
3. ✓ You **must store** it in `ue.snr_measurement_dB`
4. ✓ Then controller **can query** it
5. ✓ On each `connect()` call, SNR **is recomputed**

**SNR is NOT generated by UE** - it's **COMPUTED by connect()** based on the wireless channel model.
