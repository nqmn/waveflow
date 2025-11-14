"""Train a Linear Regression beam predictor from generated dataset.

DATASET & FORMULA (Deflection Angle):
====================================
The training dataset uses the NEW DEFLECTION ANGLE FORMULA from formula.md:

INPUT FEATURES (13 features: 9 position coordinates + 4 derived features):
  - AP position (3 coords: x, y, z)
  - RIS position (3 coords: x, y, z)
  - UE position (3 coords: x, y, z)
  - Distance features: d_ap_ris, d_ris_ue
  - Angle features: aoa (Angle of Arrival), aod (Angle of Departure)

TRAINING TARGET (best_angle):
  - LOCAL DEFLECTION ANGLE in degrees (REGRESSION: continuous values)
  - Magnitude of azimuth difference: |arctan2(UE_y - RIS_y, UE_x - RIS_x) - arctan2(AP_y - RIS_y, AP_x - RIS_x)|
  - Range: 0° to 180° (always positive)
  - Represents: How much to deflect from incident direction to reach target

The model learns to predict the optimal deflection angle given network geometry.
"""

from __future__ import annotations

import argparse
import csv
import pickle
import time
from pathlib import Path
from typing import List

import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
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
            # Use 13 features: 9 position + 4 derived (distances + angles)
            features = [
                # Position features (3D coordinates)
                float(row['ap_x']), float(row['ap_y']), float(row['ap_z']),
                float(row['ris_x']), float(row['ris_y']), float(row['ris_z']),
                float(row['ue_x']), float(row['ue_y']), float(row['ue_z']),
                # Distance features
                float(row['d_ap_ris']), float(row['d_ris_ue']),
                # Angle features (Angle of Arrival, Angle of Departure)
                float(row['aoa']), float(row['aod']),
            ]
            X.append(features)
            # Use continuous angle directly (no binning for regression)
            y.append(float(row['best_angle']))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y):
    # Normalize features for better linear regression performance
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = LinearRegression()
    model.fit(X_scaled, y)

    # Store scaler with model for inference
    model.scaler = scaler
    return model


def main():
    overall_start = time.time()
    parser = argparse.ArgumentParser(description="Train Linear Regression beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/lr_beam_predictor.pkl'))
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
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

    print("\nTraining Linear Regression regression model...")
    train_start = time.time()
    model = train_model(X_train, y_train)
    train_time = time.time() - train_start

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    # Training metrics
    eval_start = time.time()
    X_train_scaled = model.scaler.transform(X_train)
    y_train_pred = model.predict(X_train_scaled)
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
    X_test_scaled = model.scaler.transform(X_test)
    y_test_pred = model.predict(X_test_scaled)
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
    print(f"Saved Linear Regression model to {args.output}")

    overall_time = time.time() - overall_start
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {overall_time:.3f}s")


if __name__ == "__main__":
    main()
