"""Train a Random Forest beam predictor from generated dataset.

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
    from sklearn.ensemble import RandomForestRegressor
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
    parser = argparse.ArgumentParser(description="Train Random Forest beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/rf_beam_predictor.pkl'))
    parser.add_argument('--n-estimators', type=int, default=100, help='Number of trees')
    parser.add_argument('--max-depth', type=int, default=20, help='Maximum tree depth')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("Loading dataset...")
    X, y = load_dataset(args.data)
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    print("Training Random Forest model...")
    model = train_model(X, y, n_estimators=args.n_estimators, max_depth=args.max_depth, random_state=args.seed)

    print("Evaluating model...")
    train_score = model.score(X, y)
    print(f"Training R² score: {train_score:.4f}")

    print("Saving model...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as f:
        pickle.dump(model, f)
    print(f"Saved Random Forest model to {args.output}")


if __name__ == "__main__":
    main()
