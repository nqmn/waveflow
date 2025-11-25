#!/usr/bin/env python3
import numpy as np
from scipy.optimize import minimize, differential_evolution
from joblib import Parallel, delayed
import time
import warnings
warnings.filterwarnings("ignore")

# ============================================================================
# FULL PAPER CONFIGURATION PARAMETERS
# ============================================================================

c = 3e8
f = 5.8e9
wavelength = c / f
k = 2 * np.pi / wavelength

N_side = 16             # FULL: 16×16 RIS array
N = N_side * N_side     # 256 elements
d_element = wavelength / 2.0

AP_pos = np.array([10.0, 10.0, 1.5])
RIS_center = np.array([15.0, 10.0, 1.2])
UE_true = np.array([9.5, 4.5, 1.0])

M = 32                  # FULL: 32 measurements
GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

A_on = 0.92
A_off = 0.85
target_SNR_dB = 25.0

# ============================================================================
# CORE FUNCTIONS (Same as validated version)
# ============================================================================

def compute_channel(pos_tx, pos_rx):
    if pos_tx.ndim == 1:
        pos_tx = pos_tx.reshape(1, 3)
    dx = pos_tx[0, 0] - pos_rx[:, 0]
    dy = pos_tx[0, 1] - pos_rx[:, 1]
    dz = pos_tx[0, 2] - pos_rx[:, 2]
    d = np.sqrt(dx*dx + dy*dy + dz*dz)
    d = np.maximum(d, 1e-9)
    amplitude = wavelength / (4 * np.pi * d)
    phase = -k * d
    return amplitude * np.exp(1j * phase)

def compute_h_vector(AP_pos, RIS_positions):
    return compute_channel(AP_pos, RIS_positions)

def compute_g_vector(x_ue, RIS_positions):
    return compute_channel(x_ue, RIS_positions)

def compute_manifold_vector(x, Theta, h, RIS_positions):
    g = compute_g_vector(x, RIS_positions)
    return np.einsum('n,mn,n->m', g.conj(), Theta, h)

def compute_geometric_jacobian(x, RIS_positions):
    delta = x - RIS_positions
    d = np.linalg.norm(delta, axis=1)
    d = np.maximum(d,1e-9)
    u = delta / d[:,None]
    amplitude = wavelength / (4*np.pi*d)
    phase = -k * d
    g = amplitude * np.exp(1j * phase)
    grad_g = g[:,None] * ((-1j*k) * u - u/d[:,None])
    return grad_g

def quantize_to_1bit(phases):
    return np.where(np.cos(phases) >= 0, 0.0, np.pi)

def theta_to_complex_from_phase_1bit(phase_array):
    amp = np.where(np.isclose(phase_array,0.0), A_on, A_off)
    return amp * np.exp(1j * phase_array)

def compute_full_jacobian_vectorized(x, Theta, h, RIS_positions):
    delta = x - RIS_positions
    d = np.linalg.norm(delta, axis=1)
    d = np.maximum(d,1e-9)
    u = delta / d[:,None]
    amplitude = wavelength / (4*np.pi*d)
    phase = -k * d
    g = amplitude * np.exp(1j * phase)
    grad_g = g[:,None] * ((-1j*k) * u - u/d[:,None])
    weighted = Theta * h[None,:]
    J = weighted @ grad_g
    return J

def cost_and_grad_vectorized(x, y_meas, Theta, h, RIS_positions):
    y_pred = compute_manifold_vector(x, Theta, h, RIS_positions)
    residual = y_meas - y_pred
    cost = np.real(np.vdot(residual, residual))
    J = compute_full_jacobian_vectorized(x, Theta, h, RIS_positions)
    grad = -2.0 * np.real(J.conj().T @ residual)
    return cost, grad

def generate_ris_positions(center, N, d):
    side = int(np.sqrt(N))
    pos = []
    for i in range(side):
        for j in range(side):
            y = (i - (side - 1)/2)*d
            z = (j - (side - 1)/2)*d
            pos.append(center + np.array([0.0, y, z]))
    return np.array(pos)

