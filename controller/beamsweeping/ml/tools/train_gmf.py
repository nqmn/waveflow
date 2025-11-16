"""Train a Gaussian Mixture fingerprint model from beam dataset."""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path
from typing import List

import numpy as np

try:
    from sklearn.mixture import GaussianMixture
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn required (GaussianMixture). Install via `pip install scikit-learn`.") from exc

try:
    import joblib
except ImportError as exc:  # pragma: no cover
    raise SystemExit("joblib required to persist GMM. Install via `pip install joblib`.") from exc

FEATURE_COLUMNS = ['snr_dB', 'rssi_dBm', 'd_ap_ris', 'aoa_sin', 'aoa_cos', 'best_angle']


def _describe_model_quality(log_likelihood: float) -> str:
    if log_likelihood >= 4.0:
        return "✓ EXCELLENT - log-likelihood ≥ 4.0"
    if log_likelihood >= 3.5:
        return "✓ GOOD - log-likelihood ≥ 3.5"
    if log_likelihood >= 3.0:
        return "⚠ FAIR - log-likelihood ≥ 3.0"
    return "✗ POOR - log-likelihood < 3.0"


def load_features(path: Path) -> np.ndarray:
    """Extract [snr, rssi, d_ap_ris, aoa_sin, aoa_cos, angle_rad] rows from the CSV dataset."""
    rows: List[List[float]] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            snr = float(row['snr_dB'])
            rssi = float(row['rssi_dBm'])
            angle_rad = math.radians(float(row['best_angle']))
            d_ap_ris = float(row['d_ap_ris'])
            aoa_sin = float(row['aoa_sin'])
            aoa_cos = float(row['aoa_cos'])
            rows.append([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, angle_rad])
    return np.array(rows, dtype=float)


def main():
    parser = argparse.ArgumentParser(description="Train Gaussian Mixture fingerprint model")
    parser.add_argument('--data', type=Path, required=True, help='Path to CSV beam dataset')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/gmf_beam_prior.pkl'))
    parser.add_argument('--components', type=int, default=6, help='Number of Gaussian components')
    parser.add_argument('--covariance-type', type=str, default='full',
                        choices=('full', 'tied', 'diag', 'spherical'))
    parser.add_argument('--n-init', type=int, default=10, help='Number of EM initializations')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("Loading dataset...")
    load_start = time.time()
    data = load_features(args.data)
    load_time = time.time() - load_start
    print(f"  {data.shape[0]} samples extracted (features: {FEATURE_COLUMNS})")

    print("\nFitting Gaussian Mixture Model...")
    fit_start = time.time()
    gmm = GaussianMixture(
        n_components=args.components,
        covariance_type=args.covariance_type,
        n_init=args.n_init,
        random_state=args.seed,
    )
    gmm.fit(data)
    fit_time = time.time() - fit_start

    print("\nEvaluation:")
    log_likelihood = float(gmm.score(data))
    bic = float(gmm.bic(data))
    aic = float(gmm.aic(data))
    print(f"  Log-likelihood: {log_likelihood:.6f}")
    print(f"  BIC: {bic:.2f}")
    print(f"  AIC: {aic:.2f}")
    print(f"  Assessment: {_describe_model_quality(log_likelihood)}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(gmm, args.output)
    print(f"\nSaved GMM prior to {args.output}")

    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  GMM training: {fit_time:.3f}s")
    print(f"  Total: {load_time + fit_time:.3f}s")


if __name__ == "__main__":
    main()
