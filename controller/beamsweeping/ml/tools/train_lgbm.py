"""Train a LightGBM beam predictor from the generated dataset."""

from __future__ import annotations

import argparse
import csv
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
    import lightgbm as lgb  # type: ignore
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
except ImportError as exc:  # pragma: no cover
    raise SystemExit("lightgbm and scikit-learn are required. Install via `pip install lightgbm scikit-learn`.") from exc


def load_dataset(path: Path) -> tuple:
    """Load dataset from CSV file (REGRESSION: continuous angle values)."""
    X: List[List[float]] = []
    y: List[float] = []
    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            features = [float(row[col]) for col in FEATURE_COLUMNS]
            X.append(features)
            y.append(float(row['best_angle']))
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y, params, num_boost_round: int = 500):
    dataset = lgb.Dataset(X, label=y)
    booster = lgb.train(params, dataset, num_boost_round=num_boost_round)
    return booster


def main():
    overall_start = time.time()
    parser = argparse.ArgumentParser(description="Train LightGBM beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path,
                        default=Path('controller/beamsweeping/ml/models/lgbm_beam_predictor.txt'))
    parser.add_argument('--num-leaves', type=int, default=31, help='LightGBM tree leaves')
    parser.add_argument('--learning-rate', type=float, default=0.1, help='Learning rate')
    parser.add_argument('--num-boost-rounds', type=int, default=500, help='Number of boosting rounds')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
    args = parser.parse_args()

    print("Loading dataset...")
    load_start = time.time()
    X, y = load_dataset(args.data)
    load_time = time.time() - load_start
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )
    print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'num_leaves': args.num_leaves,
        'learning_rate': args.learning_rate,
        'verbose': -1,
        'seed': args.seed,
    }

    print("\nTraining LightGBM regression model...")
    train_start = time.time()
    booster = train_model(X_train, y_train, params, num_boost_round=args.num_boost_rounds)
    train_time = time.time() - train_start

    # Evaluate
    eval_start = time.time()
    y_train_pred = booster.predict(X_train)
    y_test_pred = booster.predict(X_test)
    eval_time = time.time() - eval_start

    train_mse = mean_squared_error(y_train, y_train_pred)
    test_mse = mean_squared_error(y_test, y_test_pred)
    train_rmse = np.sqrt(train_mse)
    test_rmse = np.sqrt(test_mse)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    train_r2 = r2_score(y_train, y_train_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print("\nTRAINING SET METRICS:")
    print(f"  MSE: {train_mse:.6f}")
    print(f"  RMSE: {train_rmse:.6f}°")
    print(f"  MAE: {train_mae:.6f}°")
    print(f"  R² Score: {train_r2:.6f}")

    print("\nTEST SET METRICS:")
    print(f"  MSE: {test_mse:.6f}")
    print(f"  RMSE: {test_rmse:.6f}°")
    print(f"  MAE: {test_mae:.6f}°")
    print(f"  R² Score: {test_r2:.6f}")

    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(output_path))
    print(f"✓ Model saved to {output_path}")

    overall_time = time.time() - overall_start
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {overall_time:.3f}s")


if __name__ == "__main__":
    main()
