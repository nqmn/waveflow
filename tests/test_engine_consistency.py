"""Cross-engine consistency: SimRIS and LightRIS are complementary, not divergent.

The two engines answer different questions (stochastic reference channel vs
fast analytical budget) and are NOT expected to return identical SNR. What
makes them complementary rather than contradictory is that:

1. There is exactly ONE LightRIS implementation: connect(), sweeps,
   pathfinding, and ML probe features all evaluate utils/lightris.
2. In the one regime where both engines model the same physics (forced LOS,
   no direct path, no NLOS scatterers, no shadow fading) they differ by a
   stable, explainable systematic offset - not by topology-dependent noise.
3. Both engines agree on physical TRENDS (topology ranking, N^2 scaling), so
   conclusions drawn with one engine transfer to the other.

Measured decomposition of the LOS-only offset (~ +10.7 dB, SimRIS above
LightRIS):
  - ~4 dB: SimRIS indoor-fitted path loss (32.4 + 17.3 log10 d + 20 log10 f)
    vs LightRIS free-space (slope 20), over two hops at these distances
  - ~5 dB: SimRIS applies the cos^3 element pattern (9.03 dBi peak) on both
    incidence and departure; LightRIS books the element pattern once
  - ~4 dB: LightRIS bakes in conservative hardware impairments (taper, phase
    error, near-field, efficiency, quantization) that SimRIS's ideal
    phase-matched evaluation omits
"""

import numpy as np
import pytest

from core import RISNetwork
from utils.lightris import evaluate_lightris_from_nodes

TOPOLOGIES = [
    ((0, 0), (5, 0), (10, 3)),
    ((0, 4), (6, 1), (12, 6)),
    ((2, 0), (8, 3), (9, 9)),
    ((1, 1), (4, 2), (2, 6)),
    ((0, 0), (10, 0), (20, 5)),
]


def _make_net(a, r, u, n_side=16):
    net = RISNetwork(enable_messaging=False)
    net.add_ap("ap", a[0], a[1], 1, power_dBm=20)
    net.add_ris("ris", r[0], r[1], 1, N=n_side, bits=2, max_angle_deg=90)
    net.add_ue("ue", u[0], u[1], 1)
    return net


def _lightris_snr(net):
    return net.connect("ap", "ris", "ue", seed=42, use_get_snr=False,
                       channel_model="lightris", store_in_active_links=False)['snr_dB']


def _simris_los_snr(net):
    """SimRIS restricted to the LightRIS-comparable regime: deterministic LOS."""
    return net.connect("ap", "ris", "ue", seed=42, use_get_snr=False,
                       channel_model="simris", store_in_active_links=False,
                       include_direct_path=False, include_nlos=False,
                       include_shadow_fading=False,
                       force_tx_ris_los=True, force_ris_rx_los=True)['snr_dB']


class TestSingleLightRISImplementation:
    def test_connect_matches_utils_lightris(self):
        """connect(channel_model='lightris') and utils/lightris are ONE model."""
        for a, r, u in TOPOLOGIES[:3]:
            net = _make_net(a, r, u)
            via_connect = _lightris_snr(net)
            via_utils = evaluate_lightris_from_nodes(
                net.get("ap"), net.get("ris"), net.get("ue"))['snr_dB']
            assert via_connect == pytest.approx(via_utils, abs=0.01), (
                f"LightRIS drift on AP{a} RIS{r} UE{u}: "
                f"connect={via_connect:.3f} vs utils={via_utils:.3f} dB")


class TestCrossEngineComplementarity:
    def test_los_only_offset_is_stable(self):
        """LOS-only SimRIS sits a stable ~+10.7 dB above LightRIS (see module doc)."""
        deltas = []
        for a, r, u in TOPOLOGIES:
            net = _make_net(a, r, u)
            deltas.append(_simris_los_snr(net) - _lightris_snr(net))
        deltas = np.array(deltas)
        # every topology within the documented band, and the band is narrow
        assert np.all((deltas > 7.0) & (deltas < 14.0)), f"deltas {deltas}"
        assert np.ptp(deltas) < 4.0, (
            f"offset should be systematic, not topology noise: spread {np.ptp(deltas):.2f} dB")

    def test_engines_rank_topologies_identically(self):
        """Conclusions transfer: both engines order the same links the same way."""
        lr = [_lightris_snr(_make_net(a, r, u)) for a, r, u in TOPOLOGIES]
        sr = [_simris_los_snr(_make_net(a, r, u)) for a, r, u in TOPOLOGIES]
        assert list(np.argsort(lr)) == list(np.argsort(sr))

    def test_both_engines_show_n_squared_scaling(self):
        """Quadrupling the element count adds ~12 dB (N^2) under BOTH engines."""
        a, r, u = TOPOLOGIES[0]
        gain_lr = _lightris_snr(_make_net(a, r, u, n_side=32)) - _lightris_snr(_make_net(a, r, u, n_side=16))
        gain_sr = _simris_los_snr(_make_net(a, r, u, n_side=32)) - _simris_los_snr(_make_net(a, r, u, n_side=16))
        assert gain_lr == pytest.approx(12.0, abs=1.5)
        assert gain_sr == pytest.approx(12.0, abs=1.5)
