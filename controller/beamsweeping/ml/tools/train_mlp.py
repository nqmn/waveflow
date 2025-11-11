"""Train a neural network MLP beam predictor from generated dataset."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import List

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyTorch is required. Install via `pip install torch`") from exc


class MLPPredictor(nn.Module):
    """Multi-layer perceptron for beam angle prediction."""

    def __init__(self, input_size: int = 13, hidden_size: int = 128):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, x):
        return self.network(x)


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
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train_model(X, y, epochs: int = 100, batch_size: int = 32, learning_rate: float = 0.001):
    # Normalize input features
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_normalized = (X - X_mean) / (X_std + 1e-8)

    # Normalize labels
    y_mean = y.mean()
    y_std = y.std()
    y_normalized = (y - y_mean) / (y_std + 1e-8)

    # Create dataset and dataloader
    X_tensor = torch.from_numpy(X_normalized)
    y_tensor = torch.from_numpy(y_normalized).unsqueeze(1)
    dataset = TensorDataset(X_tensor, y_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    # Initialize model and training components
    model = MLPPredictor(input_size=X.shape[1], hidden_size=128)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()

    # Training loop
    for epoch in range(epochs):
        epoch_loss = 0.0
        for X_batch, y_batch in dataloader:
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = criterion(predictions, y_batch)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            avg_loss = epoch_loss / len(dataloader)
            print(f"Epoch {epoch + 1}/{epochs}, Loss: {avg_loss:.6f}")

    # Store normalization parameters for inference
    model.X_mean = X_mean
    model.X_std = X_std
    model.y_mean = y_mean
    model.y_std = y_std

    return model


def save_model(model, path: Path):
    """Save model weights and normalization parameters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        'model_state_dict': model.state_dict(),
        'X_mean': model.X_mean,
        'X_std': model.X_std,
        'y_mean': model.y_mean,
        'y_std': model.y_std,
        'input_size': model.network[0].in_features,
    }
    torch.save(checkpoint, str(path))


def main():
    parser = argparse.ArgumentParser(description="Train MLP beam predictor")
    parser.add_argument('--data', type=Path, required=True, help='Path to dataset CSV')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/mlp_beam_predictor.pth'))
    parser.add_argument('--epochs', type=int, default=100, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for training')
    parser.add_argument('--learning-rate', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--hidden-size', type=int, default=128, help='Hidden layer size')
    args = parser.parse_args()

    print("Loading dataset...")
    X, y = load_dataset(args.data)
    print(f"Dataset loaded: {X.shape[0]} samples, {X.shape[1]} features")

    print("Training MLP model...")
    model = train_model(X, y, epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.learning_rate)

    print("Saving model...")
    save_model(model, args.output)
    print(f"Saved MLP model to {args.output}")


if __name__ == "__main__":
    main()
