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

FEATURE_COLUMNS = ['snr_dB', 'rssi_dBm', 'd_ap_ris', 'aoa_sin', 'aoa_cos', 'el_sin', 'el_cos', 'dx', 'dy', 'dz', 'best_angle']


def _describe_model_quality(log_likelihood: float) -> str:
    if log_likelihood >= 4.0:
        return "✓ EXCELLENT - log-likelihood ≥ 4.0"
    if log_likelihood >= 3.5:
        return "✓ GOOD - log-likelihood ≥ 3.5"
    if log_likelihood >= 3.0:
        return "⚠ FAIR - log-likelihood ≥ 3.0"
    return "✗ POOR - log-likelihood < 3.0"


def evaluate_gmm_predictions(gmm, X: np.ndarray, y: np.ndarray, resolution: float = 1.0) -> dict:
    """Evaluate GMM by computing MAE on angle predictions.

    For each sample, extracts the most likely angle from the posterior.
    """
    angle_grid = np.arange(0, 60.0 + resolution, resolution)
    predictions = []

    for i in range(X.shape[0]):
        obs = X[i:i+1]
        angles_rad = np.radians(angle_grid)
        obs_matrix = np.repeat(obs, len(angles_rad), axis=0)
        samples = np.hstack([obs_matrix, angles_rad.reshape(-1, 1)])

        log_likelihoods = gmm.score_samples(samples)
        log_likelihoods -= np.max(log_likelihoods)
        posterior = np.exp(log_likelihoods)
        posterior /= np.sum(posterior)

        predicted_angle = angle_grid[np.argmax(posterior)]
        predictions.append(predicted_angle)

        if (i + 1) % 20000 == 0:
            print(f"    Evaluated {i+1}/{X.shape[0]} samples...")

    predictions = np.array(predictions)
    mae = np.mean(np.abs(predictions - y))
    rmse = np.sqrt(np.mean((predictions - y) ** 2))
    max_error = np.max(np.abs(predictions - y))

    return {
        'mae': float(mae),
        'rmse': float(rmse),
        'max_error': float(max_error),
    }


def load_features(path: Path) -> np.ndarray:
    """Extract [snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, dx, dy, dz, angle_rad] rows from the CSV dataset."""
    rows: List[List[float]] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            snr = float(row['snr_dB'])
            rssi = float(row['rssi_dBm'])
            d_ap_ris = float(row['d_ap_ris'])
            aoa_sin = float(row['aoa_sin'])
            aoa_cos = float(row['aoa_cos'])
            el_sin = float(row['el_sin'])
            el_cos = float(row['el_cos'])
            dx = float(row['dx'])
            dy = float(row['dy'])
            dz = float(row['dz'])
            angle_rad = math.radians(float(row['best_angle']))
            rows.append([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, dx, dy, dz, angle_rad])
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
    print(f"  Input shape: {data.shape} (11D: 10 features + 1 label)")
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

    # Compute angle prediction metrics
    print("\nComputing angle prediction metrics...")
    eval_start = time.time()
    X = data[:, :-1]  # All columns except last
    y = np.degrees(data[:, -1])  # Last column (best_angle in radians) -> convert to degrees
    pred_metrics = evaluate_gmm_predictions(gmm, X, y)
    eval_time = time.time() - eval_start

    print("\nAngle Prediction Metrics:")
    print(f"  MAE:       {pred_metrics['mae']:.4f}°")
    print(f"  RMSE:      {pred_metrics['rmse']:.4f}°")
    print(f"  Max Error: {pred_metrics['max_error']:.4f}°")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(gmm, args.output)
    print(f"\nSaved GMM prior to {args.output}")

    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  GMM training: {fit_time:.3f}s")
    print(f"  Evaluation:   {eval_time:.3f}s")
    print(f"  Total: {load_time + fit_time + eval_time:.3f}s")


if __name__ == "__main__":
    main()