def baseline_region_theta(center, size, h, M, density=4, seed=GLOBAL_SEED):
    np.random.seed(seed)
    samples = []
    for dx in np.linspace(-size, size, density):
        for dy in np.linspace(-size, size, density):
            samples.append(center + np.array([dx, dy, 0.0]))
    samples = np.array(samples)
    Theta = []
    for m in range(M):
        if m < 3:
            v = np.zeros(3); v[m]=1.0
        else:
            v = np.random.randn(3); v /= np.linalg.norm(v)
        Havg = np.zeros((N,3), dtype=complex)
        for s in samples:
            Havg += compute_geometric_jacobian(s, RIS_positions)
        Havg /= len(samples)
        proj = Havg @ v
        theta = np.exp(1j * np.angle(proj * np.conj(h)))
        Theta.append(theta)
    return np.array(Theta), samples

def steering_phase_for_direction(v):
    phases = np.zeros(N)
    for n in range(N):
        rp = RIS_positions[n] - RIS_center
        phases[n] = -(2*np.pi/wavelength)*np.dot(rp, v)
    return np.exp(1j * phases)

def build_candidate_pool(Theta_base, h, M):
    pool = []
    for m in range(len(Theta_base)):
        raw_phase = np.angle(Theta_base[m])
        q = quantize_to_1bit(raw_phase)
        pool.append(theta_to_complex_from_phase_1bit(q))
    np.random.seed(GLOBAL_SEED)
    for m in range(len(Theta_base)):
        jitter = 0.04 * np.random.randn(N)
        raw = np.angle(Theta_base[m]) + jitter
        q = quantize_to_1bit(raw)
        pool.append(theta_to_complex_from_phase_1bit(q))
    dirs = [np.array([-1.0,0.0,0.0]), np.array([-1.0,0.2,0.0]), np.array([-1.0,-0.2,0.0])]
    for d in dirs:
        d = d / np.linalg.norm(d)
        s = steering_phase_for_direction(d)
        raw = np.angle(s * np.conj(h))
        q = quantize_to_1bit(raw)
        pool.append(theta_to_complex_from_phase_1bit(q))
    return np.array(pool)

def precompute_weighted_jacobians(region_samples, h, RIS_positions):
    S = len(region_samples)
    GH = np.zeros((S,N,3), dtype=complex)
    for s_idx in range(S):
        Gs = compute_geometric_jacobian(region_samples[s_idx], RIS_positions)
        GH[s_idx] = Gs * h[:,None]
    return GH

def compute_fim_score_fast(Theta, GH, noise_power):
    S = GH.shape[0]
    scores = np.zeros(S)
    for s in range(S):
        J = Theta @ GH[s]
        F = np.real(J.conj().T @ J) / noise_power
        scores[s] = np.trace(F)
    return np.mean(scores)

