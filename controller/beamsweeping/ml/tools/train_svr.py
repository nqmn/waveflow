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
    args = parser.parse_args()

    print("Loading dataset...")
    X, y = load_dataset(args.data)
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    print(f"Training SVR model with kernel={args.kernel}, C={args.C}, gamma={args.gamma}, epsilon={args.epsilon}...")
    model = train_model(X, y, kernel=args.kernel, C=args.C, gamma=args.gamma, epsilon=args.epsilon)

    print("Evaluating model...")
    X_scaled = model.scaler.transform(X)
    train_score = model.score(X_scaled, y)
    print(f"Training R² score: {train_score:.4f}")

    print("Saving model...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('wb') as f:
        pickle.dump(model, f)
    print(f"Saved SVR model to {args.output}")


if __name__ == "__main__":
    main()
