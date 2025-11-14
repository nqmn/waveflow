"""Train all beam predictor models (XGBoost, SVR, Random Forest, KNN, Linear Regression) from dataset.

This script trains all five ML models for faster execution.
Each model learns to predict the optimal deflection angle given network geometry.

Models trained (all use REGRESSION):
  1. XGBoost - Gradient boosted regression trees
  2. SVR (Support Vector Regression) - Kernel-based regression
  3. Random Forest - Ensemble of regression trees
  4. KNN (K-Nearest Neighbors) - Distance-based regression
  5. Linear Regression - Simple linear regression model

Usage:
    python train_all.py --data controller/beamsweeping/ml/data/beam_dataset.csv
"""

from __future__ import annotations

import argparse
import csv
import pickle
import subprocess
import sys
import time
from pathlib import Path
from typing import List

import numpy as np

try:
    from sklearn.model_selection import train_test_split
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


def train_xgb(data_path: Path, output_path: Path, seed: int, test_size: float) -> None:
    """Train XGBoost regression model."""
    print("\n" + "="*70)
    print("TRAINING XGBOOST MODEL (REGRESSION)")
    print("="*70)
    start_time = time.time()

    try:
        import xgboost as xgb
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    except ImportError as exc:
        print(f"✗ XGBoost training skipped: {exc}")
        return

    load_start = time.time()
    X, y = load_dataset(data_path)
    load_time = time.time() - load_start

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    dtrain = xgb.DMatrix(X_train, label=y_train)
    params = {
        'objective': 'reg:squarederror',
        'max_depth': 6,
        'eta': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': seed,
    }

    train_start = time.time()
    booster = xgb.train(params, dtrain, num_boost_round=300)
    train_time = time.time() - train_start

    # Evaluate
    eval_start = time.time()
    y_test_pred = booster.predict(xgb.DMatrix(X_test))
    eval_time = time.time() - eval_start

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"Test MSE: {test_mse:.6f}")
    print(f"Test RMSE: {test_rmse:.6f}°")
    print(f"Test MAE: {test_mae:.6f}°")
    print(f"Test R² Score: {test_r2:.6f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(output_path))
    print(f"✓ Model saved to {output_path}")

    total_time = time.time() - start_time
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")


def train_svr(data_path: Path, output_path: Path, seed: int, test_size: float) -> None:
    """Train SVR (Support Vector Regression) model."""
    print("\n" + "="*70)
    print("TRAINING SVR MODEL (REGRESSION)")
    print("="*70)
    start_time = time.time()

    try:
        from sklearn.svm import SVR
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    except ImportError as exc:
        print(f"✗ SVR training skipped: {exc}")
        return

    load_start = time.time()
    X, y = load_dataset(data_path)
    load_time = time.time() - load_start

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    train_start = time.time()
    model = SVR(kernel='rbf', C=100, gamma='scale', epsilon=1.0)
    model.fit(X_train_scaled, y_train)
    train_time = time.time() - train_start
    model.scaler = scaler

    # Evaluate
    eval_start = time.time()
    X_test_scaled = scaler.transform(X_test)
    y_test_pred = model.predict(X_test_scaled)
    eval_time = time.time() - eval_start

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"Test MSE: {test_mse:.6f}")
    print(f"Test RMSE: {test_rmse:.6f}°")
    print(f"Test MAE: {test_mae:.6f}°")
    print(f"Test R² Score: {test_r2:.6f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        pickle.dump(model, f)
    print(f"✓ Model saved to {output_path}")

    total_time = time.time() - start_time
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")


def train_rf(data_path: Path, output_path: Path, seed: int, test_size: float) -> None:
    """Train Random Forest regression model."""
    print("\n" + "="*70)
    print("TRAINING RANDOM FOREST MODEL (REGRESSION)")
    print("="*70)
    start_time = time.time()

    try:
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    except ImportError as exc:
        print(f"✗ Random Forest training skipped: {exc}")
        return

    load_start = time.time()
    X, y = load_dataset(data_path)
    load_time = time.time() - load_start

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    train_start = time.time()
    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=20,
        min_samples_split=5,
        min_samples_leaf=2,
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    train_time = time.time() - train_start

    # Evaluate
    eval_start = time.time()
    y_test_pred = model.predict(X_test)
    eval_time = time.time() - eval_start

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"Test MSE: {test_mse:.6f}")
    print(f"Test RMSE: {test_rmse:.6f}°")
    print(f"Test MAE: {test_mae:.6f}°")
    print(f"Test R² Score: {test_r2:.6f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        pickle.dump(model, f)
    print(f"✓ Model saved to {output_path}")

    total_time = time.time() - start_time
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")


def train_knn(data_path: Path, output_path: Path, seed: int, test_size: float) -> None:
    """Train K-Nearest Neighbors regression model."""
    print("\n" + "="*70)
    print("TRAINING KNN MODEL (REGRESSION)")
    print("="*70)
    start_time = time.time()

    try:
        from sklearn.neighbors import KNeighborsRegressor
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    except ImportError as exc:
        print(f"✗ KNN training skipped: {exc}")
        return

    load_start = time.time()
    X, y = load_dataset(data_path)
    load_time = time.time() - load_start

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    # Normalize features - critical for KNN performance
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    train_start = time.time()
    model = KNeighborsRegressor(
        n_neighbors=5,
        weights='distance',
        metric='minkowski',
        n_jobs=-1,
    )
    model.fit(X_train_scaled, y_train)
    train_time = time.time() - train_start
    model.scaler = scaler

    # Evaluate
    eval_start = time.time()
    X_test_scaled = scaler.transform(X_test)
    y_test_pred = model.predict(X_test_scaled)
    eval_time = time.time() - eval_start

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"Test MSE: {test_mse:.6f}")
    print(f"Test RMSE: {test_rmse:.6f}°")
    print(f"Test MAE: {test_mae:.6f}°")
    print(f"Test R² Score: {test_r2:.6f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        pickle.dump(model, f)
    print(f"✓ Model saved to {output_path}")

    total_time = time.time() - start_time
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")


def train_lr(data_path: Path, output_path: Path, seed: int, test_size: float) -> None:
    """Train Linear Regression model."""
    print("\n" + "="*70)
    print("TRAINING LINEAR REGRESSION MODEL (REGRESSION)")
    print("="*70)
    start_time = time.time()

    try:
        from sklearn.linear_model import LinearRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
    except ImportError as exc:
        print(f"✗ Linear Regression training skipped: {exc}")
        return

    load_start = time.time()
    X, y = load_dataset(data_path)
    load_time = time.time() - load_start

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=seed
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)

    train_start = time.time()
    model = LinearRegression()
    model.fit(X_train_scaled, y_train)
    train_time = time.time() - train_start
    model.scaler = scaler

    # Evaluate
    eval_start = time.time()
    X_test_scaled = scaler.transform(X_test)
    y_test_pred = model.predict(X_test_scaled)
    eval_time = time.time() - eval_start

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print(f"Test MSE: {test_mse:.6f}")
    print(f"Test RMSE: {test_rmse:.6f}°")
    print(f"Test MAE: {test_mae:.6f}°")
    print(f"Test R² Score: {test_r2:.6f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('wb') as f:
        pickle.dump(model, f)
    print(f"✓ Model saved to {output_path}")

    total_time = time.time() - start_time
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {total_time:.3f}s")


def main():
    parser = argparse.ArgumentParser(description="Train all beam predictor models")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('controller/beamsweeping/ml/models'),
                       help='Output directory for models')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction')
    parser.add_argument('--skip-xgb', action='store_true', help='Skip XGBoost training')
    parser.add_argument('--skip-svr', action='store_true', help='Skip SVR training')
    parser.add_argument('--skip-rf', action='store_true', help='Skip Random Forest training')
    parser.add_argument('--skip-knn', action='store_true', help='Skip KNN training')
    parser.add_argument('--skip-lr', action='store_true', help='Skip Linear Regression training')
    args = parser.parse_args()

    if not args.data.exists():
        print(f"✗ Dataset not found: {args.data}")
        sys.exit(1)

    print("\n" + "="*70)
    print("TRAINING ALL BEAM PREDICTOR MODELS")
    print("="*70)
    print(f"Dataset: {args.data}")
    print(f"Output directory: {args.output_dir}")
    print(f"Random seed: {args.seed}")
    print(f"Test set size: {args.test_size}")

    # Track overall timing
    overall_start = time.time()

    # Train all models
    if not args.skip_xgb:
        train_xgb(args.data, args.output_dir / 'xgb_beam_predictor.json',
                 args.seed, args.test_size)

    if not args.skip_svr:
        train_svr(args.data, args.output_dir / 'svr_beam_predictor.pkl',
                 args.seed, args.test_size)

    if not args.skip_rf:
        train_rf(args.data, args.output_dir / 'rf_beam_predictor.pkl',
                args.seed, args.test_size)

    if not args.skip_knn:
        train_knn(args.data, args.output_dir / 'knn_beam_predictor.pkl',
                 args.seed, args.test_size)

    if not args.skip_lr:
        train_lr(args.data, args.output_dir / 'lr_beam_predictor.pkl',
                args.seed, args.test_size)

    overall_time = time.time() - overall_start

    print("\n" + "="*70)
    print("✓ ALL MODELS TRAINED SUCCESSFULLY")
    print("="*70)
    print(f"\n⏱ Overall training time: {overall_time:.2f}s ({overall_time/60:.2f} minutes)")


if __name__ == "__main__":
    main()