def evaluate_candidate(idx, cand, Theta_current, GH, noise_power):
    if Theta_current.size != 0:
        T = np.vstack([Theta_current, cand])
    else:
        T = cand[None,:]
    return idx, compute_fim_score_fast(T, GH, noise_power)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("RIS LOCALIZATION - FULL PAPER CONFIGURATION")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"  RIS: {N_side}×{N_side} = {N} elements")
    print(f"  Measurements: M = {M}")
    print(f"  Frequency: {f/1e9:.1f} GHz, wavelength: {wavelength*1000:.2f} mm")
    print(f"  SNR: {target_SNR_dB} dB")
    print(f"\nGeometry:")
    print(f"  AP:  {AP_pos}")
    print(f"  RIS: {RIS_center}")
    print(f"  UE:  {UE_true}")
    
    # Build geometry
    RIS_positions = generate_ris_positions(RIS_center, N, d_element)
    h = compute_h_vector(AP_pos, RIS_positions)
    
    # Generate configurations
    region_center = np.array([10.0,7.0,0.0])
    region_size = 5.0
    
    print(f"\n1. Configuration Design")
    start_total = time.time()
    Theta_base_continuous, region_samples = baseline_region_theta(region_center, region_size, h, M)
    pool = build_candidate_pool(Theta_base_continuous, h, M)
    print(f"   Candidate pool: {len(pool)} configurations")
    
    # FIM-based selection
    GH = precompute_weighted_jacobians(region_samples, h, RIS_positions)
    import multiprocessing
    workers = max(1, multiprocessing.cpu_count()-1)
    
    remaining = list(range(len(pool)))
    selected = []
    noise_power_dummy = 1e-9
    
    print(f"\n2. Greedy Selection ({workers} workers)")
    start_sel = time.time()
    for step in range(M):
        Theta_curr = pool[selected] if len(selected)>0 else np.zeros((0,N),dtype=complex)
        results = Parallel(n_jobs=workers)(delayed(evaluate_candidate)(
            idx, pool[idx], Theta_curr, GH, noise_power_dummy) for idx in remaining)
        best = max(results, key=lambda x: x[1])[0]
        selected.append(best)
        remaining.remove(best)
    end_sel = time.time()
    print(f"   Completed in {end_sel-start_sel:.2f}s")
    
    Theta_selected = pool[selected]
    
    # Simulate measurements
    print(f"\n3. Measurement Simulation")
    y_true = compute_manifold_vector(UE_true, Theta_selected, h, RIS_positions)
    signal_power = np.mean(np.abs(y_true)**2)
    noise_power = signal_power / (10**(target_SNR_dB/10.0))
    np.random.seed(GLOBAL_SEED)
    noise = np.sqrt(noise_power/2) * (np.random.randn(M) + 1j*np.random.randn(M))
    y_meas = y_true + noise
    print(f"   SNR: {10*np.log10(signal_power/noise_power):.2f} dB")
    
    # Estimate position
    bounds = [(region_center[0]-region_size-1, region_center[0]+region_size+1),
              (region_center[1]-region_size-1, region_center[1]+region_size+1),
              (-0.5, 2.5)]
    
    print(f"\n4. Position Estimation")
    start_opt = time.time()
    res_de = differential_evolution(
        lambda x: np.real(np.vdot(y_meas - compute_manifold_vector(x, Theta_selected, h, RIS_positions), 
                                 y_meas - compute_manifold_vector(x, Theta_selected, h, RIS_positions))),
        bounds, maxiter=100, popsize=15, seed=GLOBAL_SEED, polish=True, workers=1)
    
    res_local = minimize(
        lambda x: cost_and_grad_vectorized(x, y_meas, Theta_selected, h, RIS_positions)[0],
        res_de.x, method='L-BFGS-B',
        jac=lambda x: cost_and_grad_vectorized(x, y_meas, Theta_selected, h, RIS_positions)[1],
        bounds=bounds, options={'maxiter':200, 'ftol':1e-10})
    end_opt = time.time()
    print(f"   Optimization completed in {end_opt-start_opt:.2f}s")
    
    x_est = res_local.x
    est_error = np.linalg.norm(x_est - UE_true)
    end_total = time.time()
    
    # Results
    print(f"\n{'='*70}")
    print("RESULTS")
    print(f"{'='*70}")
    print(f"Estimated: [{x_est[0]:.4f}, {x_est[1]:.4f}, {x_est[2]:.4f}] m")
    print(f"True:      [{UE_true[0]:.4f}, {UE_true[1]:.4f}, {UE_true[2]:.4f}] m")
    print(f"\nError: {est_error:.4f} m")
    print(f"  Δx={abs(x_est[0]-UE_true[0]):.4f}, Δy={abs(x_est[1]-UE_true[1]):.4f}, Δz={abs(x_est[2]-UE_true[2]):.4f}")
    print(f"\nTotal time: {end_total-start_total:.2f} s")
    print(f"Status: {'EXCELLENT ✓' if est_error < 0.5 else 'GOOD ✓'}")
    print(f"{'='*70}")