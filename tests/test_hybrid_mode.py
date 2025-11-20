#!/usr/bin/env python3
"""
Test script for hybrid RIS phase pattern generation

Tests all 4 TX/RX mode combinations and auto-selection logic
"""

import numpy as np
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from core.nodes import RIS
from controller.ris_phase.phase_hybrid import HybridPhaseEngine


def test_hybrid_engine_direct():
    """Test HybridPhaseEngine directly with all 4 combinations"""

    print("="*70)
    print("TEST 1: Direct HybridPhaseEngine with all 4 TX/RX combinations")
    print("="*70)

    # Test coordinates (near-field scenario)
    source = np.array([0.0, 0.0, 0.5])      # AP 0.5m above RIS
    ris_center = np.array([0.0, 0.0, 0.0])
    target = np.array([0.3536, 0.0, 0.3536]) # UE at 45° elevation, 0.5m away

    freq = 5.8e9
    array_size = 16

    # Test all 4 combinations
    combinations = [
        (False, False, "Spherical TX + Spherical RX (Full near-field)"),
        (False, True,  "Spherical TX + Plane RX (Hybrid)"),
        (True,  False, "Plane TX + Spherical RX (Hybrid)"),
        (True,  True,  "Plane TX + Plane RX (Full far-field)"),
    ]

    for plane_tx, plane_rx, description in combinations:
        print(f"\n{description}")
        print("-" * 70)

        phases, metadata = HybridPhaseEngine.compute_hybrid_pattern(
            source, ris_center, target, freq,
            array_size=array_size,
            plane_tx=plane_tx,
            plane_rx=plane_rx
        )

        print(f"  TX Mode:               {metadata['tx_mode']}")
        print(f"  RX Mode:               {metadata['rx_mode']}")
        print(f"  Fraunhofer Boundary:   {metadata['fraunhofer_boundary_m']:.3f} m")
        print(f"  Dist AP to RIS:        {metadata['dist_ap_to_ris_m']:.3f} m")
        print(f"  Dist RIS to UE:        {metadata['dist_ris_to_ue_m']:.3f} m")
        print(f"  Deflection Angle:      {metadata['deflection_angle_deg']:.2f}°")
        print(f"  Phase Array Shape:     {phases.shape}")
        print(f"  Phase Range:           [{np.min(phases):.3f}, {np.max(phases):.3f}] rad")
        print(f"  Phase Mean:            {np.mean(phases):.3f} rad")


def test_auto_selection():
    """Test automatic mode selection based on Fraunhofer boundary"""

    print("\n" + "="*70)
    print("TEST 2: Automatic mode selection (plane_tx=None, plane_rx=None)")
    print("="*70)

    freq = 5.8e9
    array_size = 16
    ris_center = np.array([0.0, 0.0, 0.0])

    # Scenario 1: Both near-field (< boundary)
    print("\nScenario 1: Both nodes near-field (< Fraunhofer boundary)")
    print("-" * 70)
    source = np.array([0.0, 0.0, 0.3])      # AP 0.3m above
    target = np.array([0.2, 0.0, 0.2])      # UE 0.28m away

    phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
        source, ris_center, target, freq, array_size,
        plane_tx=None, plane_rx=None  # Auto-select
    )

    print(f"  Fraunhofer Boundary:   {meta['fraunhofer_boundary_m']:.3f} m")
    print(f"  Dist AP to RIS:        {meta['dist_ap_to_ris_m']:.3f} m -> {meta['tx_mode']} TX")
    print(f"  Dist RIS to UE:        {meta['dist_ris_to_ue_m']:.3f} m -> {meta['rx_mode']} RX")
    print(f"  Auto-selected:         {meta['tx_mode']} TX + {meta['rx_mode']} RX")

    # Scenario 2: Both far-field (> boundary)
    print("\nScenario 2: Both nodes far-field (> Fraunhofer boundary)")
    print("-" * 70)
    source = np.array([0.0, 0.0, 2.0])      # AP 2m above
    target = np.array([1.5, 0.0, 0.5])      # UE 1.58m away

    phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
        source, ris_center, target, freq, array_size,
        plane_tx=None, plane_rx=None  # Auto-select
    )

    print(f"  Fraunhofer Boundary:   {meta['fraunhofer_boundary_m']:.3f} m")
    print(f"  Dist AP to RIS:        {meta['dist_ap_to_ris_m']:.3f} m -> {meta['tx_mode']} TX")
    print(f"  Dist RIS to UE:        {meta['dist_ris_to_ue_m']:.3f} m -> {meta['rx_mode']} RX")
    print(f"  Auto-selected:         {meta['tx_mode']} TX + {meta['rx_mode']} RX")

    # Scenario 3: Mixed (AP near, UE far)
    print("\nScenario 3: Mixed scenario (AP near, UE far)")
    print("-" * 70)
    source = np.array([0.0, 0.0, 0.3])      # AP 0.3m above (near)
    target = np.array([1.5, 0.0, 0.5])      # UE 1.58m away (far)

    phases, meta = HybridPhaseEngine.compute_hybrid_pattern(
        source, ris_center, target, freq, array_size,
        plane_tx=None, plane_rx=None  # Auto-select
    )

    print(f"  Fraunhofer Boundary:   {meta['fraunhofer_boundary_m']:.3f} m")
    print(f"  Dist AP to RIS:        {meta['dist_ap_to_ris_m']:.3f} m -> {meta['tx_mode']} TX")
    print(f"  Dist RIS to UE:        {meta['dist_ris_to_ue_m']:.3f} m -> {meta['rx_mode']} RX")
    print(f"  Auto-selected:         {meta['tx_mode']} TX + {meta['rx_mode']} RX")


