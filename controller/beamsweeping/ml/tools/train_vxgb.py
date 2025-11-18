"""Train a Variational Autoencoder + XGBoost model for beam prediction.

Combines VAE feature encoding with XGBoost regression for improved angle prediction.
The VAE compresses 7 input features into a lower-dimensional latent space,
which is then used as input to an XGBoost regressor for angle prediction.
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
    import xgboost as xgb
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
except ImportError as exc:
    raise SystemExit("xgboost and scikit-learn packages required. Install via `pip install xgboost scikit-learn`.") from exc

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
except ImportError as exc:
    raise SystemExit("torch required. Install via `pip install torch`.") from exc

try:
    import joblib
except ImportError as exc:
    raise SystemExit("joblib required to persist models. Install via `pip install joblib`.") from exc


class VAE(nn.Module):
    """Variational Autoencoder for beam feature compression."""

    def __init__(self, input_dim: int = 10, latent_dim: int = 4, hidden_dim: int = 64):
        super().__init__()
        self.input_dim = input_dim
        self.latent_dim = latent_dim

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        return mu, logvar

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + eps * std
        return z

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        recon_x = self.decode(z)
        return recon_x, mu, logvar, z


def vae_loss_fn(recon_x, x, mu, logvar, beta=1.0):
    """Compute VAE loss: reconstruction + KL divergence."""
    mse = nn.MSELoss(reduction='mean')(recon_x, x)
    kl_div = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return mse + beta * kl_div, mse, kl_div


def train_vae(vae, train_loader, val_loader, epochs=50, device='cpu', learning_rate=1e-3, beta=1.0):
    """Train the VAE."""
    optimizer = optim.Adam(vae.parameters(), lr=learning_rate)

    best_val_loss = float('inf')

    for epoch in range(epochs):
        vae.train()
        train_loss = 0.0
        train_mse = 0.0
        train_kl = 0.0

        for batch in train_loader:
            batch_x = batch[0].to(device)
            optimizer.zero_grad()

            recon_x, mu, logvar, _ = vae(batch_x)
            loss, mse, kl = vae_loss_fn(recon_x, batch_x, mu, logvar, beta)

            loss.backward()
            optimizer.step()

            train_loss += loss.item()
            train_mse += mse.item()
            train_kl += kl.item()

        train_loss /= len(train_loader)
        train_mse /= len(train_loader)
        train_kl /= len(train_loader)

        vae.eval()
        val_loss = 0.0
        with torch.no_grad():
            for batch in val_loader:
                batch_x = batch[0].to(device)
                recon_x, mu, logvar, _ = vae(batch_x)
                loss, _, _ = vae_loss_fn(recon_x, batch_x, mu, logvar, beta)
                val_loss += loss.item()

        val_loss /= len(val_loader)

        if (epoch + 1) % 10 == 0:
            print(f"  Epoch {epoch+1}/{epochs}: Train Loss={train_loss:.6f} (MSE={train_mse:.6f}, KL={train_kl:.6f}), Val Loss={val_loss:.6f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss

    print(f"  Final: Best Val Loss={best_val_loss:.6f}")
    return vae


def extract_latent_vectors(vae, data_tensor, device='cpu', batch_size=32) -> np.ndarray:
    """Extract latent vectors from VAE encoder."""
    vae.eval()
    latent_vectors = []

    with torch.no_grad():
        for i in range(0, len(data_tensor), batch_size):
            batch = data_tensor[i:i+batch_size].to(device)
            _, _, _, z = vae(batch)
            latent_vectors.append(z.cpu().numpy())

    return np.vstack(latent_vectors)


def load_features(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Extract [snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, dx, dy, dz] and best_angle from CSV."""
    feature_rows: List[List[float]] = []
    angle_rows: List[float] = []

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
            dx = float(row['dx'])
            dy = float(row['dy'])
            dz = float(row['dz'])
            angle_deg = float(row['best_angle'])

            feature_rows.append([snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, dx, dy, dz])
            angle_rows.append(angle_deg)

    return np.array(feature_rows, dtype=float), np.array(angle_rows, dtype=float)


