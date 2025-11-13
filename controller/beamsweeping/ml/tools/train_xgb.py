"""Train an XGBoost beam predictor from generated dataset.

DATASET & FORMULA (Deflection Angle):
====================================
The training dataset uses the NEW DEFLECTION ANGLE FORMULA from formula.md:

INPUT FEATURES (extracted from 3D node positions and computed angles):
  - AP position (3 coords: x, y, z)
  - RIS position (3 coords: x, y, z)
  - UE position (3 coords: x, y, z)
  - Distance AP→RIS
  - Distance RIS→UE
  - AP transmit power (dBm)
  - AP frequency (Hz)
  - RIS element count (N)
  - RIS phase quantization bits
  - AOA (Angle of Arrival): AP direction from RIS perspective (degrees)
  - AOD (Angle of Departure): UE direction from RIS perspective (degrees)
  - Deflection angle: |AOD - AOA| normalized to [0°, 180°]

TRAINING TARGET (best_angle):
  - LOCAL DEFLECTION ANGLE in degrees
  - Magnitude of azimuth difference: |arctan2(UE_y - RIS_y, UE_x - RIS_x) - arctan2(AP_y - RIS_y, AP_x - RIS_x)|
  - Range: 0° to 180° (always positive)
  - Represents: How much to deflect from incident direction to reach target

The model learns to predict the optimal deflection angle given network geometry and angle features.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

import numpy as np

try:
    import xgboost as xgb  # type: ignore
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
except ImportError as exc:  # pragma: no cover
    raise SystemExit("xgboost and scikit-learn packages required. Install via `pip install xgboost scikit-learn`.") from exc


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

            # Extract or compute angle features
            aoa_deg = float(row.get('aoa_deg', 0.0))
            aod_deg = float(row.get('aod_deg', 0.0))
            deflection_deg = float(row.get('deflection_deg', 0.0))

            features = [
                *ap_pos, *ris_pos, *ue_pos,
                float(np.linalg.norm(vec_ap_ris)),
                float(np.linalg.norm(vec_ris_ue)),
                float(row['ap_power_dBm']),
                float(row['ap_freq']),
                float(row['ris_N']),
                float(row['ris_bits']),
                aoa_deg,
                aod_deg,
                deflection_deg,
            ]
            X.append(features)
            y.append(float(row['best_angle']))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y, params):
    dtrain = xgb.DMatrix(X, label=y)
    booster = xgb.train(params, dtrain, num_boost_round=300)
    return booster


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/xgb_beam_predictor.json'))
    parser.add_argument('--max-depth', type=int, default=6)
    parser.add_argument('--eta', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
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

    print("\nTraining XGBoost model...")
    params = {
        'objective': 'reg:squarederror',
        'max_depth': args.max_depth,
        'eta': args.eta,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': args.seed,
    }
    booster = train_model(X_train, y_train, params)

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    # Training metrics
    y_train_pred = booster.predict(xgb.DMatrix(X_train))
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    train_r2 = r2_score(y_train, y_train_pred)

    print("\nTRAINING SET METRICS:")
    print(f"  MAE (Mean Absolute Error):  {train_mae:>10.6f}°")
    print(f"  RMSE (Root Mean Sq. Error): {train_rmse:>10.6f}°")
    print(f"  R² Score:                   {train_r2:>10.6f}")

    # Test metrics
    y_test_pred = booster.predict(xgb.DMatrix(X_test))
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
    booster.save_model(str(args.output))
    print(f"Saved XGBoost model to {args.output}")


if __name__ == "__main__":
    main()