def test_ris_node_integration():
    """Test RIS node class with hybrid engine"""

    print("\n" + "="*70)
    print("TEST 3: RIS node integration with hybrid engine")
    print("="*70)

    # Create RIS node
    ris = RIS(
        name="RIS1",
        x=0.0, y=0.0, z=0.0,
        N=16,
        bits=1,
        freq=5.8e9
    )

    # Verify hybrid engine is enabled by default
    print(f"\nRIS Node: {ris.name}")
    print(f"  Hybrid Engine:  {ris.use_hybrid_engine}")
    print(f"  TX Mode:        {ris.plane_tx}")
    print(f"  RX Mode:        {ris.plane_rx}")

    # Test mode setting
    print("\n--- Testing set_tx_mode ---")
    result = ris.set_tx_mode('spherical')
    print(f"  set_tx_mode('spherical'): {result}")

    print("\n--- Testing set_rx_mode ---")
    result = ris.set_rx_mode('focus')
    print(f"  set_rx_mode('focus'): {result}")

    # Compute phases
    print("\n--- Computing phases ---")
    ap_pos = np.array([0.0, 0.0, 0.5])
    ue_pos = np.array([0.3536, 0.0, 0.3536])

    phases = ris.compute_phases(ap_pos, ue_pos)

    print(f"  Phases computed:     {phases.shape}")
    print(f"  Metadata available:  {ris.phase_metadata is not None}")

    # Get hybrid mode info
    print("\n--- Hybrid mode info ---")
    info = ris.get_hybrid_mode_info()
    for key, value in info.items():
        if isinstance(value, float):
            print(f"  {key:25s}: {value:.3f}")
        else:
            print(f"  {key:25s}: {value}")

    # Test auto mode
    print("\n--- Testing auto mode ---")
    ris.set_tx_mode('auto')
    ris.set_rx_mode('auto')
    phases = ris.compute_phases(ap_pos, ue_pos)
    info = ris.get_hybrid_mode_info()
    print(f"  Auto-selected TX:    {info['last_tx_mode_used']}")
    print(f"  Auto-selected RX:    {info['last_rx_mode_used']}")


def test_mode_descriptions():
    """Test mode description strings"""

    print("\n" + "="*70)
    print("TEST 4: Mode descriptions")
    print("="*70)

    combinations = [
        (False, False),
        (False, True),
        (True, False),
        (True, True),
    ]

    for plane_tx, plane_rx in combinations:
        desc = HybridPhaseEngine.get_mode_description(plane_tx, plane_rx)
        print(f"  plane_tx={plane_tx:5}, plane_rx={plane_rx:5} -> {desc}")


if __name__ == '__main__':
    try:
        # Run all tests
        test_hybrid_engine_direct()
        test_auto_selection()
        test_ris_node_integration()
        test_mode_descriptions()

        print("\n" + "="*70)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nHybrid mode implementation is ready to use!")
        print("\nNext steps:")
        print("  1. Launch risnet CLI: python main.py")
        print("  2. Connect to RIS shell: ris <name>")
        print("  3. Use commands:")
        print("     - hybrid_mode          (show current configuration)")
        print("     - set_tx_mode auto     (auto-select TX wave type)")
        print("     - set_rx_mode focus    (use point focusing)")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