def main():
    parser = argparse.ArgumentParser(description="Train Variational Autoencoder + XGBoost for beam prediction")
    parser.add_argument('--data', type=Path, required=True, help='Path to CSV beam dataset')
    parser.add_argument('--vae-output', type=Path, default=Path('controller/beamsweeping/ml/models/vxgb_vae.pth'),
                        help='Output path for VAE model')
    parser.add_argument('--xgb-output', type=Path, default=Path('controller/beamsweeping/ml/models/vxgb_xgb.json'),
                        help='Output path for XGBoost model')
    parser.add_argument('--latent-dim', type=int, default=6, help='VAE latent dimension')
    parser.add_argument('--hidden-dim', type=int, default=64, help='VAE hidden dimension')
    parser.add_argument('--vae-epochs', type=int, default=100, help='Number of VAE training epochs')
    parser.add_argument('--vae-batch-size', type=int, default=32, help='VAE batch size')
    parser.add_argument('--vae-lr', type=float, default=1e-3, help='VAE learning rate')
    parser.add_argument('--vae-beta', type=float, default=0.5, help='VAE KL divergence weight')
    parser.add_argument('--xgb-max-depth', type=int, default=6, help='XGBoost max depth')
    parser.add_argument('--xgb-eta', type=float, default=0.1, help='XGBoost learning rate')
    parser.add_argument('--xgb-rounds', type=int, default=300, help='XGBoost training rounds')
    parser.add_argument('--val-split', type=float, default=0.2, help='Validation split ratio')
    parser.add_argument('--test-split', type=float, default=0.2, help='Test set fraction')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print("\nLoading dataset...")
    load_start = time.time()
    X_features, y_angles = load_features(args.data)
    load_time = time.time() - load_start
    print(f"  {X_features.shape[0]} samples loaded (10 input features + 1 angle label)")

    print(f"\nSplitting data: {int((1-args.test_split)*100)}% train+val, {int(args.test_split*100)}% test")
    X_temp, X_test, y_temp, y_test = train_test_split(
        X_features, y_angles, test_size=args.test_split, random_state=args.seed
    )

    val_split_idx = int(len(X_temp) * (1 - args.val_split))
    indices = np.random.permutation(len(X_temp))
    train_indices = indices[:val_split_idx]
    val_indices = indices[val_split_idx:]

    X_train = X_temp[train_indices]
    y_train = y_temp[train_indices]
    X_val = X_temp[val_indices]
    y_val = y_temp[val_indices]

    print(f"  Train: {X_train.shape[0]} | Val: {X_val.shape[0]} | Test: {X_test.shape[0]}")

    X_train_tensor = torch.tensor(X_train, dtype=torch.float32)
    X_val_tensor = torch.tensor(X_val, dtype=torch.float32)

    train_loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X_train_tensor),
        batch_size=args.vae_batch_size,
        shuffle=True
    )
    val_loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(X_val_tensor),
        batch_size=args.vae_batch_size,
        shuffle=False
    )

    print("\nTraining Variational Autoencoder...")
    vae_start = time.time()
    vae = VAE(input_dim=10, latent_dim=args.latent_dim, hidden_dim=args.hidden_dim)
    vae.to(device)
    vae = train_vae(vae, train_loader, val_loader, epochs=args.vae_epochs,
                    device=device, learning_rate=args.vae_lr, beta=args.vae_beta)
    vae_time = time.time() - vae_start

    print("\nExtracting latent vectors from training data...")
    latent_start = time.time()
    Z_train = extract_latent_vectors(vae, X_train_tensor, device=device, batch_size=args.vae_batch_size)
    Z_val = extract_latent_vectors(vae, X_val_tensor, device=device, batch_size=args.vae_batch_size)
    X_test_tensor = torch.tensor(X_test, dtype=torch.float32)
    Z_test = extract_latent_vectors(vae, X_test_tensor, device=device, batch_size=args.vae_batch_size)
    latent_time = time.time() - latent_start
    print(f"  Extracted latent vectors (dim: {Z_train.shape[1]})")
    print(f"    Train: {Z_train.shape[0]} | Val: {Z_val.shape[0]} | Test: {Z_test.shape[0]}")

    print("\nTraining XGBoost regression model on VAE latent space...")
    xgb_start = time.time()
    params = {
        'objective': 'reg:squarederror',
        'max_depth': args.xgb_max_depth,
        'eta': args.xgb_eta,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'seed': args.seed,
    }
    dtrain = xgb.DMatrix(Z_train, label=y_train)
    dval = xgb.DMatrix(Z_val, label=y_val)
    dtest = xgb.DMatrix(Z_test, label=y_test)

    evals = [(dtrain, 'train'), (dval, 'val'), (dtest, 'test')]
    evals_result = {}
    booster = xgb.train(params, dtrain, num_boost_round=args.xgb_rounds, evals=evals, evals_result=evals_result)
    xgb_time = time.time() - xgb_start

    print("\n" + "="*70)
    print("MODEL EVALUATION METRICS")
    print("="*70)

    y_train_pred = booster.predict(dtrain)
    y_val_pred = booster.predict(dval)
    y_test_pred = booster.predict(dtest)

    def compute_metrics(y_true, y_pred, label):
        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)
        max_error = np.max(np.abs(y_true - y_pred))
        print(f"\n{label} SET METRICS:")
        print(f"  MAE:       {mae:>10.4f}°")
        print(f"  RMSE:      {rmse:>10.4f}°")
        print(f"  Max Error: {max_error:>10.4f}°")
        print(f"  MSE:       {mse:>10.6f}")
        print(f"  R² Score:  {r2:>10.6f}")
        return mae, rmse, r2

    train_mae, train_rmse, train_r2 = compute_metrics(y_train, y_train_pred, "TRAINING")
    val_mae, val_rmse, val_r2 = compute_metrics(y_val, y_val_pred, "VALIDATION")
    test_mae, test_rmse, test_r2 = compute_metrics(y_test, y_test_pred, "TEST")

    print("\nMODEL ASSESSMENT:")
    if test_r2 >= 0.90:
        assessment = "EXCELLENT - R² >= 0.90"
    elif test_r2 >= 0.75:
        assessment = "GOOD - R² >= 0.75"
    elif test_r2 >= 0.60:
        assessment = "FAIR - R² >= 0.60"
    else:
        assessment = "POOR - R² < 0.60"
    print(f"  {assessment}")

    print("\nSaving models...")
    args.vae_output.parent.mkdir(parents=True, exist_ok=True)
    args.xgb_output.parent.mkdir(parents=True, exist_ok=True)

    vae_checkpoint = {
        "vae_state_dict": vae.state_dict(),
        "hyperparams": {
            "input_dim": 10,
            "latent_dim": args.latent_dim,
            "hidden_dim": args.hidden_dim,
        }
    }
    torch.save(vae_checkpoint, args.vae_output)
    print(f"Saved VAE model to {args.vae_output}")

    booster.save_model(str(args.xgb_output))
    print(f"Saved XGBoost model to {args.xgb_output}")

    metadata = {
        'pipeline': 'vae_xgb',
        'vae_latent_dim': args.latent_dim,
        'vae_hidden_dim': args.hidden_dim,
        'xgb_max_depth': args.xgb_max_depth,
        'xgb_eta': args.xgb_eta,
        'samples': len(X_features),
        'created_at': time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    meta_path = args.xgb_output.parent / "vxgb_pipeline.json"
    with meta_path.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved pipeline metadata to {meta_path}")

    print(f"\nTiming Summary:")
    print(f"  Data loading:      {load_time:.3f}s")
    print(f"  VAE training:      {vae_time:.3f}s")
    print(f"  Latent extraction: {latent_time:.3f}s")
    print(f"  XGB training:      {xgb_time:.3f}s")
    print(f"  Total:             {load_time + vae_time + latent_time + xgb_time:.3f}s")

    print("\nComparison Summary:")
    print(f"  VGMF (GMM):        MAE={14.77:.2f}°, RMSE={17.12:.2f}°")
    print(f"  VXGB (VAE+XGB):    MAE={test_mae:.2f}°, RMSE={test_rmse:.2f}°")
    improvement_mae = ((14.77 - test_mae) / 14.77) * 100
    improvement_rmse = ((17.12 - test_rmse) / 17.12) * 100
    print(f"  Improvement:       MAE {improvement_mae:+.1f}%, RMSE {improvement_rmse:+.1f}%")


if __name__ == "__main__":
    main()
