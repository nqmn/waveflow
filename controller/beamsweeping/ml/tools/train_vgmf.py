"""Train a Variational Autoencoder + Gaussian Mixture Model for beam prediction."""

from __future__ import annotations

import argparse
import csv
import math
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

try:
    from sklearn.mixture import GaussianMixture
except ImportError as exc:  # pragma: no cover
    raise SystemExit("scikit-learn required (GaussianMixture). Install via `pip install scikit-learn`.") from exc

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
except ImportError as exc:  # pragma: no cover
    raise SystemExit("torch required. Install via `pip install torch`.") from exc

try:
    import joblib
except ImportError as exc:  # pragma: no cover
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
    """Extract latent vectors (mu) from VAE encoder for deterministic representation."""
    vae.eval()
    latent_vectors = []

    with torch.no_grad():
        for i in range(0, len(data_tensor), batch_size):
            batch = data_tensor[i:i+batch_size].to(device)
            mu, _ = vae.encode(batch)
            latent_vectors.append(mu.cpu().numpy())

    return np.vstack(latent_vectors)


def load_features(path: Path) -> Tuple[np.ndarray, np.ndarray]:
    """Extract [snr, rssi, d_ap_ris, aoa_sin, aoa_cos, el_sin, el_cos, dx, dy, dz] and best_angle_sin, best_angle_cos from CSV."""
    feature_rows: List[List[float]] = []
    angle_sin_rows: List[float] = []
    angle_cos_rows: List[float] = []

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
            angle_rad = math.radians(angle_deg)
            angle_sin_rows.append(math.sin(angle_rad))
            angle_cos_rows.append(math.cos(angle_rad))

    angle_rows = np.column_stack([np.array(angle_sin_rows, dtype=float), np.array(angle_cos_rows, dtype=float)])
    return np.array(feature_rows, dtype=float), angle_rows


def evaluate_vgmf_predictions(vae, gmm, X_features: np.ndarray, y_angles: np.ndarray,
                              device='cpu', batch_size=32) -> dict:
    """Evaluate VGMF by computing MAE on angle predictions using deterministic mu.

    y_angles is shape (N, 2) containing [sin, cos] representations.
    Converts back to degrees for error computation.
    """
    vae.eval()
    predictions_sin = []
    predictions_cos = []

    with torch.no_grad():
        for i in range(0, len(X_features), batch_size):
            batch_X = torch.tensor(X_features[i:i+batch_size], dtype=torch.float32, device=device)
            mu, _ = vae.encode(batch_X)
            z_np = mu.cpu().numpy()

            for z_sample in z_np:
                angle_grid = np.linspace(0.0, 360.0, 360)
                angles_rad = np.radians(angle_grid)
                angle_sin = np.sin(angles_rad)
                angle_cos = np.cos(angles_rad)

                z_matrix = np.repeat(z_sample[np.newaxis, :], len(angle_grid), axis=0)
                samples = np.hstack([z_matrix, angle_sin.reshape(-1, 1), angle_cos.reshape(-1, 1)])

                log_likelihoods = gmm.score_samples(samples)
                log_likelihoods -= np.max(log_likelihoods)
                posterior = np.exp(log_likelihoods)
                posterior /= np.sum(posterior)

                best_idx = np.argmax(posterior)
                predictions_sin.append(angle_sin[best_idx])
                predictions_cos.append(angle_cos[best_idx])

            if (i + batch_size) % 1000 == 0 or (i + batch_size) >= len(X_features):
                print(f"    Evaluated {min(i + batch_size, len(X_features))}/{len(X_features)} samples...")

    predictions_sin = np.array(predictions_sin)
    predictions_cos = np.array(predictions_cos)

    predicted_angles = np.degrees(np.arctan2(predictions_sin, predictions_cos)) % 360.0
    true_angles = np.degrees(np.arctan2(y_angles[:, 0], y_angles[:, 1])) % 360.0

    angle_diff = np.abs(predicted_angles - true_angles)
    angle_diff = np.minimum(angle_diff, 360.0 - angle_diff)

    mae = np.mean(angle_diff)
    rmse = np.sqrt(np.mean(angle_diff ** 2))
    max_error = np.max(angle_diff)

    return {
        'mae': float(mae),
        'rmse': float(rmse),
        'max_error': float(max_error),
        'predictions': predicted_angles,
    }


