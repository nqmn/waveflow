"""Train a Random Forest beam predictor from generated dataset.

DATASET & FORMULA (Deflection Angle):
====================================
The training dataset uses the NEW DEFLECTION ANGLE FORMULA from formula.md, but the
Random Forest sees only AP-to-RIS geometry since UE coordinates are unavailable.

INPUT FEATURES (~18 features: AP/RIS positions + derived geometry + link metrics):
  - AP position (3 coords: x, y, z)
  - RIS position (3 coords: x, y, z)
  - Distance feature: d_ap_ris (Euclidean distance between AP and RIS)
  - AoA/AoD sines/cosines (incident/reflected azimuths)
  - AP→RIS offset + azimuth/elevation trig features
  - Link metrics: snr_dB, rssi_dBm computed for the AP→RIS→UE path

TRAINING TARGET (best_angle):
  - LOCAL DEFLECTION ANGLE in degrees (REGRESSION: continuous values)
  - Magnitude of azimuth difference: |arctan2(UE_y - RIS_y, UE_x - RIS_x) - arctan2(AP_y - RIS_y, AP_x - RIS_x)|
  - Range: 0° to 180° (always positive)
  - Represents: How much to deflect from incident direction to reach target

The model learns to predict the optimal deflection angle given AP-to-RIS geometry.
"""

from __future__ import annotations

import argparse
import csv
import pickle
import time
from pathlib import Path
from typing import List

import numpy as np

FEATURE_COLUMNS = [
    'ap_x', 'ap_y', 'ap_z',
    'ris_x', 'ris_y', 'ris_z',
    'd_ap_ris',
    'aoa_sin', 'aoa_cos',
    'dx', 'dy', 'dz',
    'az_sin', 'az_cos', 'el_sin', 'el_cos',
    'ap_az_sin', 'ap_az_cos', 'ap_el_sin', 'ap_el_cos',
    'spec_sin', 'spec_cos',
    'align_cos', 'align_sin',
    'snr_dB', 'rssi_dBm',
]

try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn is required. Install via `pip install scikit-learn`") from exc


def load_dataset(path: Path) -> tuple:
    """Load dataset from CSV file (REGRESSION: continuous angle values)."""
    X: List[List[float]] = []
    y: List[float] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Use the expanded geometry trig features plus link metrics.
            features = [float(row[col]) for col in FEATURE_COLUMNS]
            X.append(features)
            # Use continuous angle directly (no binning for regression)
            y.append(float(row['best_angle']))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y, n_estimators: int = 100, max_depth: int = 20, random_state: int = 42):
    model = RandomForestRegressor(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X, y)
    return model


def main():
    overall_start = time.time()
    parser = argparse.ArgumentParser(description="Train Random Forest beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/rf_beam_predictor.pkl'))
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of trees')
    parser.add_argument('--max-depth', type=int, default=20, help='Maximum tree depth')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
    args = parser.parse_args()

    print("Loading dataset...")
    load_start = time.time()
    X, y = load_dataset(args.data)
    load_time = time.time() - load_start
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    # Split into train/test sets
    print(f"\nSplitting data: {int((1-args.test_size)*100)}% train, {int(args.test_size*100)}% test")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )
    print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

    print("\nTraining Random Forest regression model...")
    train_start = time.time()
    model = train_model(X_train, y_train, n_estimators=args.n_estimators,
                       max_depth=args.max_depth, random_state=args.seed)
    train_time = time.time() - train_start

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    # Training metrics
    eval_start = time.time()
    y_train_pred = model.predict(X_train)
    train_mse = mean_squared_error(y_train, y_train_pred)
    train_rmse = np.sqrt(train_mse)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_r2 = r2_score(y_train, y_train_pred)

    print("\nTRAINING SET METRICS:")
    print(f"  MSE: {train_mse:>10.6f}")
    print(f"  RMSE: {train_rmse:>10.6f}°")
    print(f"  MAE: {train_mae:>10.6f}°")
    print(f"  R² Score: {train_r2:>10.6f}")

    # Test metrics
    y_test_pred = model.predict(X_test)
    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)
    eval_time = time.time() - eval_start

    print("\nTEST SET METRICS:")
    print(f"  MSE: {test_mse:>10.6f}")
    print(f"  RMSE: {test_rmse:>10.6f}°")
    print(f"  MAE: {test_mae:>10.6f}°")
    print(f"  R² Score: {test_r2:>10.6f}")

    # Assessment
    print("\nMODEL ASSESSMENT:")
    if test_r2 >= 0.90:
        assessment = "✓ EXCELLENT - R² ≥ 0.90"
    elif test_r2 >= 0.75:
        assessment = "✓ GOOD - R² ≥ 0.75"
    elif test_r2 >= 0.60:
        assessment = "⚠ FAIR - R² ≥ 0.60"
    else:
        assessment = "✗ POOR - R² < 0.60"
    print(f"  {assessment}")

    print("="*70)

    print("\nSaving model...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as f:
        pickle.dump(model, f)
    print(f"Saved Random Forest model to {args.output}")

    overall_time = time.time() - overall_start
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {overall_time:.3f}s")


if __name__ == "__main__":
    main()
