# SimRIS & LightRIS: How the Two Engines Relate

Waveflow ships two channel engines that are **complementary, not
interchangeable**. They answer different questions and are calibrated
differently on purpose. This page documents exactly how they relate, so
results from one can be interpreted against the other.
`tests/test_engine_consistency.py` enforces everything stated here.

## Roles

| | SimRIS | LightRIS |
|---|---|---|
| Nature | Stochastic reference channel (published-model based) | Native analytical budget |
| Use for | Literature-aligned channel studies, H/G/D tensor analysis, realistic per-realization variation | Fast system-level evaluation, large beam sweeps, feedback loops, ML dataset generation |
| Path loss | 3GPP-style indoor fit (32.4 + 17.3·log₁₀d + 20·log₁₀f) with LOS blocking probability | Free-space (FSPL) on both hops |
| Randomness | Scatterer clusters, shadow fading, LOS sampling | None (deterministic) |
| Direct AP→UE path | Included by default | Not modeled (RIS path only) |

## One LightRIS

There is exactly **one** LightRIS implementation: `utils/lightris.py`.
`connect(channel_model="lightris")`, beam sweeps, pathfinding edge SNR, and
the ML probe features all delegate to it. `connect()` and
`evaluate_lightris_from_nodes()` agree to <0.01 dB by regression test.

## The systematic offset between the engines

In the only regime where both engines model the same physics — forced LOS,
direct path off, NLOS and shadow fading off — SimRIS reads a **stable
+10.7 ± 1.2 dB above LightRIS**. This is a documented calibration
difference, not a contradiction:

| Component | ≈ dB | Cause |
|---|---|---|
| Path loss model | ~4 | Indoor-fitted slope 17.3 vs free-space slope 20, over two hops |
| Element pattern bookkeeping | ~5 | SimRIS applies the cos³ element pattern (9.03 dBi peak) at incidence **and** departure; LightRIS books it once |
| Hardware impairments | ~4 | LightRIS bakes in conservative taper/phase-error/near-field/efficiency/quantization corrections that SimRIS's ideal phase-matched evaluation omits |

## What must always agree (and is tested)

- **Topology ranking:** both engines order the same set of links identically —
  conclusions drawn with the fast engine transfer to the reference engine.
- **N² scaling:** quadrupling the element count adds ~12 dB under both
  engines, consistent with the established far-field RIS result
  (Björnson et al. 2020; Tang et al. 2021 measurements).
- **Offset stability:** the LOS-only delta stays inside a 7–14 dB band with
  <4 dB spread across topologies. If a model change moves it, the
  consistency test fails and the table above must be re-derived.

## Practical guidance

- Prototype, sweep, and train on **LightRIS**; expect conservative absolute
  SNR (its impairment terms are safety margin).
- Validate final scenarios on **SimRIS**; expect higher absolute SNR and
  per-seed variation, plus the direct path unless you disable it.
- Never mix absolute SNR numbers across engines in one comparison; compare
  trends, rankings, or deltas instead.
