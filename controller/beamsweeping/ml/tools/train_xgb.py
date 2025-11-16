"""Train an XGBoost beam predictor with preprocessing (scaling, PCA, clustering).

The dataset encodes deflection angles computed from AP→RIS→UE geometries. Because
the raw feature space is highly correlated, we first standardize the features,
reduce them via PCA, and attach a cluster label from KMeans before training the
regressor. The same preprocessing pipeline is saved alongside the trained booster
so inference can apply the same transforms.
"""

from __future__ import annotations

import argparse
import csv
import json
import pickle
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import xgboost as xgb  # type: ignore
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
except ImportError as exc:  # pragma: no cover
    raise SystemExit("xgboost and scikit-learn packages required. Install via `pip install xgboost scikit-learn`.") from exc

FEATURE_COLUMNS = [
    'd_ap_ris',
    'aoa_sin', 'aoa_cos',
    'dx', 'dy', 'dz',
    'spec_sin', 'spec_cos',
    'align_cos', 'align_sin',
    'snr_dB', 'rssi_dBm',
]

SCALER_FILENAME = "xgb_scaler.pkl"
PCA_FILENAME = "xgb_pca.pkl"
KMEANS_FILENAME = "xgb_kmeans.pkl"
PIPELINE_META_FILENAME = "xgb_pipeline.json"
DEFAULT_PCA_COMPONENTS = 3
DEFAULT_KMEANS_CLUSTERS = 4


def load_dataset(path: Path) -> Tuple[np.ndarray, np.ndarray]:
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


def _stack_pipeline_features(X_pca: np.ndarray, cluster_ids: np.ndarray) -> np.ndarray:
    """Attach the KMeans cluster identifier as an extra column."""
    cluster_col = cluster_ids.reshape(-1, 1).astype(float)
    return np.hstack([X_pca, cluster_col])


def _fit_preprocessing_pipeline(
    X_train: np.ndarray,
    args: argparse.Namespace
) -> Tuple[StandardScaler, PCA, KMeans, np.ndarray, np.ndarray]:
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    pca = PCA(n_components=args.pca_components, random_state=args.seed)
    X_train_pca = pca.fit_transform(X_train_scaled)
    kmeans = KMeans(
        n_clusters=args.kmeans_clusters,
        random_state=args.seed,
        n_init=10,
    )
    train_clusters = kmeans.fit_predict(X_train_pca)
    return scaler, pca, kmeans, X_train_pca, train_clusters


def _apply_pipeline(
    X: np.ndarray,
    scaler: StandardScaler,
    pca: PCA,
    kmeans: KMeans
) -> Tuple[np.ndarray, np.ndarray]:
    X_scaled = scaler.transform(X)
    X_pca = pca.transform(X_scaled)
    clusters = kmeans.predict(X_pca)
    return X_pca, clusters


def _save_pipeline_artifacts(
    pipeline_dir: Path,
    scaler: StandardScaler,
    pca: PCA,
    kmeans: KMeans,
    args: argparse.Namespace,
    sample_count: int,
) -> None:
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    with (pipeline_dir / SCALER_FILENAME).open('wb') as out:
        pickle.dump(scaler, out)
    with (pipeline_dir / PCA_FILENAME).open('wb') as out:
        pickle.dump(pca, out)
    with (pipeline_dir / KMEANS_FILENAME).open('wb') as out:
        pickle.dump(kmeans, out)

    metadata = {
        'pipeline': 'pca_kmeans',
        'pca_components': args.pca_components,
        'kmeans_clusters': args.kmeans_clusters,
        'samples': sample_count,
        'created_at': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with (pipeline_dir / PIPELINE_META_FILENAME).open('w', encoding='utf-8') as out:
        json.dump(metadata, out, indent=2)


def train_model(X, y, params):
    dtrain = xgb.DMatrix(X, label=y)
    booster = xgb.train(params, dtrain, num_boost_round=300)
    return booster


def main():
    overall_start = time.time()
    parser = argparse.ArgumentParser(description="Train XGBoost beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/xgb_beam_predictor.json'))
    parser.add_argument('--max-depth', type=int, default=6)
    parser.add_argument('--eta', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set fraction (0.0-1.0)')
    parser.add_argument('--pca-components', type=int, default=DEFAULT_PCA_COMPONENTS, help='Number of PCA dimensions')
    parser.add_argument('--kmeans-clusters', type=int, default=DEFAULT_KMEANS_CLUSTERS, help='Number of clusters for KMeans')
    args = parser.parse_args()

    print("Loading dataset...")
    load_start = time.time()
    X, y = load_dataset(args.data)
    load_time = time.time() - load_start
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    print(f"\nSplitting data: {int((1-args.test_size)*100)}% train, {int(args.test_size*100)}% test")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=args.test_size, random_state=args.seed
    )
    print(f"Train: {X_train.shape[0]} samples | Test: {X_test.shape[0]} samples")

    print("\nFitting preprocessing pipeline (StandardScaler → PCA → KMeans)...")
    scaler, pca, kmeans, X_train_pca, train_clusters = _fit_preprocessing_pipeline(X_train, args)
    X_train_final = _stack_pipeline_features(X_train_pca, train_clusters)
    X_test_pca, test_clusters = _apply_pipeline(X_test, scaler, pca, kmeans)
    X_test_final = _stack_pipeline_features(X_test_pca, test_clusters)

    print("\nTraining XGBoost regression model on transformed features...")
    train_start = time.time()
    params = {
        'objective': 'reg:squarederror',
        'max_depth': args.max_depth,
        'eta': args.eta,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': args.seed,
    }
    booster = train_model(X_train_final, y_train, params)
    train_time = time.time() - train_start

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    try:
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    except ImportError:
        raise SystemExit("scikit-learn is required for regression metrics")

    eval_start = time.time()
    y_train_pred = booster.predict(xgb.DMatrix(X_train_final))
    y_test_pred = booster.predict(xgb.DMatrix(X_test_final))
    eval_time = time.time() - eval_start

    train_mse = mean_squared_error(y_train, y_train_pred)
    train_rmse = np.sqrt(train_mse)
    train_mae = mean_absolute_error(y_train, y_train_pred)
    train_r2 = r2_score(y_train, y_train_pred)

    test_mse = mean_squared_error(y_test, y_test_pred)
    test_rmse = np.sqrt(test_mse)
    test_mae = mean_absolute_error(y_test, y_test_pred)
    test_r2 = r2_score(y_test, y_test_pred)

    print("\nTRAINING SET METRICS:")
    print(f"  MSE: {train_mse:>10.6f}")
    print(f"  RMSE: {train_rmse:>10.6f}°")
    print(f"  MAE: {train_mae:>10.6f}°")
    print(f"  R² Score: {train_r2:>10.6f}")

    print("\nTEST SET METRICS:")
    print(f"  MSE: {test_mse:>10.6f}")
    print(f"  RMSE: {test_rmse:>10.6f}°")
    print(f"  MAE: {test_mae:>10.6f}°")
    print(f"  R² Score: {test_r2:>10.6f}")

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

    print("\nSaving preprocessing pipeline and XGBoost model...")
    output_dir = args.output.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    _save_pipeline_artifacts(output_dir, scaler, pca, kmeans, args, X.shape[0])
    booster.save_model(str(args.output))
    print(f"Saved XGBoost model to {args.output}")
    print(f"Saved pipeline artifacts to {output_dir}")

    overall_time = time.time() - overall_start
    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Model training: {train_time:.3f}s")
    print(f"  Model evaluation: {eval_time:.3f}s")
    print(f"  Total: {overall_time:.3f}s")


if __name__ == "__main__":
    main()
