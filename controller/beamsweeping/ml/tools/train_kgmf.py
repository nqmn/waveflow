"""Train a KGMF beam predictor: sector classifier + Gaussian Mixture Fine sweep."""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path
from typing import List

import numpy as np

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn required (RandomForestClassifier). Install via `pip install scikit-learn`.") from exc

try:
    from sklearn.mixture import GaussianMixture
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn required (GaussianMixture). Install via `pip install scikit-learn`.") from exc

try:
    import joblib
except ImportError as exc:  # pragma: no cover
    raise SystemExit("joblib required to persist models. Install via `pip install joblib`.") from exc

FEATURE_COLUMNS = ['snr_dB', 'rssi_dBm', 'best_angle']


def _describe_classifier_quality(acc: float) -> str:
    if acc >= 0.90:
        return "✓ EXCELLENT - accuracy ≥ 90%"
    if acc >= 0.75:
        return "✓ GOOD - accuracy ≥ 75%"
    if acc >= 0.60:
        return "⚠ FAIR - accuracy ≥ 60%"
    return "✗ POOR - accuracy < 60%"


def _describe_gmm_quality(log_likelihood: float) -> str:
    if log_likelihood >= 4.0:
        return "✓ EXCELLENT - log-likelihood ≥ 4.0"
    if log_likelihood >= 3.5:
        return "✓ GOOD - log-likelihood ≥ 3.5"
    if log_likelihood >= 3.0:
        return "⚠ FAIR - log-likelihood ≥ 3.0"
    return "✗ POOR - log-likelihood < 3.0"


def load_dataset(path: Path) -> np.ndarray:
    """Load dataset columns (snr, rssi, best_angle)."""
    rows: List[List[float]] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            snr = float(row['snr_dB'])
            rssi = float(row['rssi_dBm'])
            angle = float(row['best_angle'])
            rows.append([snr, rssi, angle])
    return np.array(rows, dtype=float)


def compute_sector_labels(angle_deg: np.ndarray, n_sectors: int) -> np.ndarray:
    width = 360.0 / n_sectors
    normalized = np.mod(angle_deg, 360.0)
    labels = np.floor(normalized / width).astype(int)
    labels = np.clip(labels, 0, n_sectors - 1)
    return labels


def main():
    parser = argparse.ArgumentParser(description="Train KGMF beam predictor (sector + GMM)")
    parser.add_argument('--data', type=Path, required=True, help='Path to CSV beam dataset')
    parser.add_argument('--output-dir', type=Path, default=Path('controller/beamsweeping/ml/models'))
    parser.add_argument('--components', type=int, default=6, help='Number of GMM components')
    parser.add_argument('--covariance-type', type=str, default='full',
                        choices=('full', 'tied', 'diag', 'spherical'))
    parser.add_argument('--n-init', type=int, default=10, help='GMM EM restarts')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for both models')
    parser.add_argument('--sectors', type=int, default=18, help='Number of coarse beam sectors')
    args = parser.parse_args()

    print("Loading dataset...")
    load_start = time.time()
    data = load_dataset(args.data)
    load_time = time.time() - load_start
    print(f"  {data.shape[0]} samples loaded ({FEATURE_COLUMNS})")

    snr = data[:, 0]
    rssi = data[:, 1]
    angle_deg = data[:, 2]
    X = np.column_stack([snr, rssi])
    sector_labels = compute_sector_labels(angle_deg, args.sectors)

    print("\nTraining sector classifier (Random Forest)...")
    clf = RandomForestClassifier(n_estimators=150, random_state=args.seed, n_jobs=-1)
    clf.fit(X, sector_labels)
    classifier_accuracy = float(clf.score(X, sector_labels))

    print("\nFitting Gaussian Mixture Model...")
    fit_start = time.time()
    Z = np.column_stack([snr, rssi, np.deg2rad(angle_deg)])
    gmm = GaussianMixture(
        n_components=args.components,
        covariance_type=args.covariance_type,
        n_init=args.n_init,
        random_state=args.seed,
    )
    gmm.fit(Z)
    gmm_time = time.time() - fit_start

    log_likelihood = float(gmm.score(Z))
    bic = float(gmm.bic(Z))
    aic = float(gmm.aic(Z))

    print("\nEvaluation:")
    print(f"  Sector classifier accuracy: {classifier_accuracy * 100:.2f}% "
          f"({_describe_classifier_quality(classifier_accuracy)})")
    print(f"  GMM log-likelihood: {log_likelihood:.6f} {_describe_gmm_quality(log_likelihood)}")
    print(f"  GMM BIC: {bic:.2f}")
    print(f"  GMM AIC: {aic:.2f}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    sector_path = args.output_dir / "kgmf_sector_classifier.pkl"
    gmm_path = args.output_dir / "kgmf_gmm.pkl"
    joblib.dump(clf, sector_path)
    joblib.dump(gmm, gmm_path)
    print(f"\nSaved sector classifier to {sector_path}")
    print(f"Saved GMM prior to {gmm_path}")

    print("\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  GMM training: {gmm_time:.3f}s")
    print(f"  Total: {load_time + gmm_time:.3f}s")


if __name__ == "__main__":
    main()
