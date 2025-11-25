"""Test DE Localization Sweep Algorithm"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.network import RISNetwork
from core.nodes import AccessPoint, RIS, UE
from controller.beamsweeping.algorithms.de_localization_sweep import DELocalizationSweep


def test_de_localization_sweep_basic():
    """Test basic DE localization sweep functionality"""
    print("=" * 70)
    print("TEST: DE Localization Sweep - Basic Functionality")
    print("=" * 70)

    # Create network
    net = RISNetwork()

    # Add nodes
    net.add_ap("ap1", x=10.0, y=10.0, z=1.5)
    net.add_ris("ris1", x=15.0, y=10.0, z=1.2, N=16, freq=5.8e9)
    net.add_ue("ue1", x=9.5, y=4.5, z=1.0)

    ap = net.get("ap1")
    ris = net.get("ris1")
    ue = net.get("ue1")

    print(f"\nNetwork Setup:")
    print(f"  AP:  {ap.pos}")
    print(f"  RIS: {ris.pos}")
    print(f"  UE:  {ue.pos}")
    print(f"  RIS Size: {ris.N}×{ris.N} = {ris.N*ris.N} elements")

    # Create sweep algorithm
    algo = DELocalizationSweep(net)

    print(f"\nAlgorithm: {algo.name}")
    print(f"Description: {algo.description}")

    # Run sweep
    print(f"\nRunning DE Localization Sweep...")
    result = algo.sweep(
        ap_name="ap1",
        ris_name="ris1",
        ue_name="ue1",
        M=16,  # Fewer configs for faster test
        target_snr_db=25.0,
        de_maxiter=50,
        de_popsize=10,
        seed=42,
    )

    # Check results
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")

    est_pos = result["estimated_position"]
    true_pos = ue.pos
    error = result.get("localization_error", 0)

    print(f"Estimated Position: [{est_pos[0]:.4f}, {est_pos[1]:.4f}, {est_pos[2]:.4f}] m")
    print(f"True Position:      [{true_pos[0]:.4f}, {true_pos[1]:.4f}, {true_pos[2]:.4f}] m")
    print(f"Localization Error: {error:.4f} m")
    print(f"Beam Angle:         {result['beam_angle_deg']:.2f}°")
    print(f"SNR @ Beam Angle:   {result['snr_dB']:.2f} dB")
    print(f"Configurations:     {result['configuration_count']}")
    print(f"Total Time:         {result['total_time']:.2f} s")

    print(f"\n{'='*70}")

    # Assertions
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "estimated_position" in result, "Result should contain estimated_position"
    assert "beam_angle_deg" in result, "Result should contain beam_angle_deg"
    assert "snr_dB" in result, "Result should contain snr_dB"
    assert len(result["estimated_position"]) == 3, "Position should be 3D"
    assert result["configuration_count"] > 0, "Should have configurations"

    # Check if localization is reasonable
    if error > 0:
        assert (
            error < 2.0
        ), f"Localization error should be < 2m, got {error:.4f}m"
        print(f"Status: PASS (Error: {error:.4f}m)")
    else:
        print(f"Status: PASS (No true position comparison)")

    return True


def test_de_sweep_initialization():
    """Test algorithm initialization"""
    print("\n" + "=" * 70)
    print("TEST: Algorithm Initialization")
    print("=" * 70)

    net = RISNetwork()
    algo = DELocalizationSweep(net)

    assert algo.name == "Differential Evolution Localization Sweep"
    assert "Blind UE localization" in algo.description
    assert algo.network == net

    print(f"Name: {algo.name}")
    print(f"Description: {algo.description}")
    print("Status: PASS")

    return True


def test_de_sweep_with_small_ris():
    """Test with small RIS array (faster)"""
    print("\n" + "=" * 70)
    print("TEST: DE Localization with Small RIS (4×4)")
    print("=" * 70)

    net = RISNetwork()
    net.add_ap("ap", x=10, y=10, z=1.5)
    net.add_ris("ris", x=15, y=10, z=1.2, N=4, freq=5.8e9)  # 4x4 = 16 elements only
    net.add_ue("ue", x=9.5, y=4.5, z=1.0)

    ap = net.get("ap")
    ris = net.get("ris")
    ue = net.get("ue")

    algo = DELocalizationSweep(net)

    print(f"RIS Size: {ris.N}×{ris.N} = {ris.N*ris.N} elements (smaller for fast test)")

    result = algo.sweep(
        ap_name="ap",
        ris_name="ris",
        ue_name="ue",
        M=8,
        de_maxiter=30,
        de_popsize=8,
        seed=42,
    )

    print(f"\nResults:")
    print(f"  Estimated: {result['estimated_position']}")
    print(f"  Error: {result.get('localization_error', 'N/A'):.4f}m")
    print(f"  Beam Angle: {result['beam_angle_deg']:.2f}°")
    print(f"  Time: {result['total_time']:.2f}s")
    print("Status: PASS")

    return True


if __name__ == "__main__":
    try:
        test_de_sweep_initialization()
        test_de_localization_sweep_basic()
        test_de_sweep_with_small_ris()

        print("\n" + "=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
