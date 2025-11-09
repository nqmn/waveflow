#!/usr/bin/env python3
"""Compare sweeps with COARSE step size where ML can save measurements"""

import json
import os
import random
from pathlib import Path
import numpy as np
from core.network import RISNetwork
from controller.beamsweeping import MLPredictorLoader, SweepAlgorithmLoader

def run_coarse_sweep_comparison(num_tests=10):
    """Run sweeps with 20° step where ML can show benefits"""

    results = {
        'without_ml': [],
        'with_ml': [],
        'with_ml_zero': [],
    }

    random.seed(42)
    np.random.seed(42)

    print(f"Running {num_tests} sweep comparisons (20° step size)...\n")

    for test_num in range(num_tests):
        # Create random topology
        net = RISNetwork()

        ap_pos = np.array([
            random.uniform(0, 20),
            random.uniform(0, 20),
            random.uniform(0, 5)
        ])
        ris_pos = np.array([
            random.uniform(0, 20),
            random.uniform(0, 20),
            random.uniform(0, 5)
        ])
        ue_pos = np.array([
            random.uniform(0, 20),
            random.uniform(0, 20),
            random.uniform(0, 5)
        ])

        net.add_ap('AP', *ap_pos, power_dBm=10.0, freq=5.8e9)
        net.add_ris('RIS', *ris_pos, N=16, bits=1, freq=5.8e9)
        net.add_ue('UE', *ue_pos)

        # Test 1: No ML (20° step = 7 angles)
        algo1 = SweepAlgorithmLoader.get_algorithm("linear", net)
        result_no_ml = algo1.sweep('AP', 'RIS', 'UE', fov=60.0, step=20.0, ml_angles=None)
        coarse_measurements_no_ml = len([s for s in result_no_ml['snr_coarse'] if not np.isnan(s)])

        # Test 2: With XGBoost ML
        os.environ['RISNET_XGB_MODEL'] = '/tmp/xgb_beam_predictor_custom_10dbm_1bit.json'
        predictor_xgb = MLPredictorLoader.get_predictor('default', net)
        ml_angles_xgb = predictor_xgb.predict_local_angles('AP', 'RIS', 'UE', fov=60.0, top_k=3)

        algo2 = SweepAlgorithmLoader.get_algorithm("linear", net)
        result_with_ml = algo2.sweep('AP', 'RIS', 'UE', fov=60.0, step=20.0, ml_angles=ml_angles_xgb)
        coarse_measurements_with_ml = len([s for s in result_with_ml['snr_coarse'] if not np.isnan(s)])

        # Test 3: With Zero-Offset ML
        predictor_zero = MLPredictorLoader.get_predictor('zero', net)
        ml_angles_zero = predictor_zero.predict_local_angles('AP', 'RIS', 'UE', fov=60.0, top_k=1)

        algo3 = SweepAlgorithmLoader.get_algorithm("linear", net)
        result_with_ml_zero = algo3.sweep('AP', 'RIS', 'UE', fov=60.0, step=20.0, ml_angles=ml_angles_zero)
        coarse_measurements_with_ml_zero = len([s for s in result_with_ml_zero['snr_coarse'] if not np.isnan(s)])

        # Record results
        results['without_ml'].append({
            'best_snr': result_no_ml['best_snr_fine'],
            'best_angle': result_no_ml['best_local_fine'],
            'measurements': coarse_measurements_no_ml,
            'coarse_snr': result_no_ml['snr_coarse'],
        })
        results['with_ml'].append({
            'best_snr': result_with_ml['best_snr_fine'],
            'best_angle': result_with_ml['best_local_fine'],
            'measurements': coarse_measurements_with_ml,
            'ml_angles': ml_angles_xgb,
            'coarse_snr': result_with_ml['snr_coarse'],
        })
        results['with_ml_zero'].append({
            'best_snr': result_with_ml_zero['best_snr_fine'],
            'best_angle': result_with_ml_zero['best_local_fine'],
            'measurements': coarse_measurements_with_ml_zero,
            'ml_angles': ml_angles_zero,
            'coarse_snr': result_with_ml_zero['snr_coarse'],
        })

        if test_num < 3:  # Show first 3 tests in detail
            print(f"Test {test_num + 1}:")
            print(f"  No ML:            SNR={result_no_ml['best_snr_fine']:>7.2f} dB | "
                  f"Angle={result_no_ml['best_local_fine']:>6.2f}° | Meas={coarse_measurements_no_ml}/7")
            print(f"  With ML (XGBoost): SNR={result_with_ml['best_snr_fine']:>7.2f} dB | "
                  f"Angle={result_with_ml['best_local_fine']:>6.2f}° | Meas={coarse_measurements_with_ml}/7 | "
                  f"Pred={ml_angles_xgb[0]:>6.2f}°")
            print(f"  With ML (Zero):   SNR={result_with_ml_zero['best_snr_fine']:>7.2f} dB | "
                  f"Angle={result_with_ml_zero['best_local_fine']:>6.2f}° | Meas={coarse_measurements_with_ml_zero}/7")
            print()

    return results


