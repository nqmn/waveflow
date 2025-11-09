"""Train an XGBoost beam predictor from generated dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np

try:
    import xgboost as xgb  # type: ignore
except ImportError as exc:  # pragma: no cover
    raise SystemExit("xgboost package is required. Install via `pip install xgboost`.") from exc


def load_dataset(path: Path):
    data = json.loads(path.read_text())
    X: List[List[float]] = []
    y: List[float] = []
    for sample in data:
        ap_pos = sample['ap_pos']
        ris_pos = sample['ris_pos']
        ue_pos = sample['ue_pos']
        vec_ap_ris = np.array(ris_pos) - np.array(ap_pos)
        vec_ris_ue = np.array(ue_pos) - np.array(ris_pos)
        features = [
            *ap_pos, *ris_pos, *ue_pos,
            float(np.linalg.norm(vec_ap_ris)),
            float(np.linalg.norm(vec_ris_ue)),
            sample['ap_power_dBm'],
            sample['ap_freq'],
            sample['ris_N'],
            sample['ris_bits'],
        ]
        X.append(features)
        y.append(sample['best_angle'])
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_model(X, y, params):
    dtrain = xgb.DMatrix(X, label=y)
    booster = xgb.train(params, dtrain, num_boost_round=300)
    return booster


def main():
    parser = argparse.ArgumentParser(description="Train XGBoost beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset JSON')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/xgb_beam_predictor.json'))
    parser.add_argument('--max-depth', type=int, default=6)
    parser.add_argument('--eta', type=float, default=0.1)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    X, y = load_dataset(args.data)
    params = {
        'objective': 'reg:squarederror',
        'max_depth': args.max_depth,
        'eta': args.eta,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': args.seed,
    }
    booster = train_model(X, y, params)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(args.output))
    print(f"Saved XGBoost model to {args.output}")


if __name__ == "__main__":
    main()
