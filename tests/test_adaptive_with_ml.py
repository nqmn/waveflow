#!/usr/bin/env python3
"""Compare ADAPTIVE SWEEP (which can early-terminate) with and without ML"""

import json
import os
import random
from pathlib import Path
import numpy as np
from core.network import RISNetwork
from controller.beamsweeping import MLPredictorLoader, SweepAlgorithmLoader

def run_adaptive_comparison(num_tests=10):
    """Run adaptive sweeps which can terminate early"""

    results = {
        'without_ml': [],
        'with_ml': [],
    }

    random.seed(42)
    np.random.seed(42)

    print(f"Running {num_tests} ADAPTIVE sweep comparisons...\n")

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

        # Test 1: Adaptive without ML
        algo1 = SweepAlgorithmLoader.get_algorithm("center-out", net)
        result_no_ml = algo1.sweep('AP', 'RIS', 'UE', fov=60.0, step=20.0, ml_angles=None)
        coarse_no_ml = len([s for s in result_no_ml['snr_coarse'] if not np.isnan(s)])

        # Test 2: Adaptive with XGBoost ML
        os.environ['RISNET_XGB_MODEL'] = '/tmp/xgb_beam_predictor_custom_10dbm_1bit.json'
        predictor = MLPredictorLoader.get_predictor('default', net)
        ml_angles = predictor.predict_local_angles('AP', 'RIS', 'UE', fov=60.0, top_k=3)

        algo2 = SweepAlgorithmLoader.get_algorithm("center-out", net)
        result_with_ml = algo2.sweep('AP', 'RIS', 'UE', fov=60.0, step=20.0, ml_angles=ml_angles)
        coarse_with_ml = len([s for s in result_with_ml['snr_coarse'] if not np.isnan(s)])

        results['without_ml'].append({
            'best_snr': result_no_ml['best_snr_fine'],
            'best_angle': result_no_ml['best_local_fine'],
            'coarse_measurements': coarse_no_ml,
            'fine_measurements': len(result_no_ml['snr_fine']),
            'total_measurements': coarse_no_ml + len(result_no_ml['snr_fine']),
        })

        results['with_ml'].append({
            'best_snr': result_with_ml['best_snr_fine'],
            'best_angle': result_with_ml['best_local_fine'],
            'coarse_measurements': coarse_with_ml,
            'fine_measurements': len(result_with_ml['snr_fine']),
            'total_measurements': coarse_with_ml + len(result_with_ml['snr_fine']),
            'ml_angles': ml_angles,
        })

        if test_num < 3:
            print(f"Test {test_num + 1}:")
            print(f"  No ML:       Best={result_no_ml['best_snr_fine']:>7.2f}dB | "
                  f"Angle={result_no_ml['best_local_fine']:>6.1f}° | "
                  f"Coarse: {coarse_no_ml}/7 | Fine: {len(result_no_ml['snr_fine'])}")
            print(f"  With ML:     Best={result_with_ml['best_snr_fine']:>7.2f}dB | "
                  f"Angle={result_with_ml['best_local_fine']:>6.1f}° | "
                  f"Coarse: {coarse_with_ml}/7 | Fine: {len(result_with_ml['snr_fine'])} | "
                  f"ML: {[f'{a:.1f}' for a in ml_angles[:2]]}")
            print()

    return results


def analyze_results(results):
    """Analyze and compare results"""

    print("\n" + "="*80)
    print("SUMMARY STATISTICS (Adaptive Sweep, 20° step)")
    print("="*80 + "\n")

    for key in ['without_ml', 'with_ml']:
        snrs = [r['best_snr'] for r in results[key]]
        coarse = [r['coarse_measurements'] for r in results[key]]
        fine = [r['fine_measurements'] for r in results[key]]
        total = [r['total_measurements'] for r in results[key]]

        print(f"{key.replace('_', ' ').title():<20}")
        print(f"  Avg SNR:          {np.mean(snrs):>6.3f} dB (±{np.std(snrs):.3f})")
        print(f"  Coarse meas:      {np.mean(coarse):>5.1f}/7")
        print(f"  Fine meas:        {np.mean(fine):>5.1f}")
        print(f"  Total meas:       {np.mean(total):>5.1f}")
        print()

    # Comparisons
    snr_no_ml = [r['best_snr'] for r in results['without_ml']]
    snr_with_ml = [r['best_snr'] for r in results['with_ml']]

    total_no_ml = [r['total_measurements'] for r in results['without_ml']]
    total_with_ml = [r['total_measurements'] for r in results['with_ml']]

    print("="*80)
    print("IMPROVEMENT WITH ML")
    print("="*80 + "\n")

    snr_diff = np.mean(snr_with_ml) - np.mean(snr_no_ml)
    meas_saved = np.mean(total_no_ml) - np.mean(total_with_ml)
    meas_pct = 100 * meas_saved / np.mean(total_no_ml) if np.mean(total_no_ml) > 0 else 0

    print(f"SNR difference:       {snr_diff:>+6.3f} dB")
    print(f"Measurements saved:   {meas_saved:>+5.2f} ({meas_pct:>+5.1f}%)")
    print(f"Avg total measurements: {np.mean(total_no_ml):.1f} → {np.mean(total_with_ml):.1f}")
    print()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ADAPTIVE SWEEP WITH vs WITHOUT ML")
    print("="*80 + "\n")

    results = run_adaptive_comparison(num_tests=10)
    analyze_results(results)

    print("="*80)
