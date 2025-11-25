"""Test DE Localization Sweep accuracy over multiple random UE positions"""

import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.network import RISNetwork
from controller.beamsweeping.algorithms.de_localization_sweep import DELocalizationSweep


def test_de_accuracy_multiple_positions(num_trials=10, ris_size=8, M=16):
    """Run DE localization sweep 10 times with random UE positions"""

    print("=" * 80)
    print("DE LOCALIZATION ACCURACY TEST - RANDOM UE POSITIONS")
    print("=" * 80)

    print(f"\nTest Configuration:")
    print(f"  Trials: {num_trials}")
    print(f"  RIS Size: {ris_size}×{ris_size} = {ris_size*ris_size} elements")
    print(f"  Configurations (M): {M}")
    print(f"  SNR: 25.0 dB")

    # Fixed network geometry
    ap_pos = np.array([10.0, 10.0, 1.5])
    ris_pos = np.array([15.0, 10.0, 1.2])

    print(f"\nFixed Geometry:")
    print(f"  AP:  {ap_pos}")
    print(f"  RIS: {ris_pos}")

    # Results tracking
    errors = []
    beam_angles = []
    snrs = []
    times = []

    print(f"\n{'Trial':<6} {'UE Pos (X, Y, Z)':<30} {'Est. Pos':<30} {'Error (m)':<12} {'Time (s)':<10}")
    print("-" * 90)

    for trial in range(num_trials):
        # Generate random UE position
        # X: ±3m from AP, Y: ±3m from AP, Z: 0.8-1.2m height
        ue_x = ap_pos[0] + np.random.uniform(-3, 3)
        ue_y = ap_pos[1] + np.random.uniform(-3, 3)
        ue_z = np.random.uniform(0.8, 1.2)
        ue_pos = np.array([ue_x, ue_y, ue_z])

        # Create network with random UE
        net = RISNetwork()
        net.add_ap("ap1", x=ap_pos[0], y=ap_pos[1], z=ap_pos[2])
        net.add_ris("ris1", x=ris_pos[0], y=ris_pos[1], z=ris_pos[2], N=ris_size, freq=5.8e9)
        net.add_ue("ue1", x=ue_x, y=ue_y, z=ue_z)

        # Run DE sweep
        algo = DELocalizationSweep(net)
        result = algo.sweep(
            ap_name="ap1",
            ris_name="ris1",
            ue_name="ue1",
            M=M,
            target_snr_db=25.0,
            de_maxiter=50,
            de_popsize=10,
            seed=42 + trial  # Different seed for each trial
        )

        # Extract results
        est_pos = result["estimated_position"]
        error = result.get("localization_error", 0.0)
        beam_angle = result["beam_angle_deg"]
        snr = result["snr_coarse"][0] if result["snr_coarse"] else 0.0
        exec_time = result["total_time"]

        errors.append(error)
        beam_angles.append(beam_angle)
        snrs.append(snr)
        times.append(exec_time)

        # Print trial result
        true_pos_str = f"({ue_pos[0]:.2f}, {ue_pos[1]:.2f}, {ue_pos[2]:.2f})"
        est_pos_str = f"({est_pos[0]:.2f}, {est_pos[1]:.2f}, {est_pos[2]:.2f})"
        print(f"{trial+1:<6} {true_pos_str:<30} {est_pos_str:<30} {error:<12.4f} {exec_time:<10.2f}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    errors = np.array(errors)
    beam_angles = np.array(beam_angles)
    snrs = np.array(snrs)
    times = np.array(times)

    print(f"\nLocalization Error (m):")
    print(f"  Mean:     {np.mean(errors):.4f}")
    print(f"  Median:   {np.median(errors):.4f}")
    print(f"  Std Dev:  {np.std(errors):.4f}")
    print(f"  Min:      {np.min(errors):.4f}")
    print(f"  Max:      {np.max(errors):.4f}")
    print(f"  < 0.5m:   {np.sum(errors < 0.5)}/{num_trials} trials")
    print(f"  < 1.0m:   {np.sum(errors < 1.0)}/{num_trials} trials")

    print(f"\nBeam Angle (degrees):")
    print(f"  Mean:     {np.mean(beam_angles):.2f}°")
    print(f"  Std Dev:  {np.std(beam_angles):.2f}°")
    print(f"  Range:    {np.min(beam_angles):.2f}° to {np.max(beam_angles):.2f}°")

    print(f"\nSNR @ Beam Angle (dB):")
    print(f"  Mean:     {np.mean(snrs):.2f}")
    print(f"  Std Dev:  {np.std(snrs):.2f}")
    print(f"  Range:    {np.min(snrs):.2f} to {np.max(snrs):.2f}")

    print(f"\nExecution Time (seconds):")
    print(f"  Mean:     {np.mean(times):.2f}")
    print(f"  Std Dev:  {np.std(times):.2f}")
    print(f"  Range:    {np.min(times):.2f} to {np.max(times):.2f}")
    print(f"  Total:    {np.sum(times):.2f}")

    # Performance assessment
    print(f"\n{'='*80}")
    print("PERFORMANCE ASSESSMENT")
    print(f"{'='*80}")

    success_rate = (np.sum(errors < 0.5) / num_trials) * 100
    print(f"\nSuccess Rate (< 0.5m error): {success_rate:.1f}%")

    if success_rate >= 80:
        print("Status: EXCELLENT ✓")
    elif success_rate >= 60:
        print("Status: GOOD ✓")
    elif success_rate >= 40:
        print("Status: FAIR")
    else:
        print("Status: NEEDS IMPROVEMENT")

    # Create per-trial analysis
    print(f"\n{'='*80}")
    print("PER-TRIAL DETAILED RESULTS")
    print(f"{'='*80}\n")

    for i in range(num_trials):
        status = "OK" if errors[i] < 0.5 else "BAD" if errors[i] > 1.0 else "FAIR"
        print(f"Trial {i+1}: Error={errors[i]:.4f}m {status}, Angle={beam_angles[i]:.2f}deg, SNR={snrs[i]:.2f}dB, Time={times[i]:.2f}s")

    return {
        'errors': errors,
        'beam_angles': beam_angles,
        'snrs': snrs,
        'times': times,
        'mean_error': np.mean(errors),
        'success_rate': success_rate
    }


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("RUNNING DE LOCALIZATION ACCURACY TEST")
    print("=" * 80 + "\n")

    # Test 1: Standard configuration (8×8 RIS, M=16)
    results1 = test_de_accuracy_multiple_positions(num_trials=10, ris_size=8, M=16)

    # Test 2: Larger RIS (16×16, M=32)
    print("\n\n" + "=" * 80)
    print("RUNNING TEST 2: LARGER RIS (16×16, M=32)")
    print("=" * 80 + "\n")

    results2 = test_de_accuracy_multiple_positions(num_trials=10, ris_size=16, M=32)

    # Final summary
    print("\n\n" + "=" * 80)
    print("FINAL COMPARISON")
    print("=" * 80)
    print(f"\nConfiguration 1 (8×8, M=16):")
    print(f"  Mean Error: {results1['mean_error']:.4f}m")
    print(f"  Success Rate (< 0.5m): {results1['success_rate']:.1f}%")

    print(f"\nConfiguration 2 (16×16, M=32):")
    print(f"  Mean Error: {results2['mean_error']:.4f}m")
    print(f"  Success Rate (< 0.5m): {results2['success_rate']:.1f}%")

    if results2['success_rate'] > results1['success_rate']:
        improvement = results2['success_rate'] - results1['success_rate']
        print(f"\nLarger RIS improves success rate by {improvement:.1f}%")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")
