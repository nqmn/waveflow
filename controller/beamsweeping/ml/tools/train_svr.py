"""Train a Support Vector Regression (SVR) beam predictor from generated dataset.

DATASET & FORMULA (Deflection Angle):
====================================
The training dataset uses the NEW DEFLECTION ANGLE FORMULA from formula.md:

INPUT FEATURES (extracted from 3D node positions):
  - AP position (3 coords: x, y, z)
  - RIS position (3 coords: x, y, z)
  - UE position (3 coords: x, y, z)
  - Distance AP→RIS
  - Distance RIS→UE
  - AP transmit power (dBm)
  - AP frequency (Hz)
  - RIS element count (N)
  - RIS phase quantization bits

TRAINING TARGET (best_angle):
  - LOCAL DEFLECTION ANGLE in degrees
  - Magnitude of azimuth difference: |arctan2(UE_y - RIS_y, UE_x - RIS_x) - arctan2(AP_y - RIS_y, AP_x - RIS_x)|
  - Range: 0° to 180° (always positive)
  - Represents: How much to deflect from incident direction to reach target

The model learns to predict the optimal deflection angle given network geometry.
"""

from __future__ import annotations

import argparse
import csv
import pickle
from pathlib import Path
from typing import List

import numpy as np

try:
    from sklearn.svm import SVR
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn is required. Install via `pip install scikit-learn`") from exc


def load_dataset(path: Path):
    X: List[List[float]] = []
    y: List[float] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            ap_pos = [float(row['ap_x']), float(row['ap_y']), float(row['ap_z'])]
            ris_pos = [float(row['ris_x']), float(row['ris_y']), float(row['ris_z'])]
            ue_pos = [float(row['ue_x']), float(row['ue_y']), float(row['ue_z'])]
            vec_ap_ris = np.array(ris_pos) - np.array(ap_pos)
            vec_ris_ue = np.array(ue_pos) - np.array(ris_pos)
            features = [
                *ap_pos, *ris_pos, *ue_pos,
                float(np.linalg.norm(vec_ap_ris)),
                float(np.linalg.norm(vec_ris_ue)),
                float(row['ap_power_dBm']),
                float(row['ap_freq']),
                float(row['ris_N']),
                float(row['ris_bits']),
            ]
            X.append(features)
            y.append(float(row['best_angle']))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y, kernel: str = 'rbf', C: float = 100, gamma: str = 'scale', epsilon: float = 0.1):
    # Normalize features - critical for SVR performance
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = SVR(
        kernel=kernel,
        C=C,
        gamma=gamma,
        epsilon=epsilon,
    )
    model.fit(X_scaled, y)

    # Store scaler with model for inference
    model.scaler = scaler
    return model


def main():
    parser = argparse.ArgumentParser(description="Train Support Vector Regression (SVR) beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/svr_beam_predictor.pkl'))
    parser.add_argument('--kernel', type=str, default='rbf', choices=['linear', 'rbf', 'poly'], help='Kernel type')
    parser.add_argument('--C', type=float, default=100, help='Regularization parameter')
    parser.add_argument('--gamma', type=str, default='scale', choices=['scale', 'auto'], help='Gamma parameter')
    parser.add_argument('--epsilon', type=float, default=0.1, help='Epsilon for epsilon-SVR')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("Loading dataset...")
    X, y = load_dataset(args.data)
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    # Split into train/test sets
    print(f"\nSplitting data: {int((1-args.test_size)*100)}% train, {int(args.test_size*100)}% test")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )
    print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

    print(f"\nTraining SVR model with kernel={args.kernel}, C={args.C}, gamma={args.gamma}, epsilon={args.epsilon}...")
    model = train_model(X_train, y_train, kernel=args.kernel, C=args.C, gamma=args.gamma, epsilon=args.epsilon)

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    # Training metrics
    X_train_scaled = model.scaler.transform(X_train)
    y_train_pred = model.predict(X_train_scaled)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    train_r2 = r2_score(y_train, y_train_pred)

    print("\nTRAINING SET METRICS:")
    print(f"  MAE (Mean Absolute Error):  {train_mae:>10.6f}°")
    print(f"  RMSE (Root Mean Sq. Error): {train_rmse:>10.6f}°")
    print(f"  R² Score:                   {train_r2:>10.6f}")

    # Test metrics
    X_test_scaled = model.scaler.transform(X_test)
    y_test_pred = model.predict(X_test_scaled)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    test_r2 = r2_score(y_test, y_test_pred)

    print("\nTEST SET METRICS:")
    print(f"  MAE (Mean Absolute Error):  {test_mae:>10.6f}°")
    print(f"  RMSE (Root Mean Sq. Error): {test_rmse:>10.6f}°")
    print(f"  R² Score:                   {test_r2:>10.6f}")

    # Error statistics
    errors = np.abs(y_test - y_test_pred)
    print("\nERROR STATISTICS (Test Set):")
    print(f"  Mean Error:                 {np.mean(errors):>10.6f}°")
    print(f"  Median Error:               {np.median(errors):>10.6f}°")
    print(f"  Std Dev:                    {np.std(errors):>10.6f}°")
    print(f"  Min Error:                  {np.min(errors):>10.6f}°")
    print(f"  Max Error:                  {np.max(errors):>10.6f}°")
    print(f"  95th Percentile Error:      {np.percentile(errors, 95):>10.6f}°")

    # Assessment
    print("\nMODEL ASSESSMENT:")
    if test_mae < 2.0:
        assessment = "✓ EXCELLENT - MAE < 2° (very accurate predictions)"
    elif test_mae < 3.0:
        assessment = "✓ GOOD - MAE < 3° (accurate predictions)"
    elif test_mae < 5.0:
        assessment = "⚠ FAIR - MAE < 5° (acceptable for coarse guidance)"
    else:
        assessment = "✗ POOR - MAE ≥ 5° (insufficient accuracy, need more data)"
    print(f"  {assessment}")

    if test_r2 > 0.9:
        fit_quality = "✓ Excellent fit (explains > 90% of variance)"
    elif test_r2 > 0.7:
        fit_quality = "✓ Good fit (explains > 70% of variance)"
    elif test_r2 > 0.5:
        fit_quality = "⚠ Fair fit (explains > 50% of variance)"
    else:
        fit_quality = "✗ Poor fit (explains < 50% of variance)"
    print(f"  {fit_quality}")

    print("="*70)

    print("\nSaving model...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as f:
        pickle.dump(model, f)
    print(f"Saved SVR model to {args.output}")


if __name__ == "__main__":
    main()
