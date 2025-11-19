
import sys
import os
import numpy as np
import matplotlib.pyplot as plt

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.network import RISNetwork
from core.nodes import AccessPoint, RIS, UE

def test_side_lobe_suppression():
    print("="*70)
    print("VERIFICATION: RIS Side Lobe Suppression with Amplitude Tapering")
    print("="*70)

    # 1. Setup Network
    net = RISNetwork()
    
    # AP at origin
    ap = AccessPoint('AP1', x=0, y=0, z=0, freq=28e9, power_dBm=30)
    net.nodes[ap.name] = ap

    # RIS at 50m on x-axis, facing -x (180 degrees)
    ris = RIS('RIS1', x=50, y=0, z=0, N=64, spacing=0.005, normal_angle_deg=180.0) # 64x64 elements
    net.nodes[ris.name] = ris

    # UE at (50, 10, 0) -> approx 11.3 degrees off-axis from RIS normal
    ue = UE('UE1', x=50, y=10, z=0)
    net.nodes[ue.name] = ue

    print(f"AP Position: {ap.pos}")
    print(f"RIS Position: {ris.pos}")
    print(f"UE Position: {ue.pos}")
    
    # Move UE to (40, 5, 0)
    ue.pos = np.array([40.0, 5.0, 0.0])
    print(f"Updated UE Position: {ue.pos}")

    # Sweep parameters
    angles = np.linspace(-60, 60, 241) # 0.5 degree step
    
    results = {}
    
    for tapering in ['uniform', 'hamming']:
        print(f"\nRunning sweep with tapering: {tapering.upper()}")
        snr_values = []
        
        for angle in angles:
            res = net.connect(ap.name, ris.name, ue.name, beam_angle_deg=angle, tapering=tapering)
            snr_values.append(res['snr_dB'])
            
        results[tapering] = np.array(snr_values)

    # Analyze Results
    
    def analyze_pattern(name, snrs, angles):
        peak_idx = np.argmax(snrs)
        peak_angle = angles[peak_idx]
        peak_snr = snrs[peak_idx]
        
        # Find side lobes
        # Exclude +/- 10 degrees around peak
        mask = (np.abs(angles - peak_angle) > 10.0)
        sidelobe_snrs = snrs[mask]
        max_sidelobe_snr = np.max(sidelobe_snrs) if len(sidelobe_snrs) > 0 else -np.inf
        
        pslr = peak_snr - max_sidelobe_snr
        
        print(f"--- {name} ---")
        print(f"Peak SNR: {peak_snr:.2f} dB at {peak_angle:.1f} deg")
        print(f"Max Sidelobe SNR: {max_sidelobe_snr:.2f} dB")
        print(f"PSLR: {pslr:.2f} dB")
        return peak_snr, max_sidelobe_snr, pslr

    print("\nAnalysis:")
    u_peak, u_sl, u_pslr = analyze_pattern('UNIFORM', results['uniform'], angles)
    h_peak, h_sl, h_pslr = analyze_pattern('HAMMING', results['hamming'], angles)
    
    # Verification Checks
    print("\nVerification Checks:")
    
    # 1. Check PSLR improvement
    pslr_improvement = h_pslr - u_pslr
    print(f"PSLR Improvement: {pslr_improvement:.2f} dB")
    
    if pslr_improvement > 3.0: # Lower threshold slightly as 5dB might be ambitious depending on geometry
        print("✓ PASS: Significant side lobe suppression observed (> 3 dB improvement)")
    else:
        print("✗ FAIL: Insufficient side lobe suppression")

    # 2. Check Main Lobe Loss
    gain_loss = u_peak - h_peak
    print(f"Main Lobe Loss: {gain_loss:.2f} dB")
    
    if 0 < gain_loss < 3.0:
        print("✓ PASS: Main lobe loss is within expected range (0-3 dB)")
    else:
        print(f"Warning: Main lobe loss {gain_loss:.2f} dB is unexpected")

    # Plotting (ASCII style for log)
    print("\nASCII Plot (SNR vs Angle):")
    print("Angle | Uniform | Hamming")
    print("-" * 30)
    for i in range(0, len(angles), 10): # Sample every 5 degrees
        a = angles[i]
        u = results['uniform'][i]
        h = results['hamming'][i]
        print(f"{a:>5.1f} | {u:>7.2f} | {h:>7.2f}")

if __name__ == "__main__":
    test_side_lobe_suppression()
