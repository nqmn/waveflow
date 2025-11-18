"""Train a fully connected neural network for beam angle prediction."""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
except ImportError as exc:
    raise SystemExit("PyTorch required. Install via `pip install torch`.") from exc

FEATURE_COLUMNS = ['snr_dB', 'rssi_dBm', 'd_ap_ris', 'aoa_sin', 'aoa_cos', 'el_sin', 'el_cos']
LABEL_COLUMN = 'best_angle'


class FCNet(nn.Module):
    """Simple fully connected network for angle prediction."""

    def __init__(self, input_dim: int = 5, hidden_dim: int = 128, output_dim: int = 1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu1 = nn.ReLU()
        self.dropout1 = nn.Dropout(0.2)

        self.fc2 = nn.Linear(hidden_dim, 64)
        self.relu2 = nn.ReLU()
        self.dropout2 = nn.Dropout(0.2)

        self.fc3 = nn.Linear(64, 32)
        self.relu3 = nn.ReLU()

        self.output = nn.Linear(32, output_dim)

    def forward(self, x):
        x = self.fc1(x)
        x = self.relu1(x)
        x = self.dropout1(x)

        x = self.fc2(x)
        x = self.relu2(x)
        x = self.dropout2(x)

        x = self.fc3(x)
        x = self.relu3(x)

        x = self.output(x)
        return x


def load_features(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Extract features and labels from CSV dataset."""
    rows_x: List[List[float]] = []
    rows_y: List[float] = []

    with path.open(newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            snr = float(row['snr_dB'])
            rssi = float(row['rssi_dBm'])
            d_ap_ris = float(row['d_ap_ris'])
            aoa_sin = float(row['aoa_sin'])
            aoa_cos = float(row['aoa_cos'])
            el_sin = float(row['el_sin'])
            el_cos = float(row['el_cos'])
            best_angle = float(row['best_angle'])

            rows_x.append([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos])
            rows_y.append(best_angle)

    return np.array(rows_x, dtype=np.float32), np.array(rows_y, dtype=np.float32).reshape(-1, 1)


def train_model(
    model: FCNet,
    train_loader: DataLoader,
    val_loader: DataLoader,
    num_epochs: int = 50,
    learning_rate: float = 1e-3,
    device: torch.device = None,
) -> Tuple[FCNet, List[float], List[float]]:
    """Train the FC network and return model with training history."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)

    train_losses = []
    val_losses = []

    for epoch in range(num_epochs):
        # Training
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * X_batch.size(0)

        train_loss /= len(train_loader.dataset)
        train_losses.append(train_loss)

        # Validation
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                val_loss += loss.item() * X_batch.size(0)

        val_loss /= len(val_loader.dataset)
        val_losses.append(val_loss)

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{num_epochs} | Train Loss: {train_loss:.6f} | Val Loss: {val_loss:.6f}")

    return model, train_losses, val_losses


def evaluate_model(model: FCNet, test_loader: DataLoader, device: torch.device = None):
    """Evaluate model on test set and return metrics."""
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model.eval()
    criterion = nn.MSELoss()

    predictions = []
    actuals = []
    total_loss = 0.0

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)

            total_loss += loss.item() * X_batch.size(0)
            predictions.extend(outputs.cpu().numpy().flatten())
            actuals.extend(y_batch.cpu().numpy().flatten())

    avg_loss = total_loss / len(test_loader.dataset)
    predictions = np.array(predictions)
    actuals = np.array(actuals)

    mae = np.mean(np.abs(predictions - actuals))
    rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
    max_error = np.max(np.abs(predictions - actuals))

    return {
        'mse': avg_loss,
        'mae': mae,
        'rmse': rmse,
        'max_error': max_error,
    }


def main():
    parser = argparse.ArgumentParser(description="Train fully connected neural network for beam angle prediction")
    parser.add_argument('--data', type=Path, required=True, help='Path to CSV beam dataset')
    parser.add_argument('--output', type=Path, default=Path('controller/beamsweeping/ml/models/fc_beam_predictor.pth'))
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size for training')
    parser.add_argument('--learning-rate', type=float, default=1e-3, help='Learning rate for Adam optimizer')
    parser.add_argument('--val-split', type=float, default=0.1, help='Validation split ratio')
    parser.add_argument('--test-split', type=float, default=0.1, help='Test split ratio')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    print(f"Using device: {device}")
    print("\nLoading dataset...")
    load_start = time.time()
    X, y = load_features(args.data)
    load_time = time.time() - load_start
    print(f"  {X.shape[0]} samples loaded")
    print(f"  Features: {FEATURE_COLUMNS}")
    print(f"  Shape: {X.shape}")

    # Train/val/test split
    n_samples = X.shape[0]
    n_test = int(n_samples * args.test_split)
    n_val = int((n_samples - n_test) * args.val_split)
    n_train = n_samples - n_val - n_test

    indices = np.random.permutation(n_samples)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:n_train + n_val]
    test_idx = indices[n_train + n_val:]

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    print(f"\nData split: Train {len(train_idx)} | Val {len(val_idx)} | Test {len(test_idx)}")

    # Create data loaders
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    test_dataset = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False)

    # Create and train model
    print("\nTraining FC Network...")
    train_start = time.time()
    model = FCNet(input_dim=7, hidden_dim=128, output_dim=1)
    model, train_losses, val_losses = train_model(
        model,
        train_loader,
        val_loader,
        num_epochs=args.epochs,
        learning_rate=args.learning_rate,
        device=device,
    )
    train_time = time.time() - train_start

    # Evaluate
    print("\nEvaluating on test set...")
    metrics = evaluate_model(model, test_loader, device=device)

    print("\nTest Metrics:")
    print(f"  MSE:  {metrics['mse']:.6f}")
    print(f"  MAE:  {metrics['mae']:.4f}°")
    print(f"  RMSE: {metrics['rmse']:.4f}°")
    print(f"  Max Error: {metrics['max_error']:.4f}°")

    # Save model
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), args.output)
    print(f"\nSaved FC model to {args.output}")

    print(f"\n⏱ Timing:")
    print(f"  Data loading: {load_time:.3f}s")
    print(f"  Training: {train_time:.3f}s")
    print(f"  Total: {load_time + train_time:.3f}s")


if __name__ == "__main__":
    main()