def analyze_results(results):
    """Analyze and compare results"""

    print("\n" + "="*80)
    print("SUMMARY STATISTICS (20° step size)")
    print("="*80 + "\n")

    for key in ['without_ml', 'with_ml', 'with_ml_zero']:
        snrs = [r['best_snr'] for r in results[key]]
        measurements = [r['measurements'] for r in results[key]]

        print(f"{key.replace('_', ' ').title():<25}")
        print(f"  Avg SNR:          {np.mean(snrs):>6.3f} dB (±{np.std(snrs):.3f})")
        print(f"  Avg Measurements: {np.mean(measurements):>5.2f}/7 ({100*np.mean(measurements)/7:>5.1f}%)")
        print()

    # Comparisons
    snr_no_ml = [r['best_snr'] for r in results['without_ml']]
    snr_with_ml = [r['best_snr'] for r in results['with_ml']]
    snr_with_ml_zero = [r['best_snr'] for r in results['with_ml_zero']]

    meas_no_ml = [r['measurements'] for r in results['without_ml']]
    meas_with_ml = [r['measurements'] for r in results['with_ml']]
    meas_with_ml_zero = [r['measurements'] for r in results['with_ml_zero']]

    print("="*80)
    print("IMPROVEMENTS vs BASELINE (No ML)")
    print("="*80 + "\n")

    snr_diff_xgb = np.mean(snr_with_ml) - np.mean(snr_no_ml)
    meas_saved_xgb = np.mean(meas_no_ml) - np.mean(meas_with_ml)
    meas_pct_xgb = 100 * meas_saved_xgb / np.mean(meas_no_ml)

    snr_diff_zero = np.mean(snr_with_ml_zero) - np.mean(snr_no_ml)
    meas_saved_zero = np.mean(meas_no_ml) - np.mean(meas_with_ml_zero)
    meas_pct_zero = 100 * meas_saved_zero / np.mean(meas_no_ml)

    print(f"XGBoost ML:")
    print(f"  ΔSNR:               {snr_diff_xgb:>+7.3f} dB")
    print(f"  Measurements saved: {meas_saved_xgb:>+5.2f} ({meas_pct_xgb:>+6.1f}%)")
    print()

    print(f"Zero-Offset ML:")
    print(f"  ΔSNR:               {snr_diff_zero:>+7.3f} dB")
    print(f"  Measurements saved: {meas_saved_zero:>+5.2f} ({meas_pct_zero:>+6.1f}%)")
    print()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("BEAM SWEEP WITH vs WITHOUT ML (COARSE STEP = 20°)")
    print("="*80 + "\n")

    results = run_coarse_sweep_comparison(num_tests=10)
    analyze_results(results)

    print("="*80)
    print("INTERPRETATION")
    print("="*80)
    print("With coarser step sizes (20°), there are fewer angles to test (7 vs 13).")
    print("ML can show benefits by:")
    print("  1. Guiding the sweep to test high-SNR angles first")
    print("  2. Avoiding wasteful measurements of low-SNR angles")
    print("  3. Reducing measurement count in early termination scenarios")
    print("="*80 + "\n")