def main():
    parser = argparse.ArgumentParser(description="Train Variational Autoencoder + GMM for beam prediction")
    parser.add_argument('--data', type=Path, required=True, help='Path to CSV beam dataset')
    parser.add_argument('--vae-output', type=Path, default=Path('controller/beamsweeping/ml/models/vgmf_vae.pth'),
                       help='Output path for VAE model')
    parser.add_argument('--gmm-output', type=Path, default=Path('controller/beamsweeping/ml/models/vgmf_gmm.pkl'),
                       help='Output path for GMM model')
    parser.add_argument('--latent-dim', type=int, default=6, help='VAE latent dimension')
    parser.add_argument('--hidden-dim', type=int, default=64, help='VAE hidden dimension')
    parser.add_argument('--vae-epochs', type=int, default=100, help='Number of VAE training epochs')
    parser.add_argument('--vae-batch-size', type=int, default=32, help='VAE batch size')
    parser.add_argument('--vae-lr', type=float, default=1e-3, help='VAE learning rate')
    parser.add_argument('--vae-beta', type=float, default=0.5, help='VAE KL divergence weight')
    parser.add_argument('--gmm-components', type=int, default=12, help='Number of GMM components')
    parser.add_argument('--gmm-covariance', type=str, default='full',
                       choices=['full', 'tied', 'diag', 'spherical'], help='GMM covariance type')
    parser.add_argument('--gmm-n-init', type=int, default=10, help='GMM number of initializations')
    parser.add_argument('--val-split', type=float, default=0.2, help='Validation split ratio')
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

    val_split_idx = int(len(X_features) * (1 - args.val_split))
    indices = np.random.permutation(len(X_features))
    train_indices = indices[:val_split_idx]
    val_indices = indices[val_split_idx:]

    X_train = X_features[train_indices]
    y_train = y_angles[train_indices]
    X_val = X_features[val_indices]
    y_val = y_angles[val_indices]

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
    latent_time = time.time() - latent_start
    print(f"  Extracted {Z_train.shape[0]} latent vectors (dim: {Z_train.shape[1]})")

    print("\nFitting Gaussian Mixture Model on latent space...")
    gmm_start = time.time()
    gmm_data = np.hstack([Z_train, y_train])

    gmm = GaussianMixture(
        n_components=args.gmm_components,
        covariance_type=args.gmm_covariance,
        n_init=args.gmm_n_init,
        random_state=args.seed,
    )
    gmm.fit(gmm_data)
    gmm_time = time.time() - gmm_start

    print("\nGMM Evaluation:")
    log_likelihood = float(gmm.score(gmm_data))
    bic = float(gmm.bic(gmm_data))
    aic = float(gmm.aic(gmm_data))
    print(f"  Log-likelihood: {log_likelihood:.6f}")
    print(f"  BIC: {bic:.2f}")
    print(f"  AIC: {aic:.2f}")

    print("\nComputing angle prediction metrics on training set...")
    eval_start = time.time()
    pred_metrics = evaluate_vgmf_predictions(vae, gmm, X_train, y_train, device=device)
    eval_time = time.time() - eval_start

    print("\nAngle Prediction Metrics (Training Set):")
    print(f"  MAE:       {pred_metrics['mae']:.4f}°")
    print(f"  RMSE:      {pred_metrics['rmse']:.4f}°")
    print(f"  Max Error: {pred_metrics['max_error']:.4f}°")

    args.vae_output.parent.mkdir(parents=True, exist_ok=True)
    args.gmm_output.parent.mkdir(parents=True, exist_ok=True)

    vae_checkpoint = {
        "vae_state_dict": vae.state_dict(),
        "hyperparams": {
            "input_dim": 10,
            "latent_dim": args.latent_dim,
            "hidden_dim": args.hidden_dim,
        }
    }
    torch.save(vae_checkpoint, args.vae_output)
    print(f"\nSaved VAE model to {args.vae_output}")

    joblib.dump(gmm, args.gmm_output)
    print(f"Saved GMM model to {args.gmm_output}")

    print(f"\nTiming Summary:")
    print(f"  Data loading:    {load_time:.3f}s")
    print(f"  VAE training:    {vae_time:.3f}s")
    print(f"  Latent vector extraction: {latent_time:.3f}s")
    print(f"  GMM training:    {gmm_time:.3f}s")
    print(f"  Evaluation:      {eval_time:.3f}s")
    print(f"  Total:           {load_time + vae_time + latent_time + gmm_time + eval_time:.3f}s")


if __name__ == "__main__":
    main()
