"""
Plot the beam pattern to see if it's correct
"""

import numpy as np
import json
from core.network import RISNetwork


def main():
    print("="*80)
    print("BEAM PATTERN ANALYSIS")
    print("="*80)

    # Load topology
    with open('topo_44', 'r') as f:
        topo = json.load(f)

    net = RISNetwork()
    for node in topo['nodes']:
        if node['type'] == 'AccessPoint':
            net.add_ap(node['name'], node['pos'][0], node['pos'][1], node['pos'][2],
                      power_dBm=node['power_dBm'], freq=node['freq'],
                      bandwidth_MHz=node['bandwidth_MHz'],
                      antenna_gain_dBi=node['antenna_gain_dBi'],
                      noise_figure_dB=node['noise_figure_dB'])
        elif node['type'] == 'RIS':
            net.add_ris(node['name'], node['pos'][0], node['pos'][1], node['pos'][2],
                       N=node['N'], bits=node['bits'], freq=node['freq'],
                       max_angle_deg=node['max_angle_deg'],
                       normal_angle_deg=node['normal_angle_deg'])
        elif node['type'] == 'UE':
            net.add_ue(node['name'], node['pos'][0], node['pos'][1], node['pos'][2],
                      antenna_gain_dBi=node['antenna_gain_dBi'],
                      noise_figure_dB=node['noise_figure_dB'],
                      max_angle_deg=node['max_angle_deg'],
                      normal_angle_deg=node['normal_angle_deg'])

    ap = net.get('AP1')
    ris = net.get('R1')
    ue = net.get('UE1')

    ap_angle = np.degrees(np.arctan2((ap.pos - ris.pos)[1], (ap.pos - ris.pos)[0]))
    ue_angle = np.degrees(np.arctan2((ue.pos - ris.pos)[1], (ue.pos - ris.pos)[0]))

    angle_diff = ue_angle - ap_angle
    while angle_diff > 180:
        angle_diff -= 360
    while angle_diff < -180:
        angle_diff += 360

    ris_normal = ap_angle + angle_diff / 2

    # Steer beam to UE direction (-45° codebook)
    beam_codebook = -45
    abs_beam = ap_angle + beam_codebook

    print(f"\nSteering beam to UE direction:")
    print(f"  Codebook: {beam_codebook}°")
    print(f"  Absolute beam: {abs_beam:.2f}°")
    print(f"  UE angle: {ue_angle:.2f}°")

    # Get phases for this beam direction
    result = net.connect('AP1', 'R1', 'UE1', beam_angle_deg=abs_beam,
                        seed=42, use_get_snr=False, fixed_ris_normal=ris_normal)

    print(f"  Beam SNR: {result['snr_dB']:.2f} dB")

    # Now test SNR at different angles (sweep beam, not codebook)
    print(f"\n{'Beam Angle':>12} {'Offset from UE':>16} {'SNR':>10}")
    print("-"*45)

    # Test fine angles around UE
    test_angles = np.arange(abs_beam - 10, abs_beam + 11, 1)

    for test_beam in test_angles:
        res = net.connect('AP1', 'R1', 'UE1', beam_angle_deg=test_beam,
                         seed=42, use_get_snr=False, fixed_ris_normal=ris_normal)

        offset = abs(test_beam - ue_angle)
        if offset > 180:
            offset = 360 - offset

        marker = " ← UE" if abs(offset) < 0.5 else ""
        marker += " [-3dB]" if abs(offset) >= 3.5 and abs(offset) <= 4.0 else ""

        print(f"{test_beam:>12.2f}° {offset:>15.2f}° {res['snr_dB']:>9.2f} dB{marker}")

    print(f"\n{'='*80}")
    print("BEAMWIDTH ANALYSIS")
    print(f"{'='*80}")

    # Find -3dB points
    peak_snr = result['snr_dB']
    target_3db = peak_snr - 3.0

    print(f"\nPeak SNR: {peak_snr:.2f} dB")
    print(f"Target -3dB point: {target_3db:.2f} dB")

    # Test to find 3dB beamwidth
    offsets_tested = []
    snrs_tested = []

    for offset_deg in np.arange(0, 15, 0.5):
        test_beam_pos = abs_beam + offset_deg
        test_beam_neg = abs_beam - offset_deg

        res_pos = net.connect('AP1', 'R1', 'UE1', beam_angle_deg=test_beam_pos,
                             seed=42, use_get_snr=False, fixed_ris_normal=ris_normal)
        res_neg = net.connect('AP1', 'R1', 'UE1', beam_angle_deg=test_beam_neg,
                             seed=42, use_get_snr=False, fixed_ris_normal=ris_normal)

        offsets_tested.append(offset_deg)
        snrs_tested.append((res_pos['snr_dB'] + res_neg['snr_dB']) / 2)

    # Find where SNR drops to -3dB
    for i, (offset, snr) in enumerate(zip(offsets_tested, snrs_tested)):
        if snr <= target_3db:
            print(f"\n-3dB point found at ≈{offset:.1f}° offset (SNR = {snr:.2f} dB)")
            break
    else:
        print(f"\n-3dB point not found within ±15° offset")

    # Expected beamwidth for 16x16 array
    from core.physics import C
    wavelength = C / ris.freq
    element_spacing = wavelength / 2
    array_size = ris.N * element_spacing
    expected_bw = np.degrees(wavelength / array_size)

    print(f"\nExpected 3dB beamwidth (λ/D): {expected_bw:.2f}°")
    print(f"Measured 3dB beamwidth: ≈{offset:.1f}° (if found)")

    if offset < expected_bw / 2:
        print(f"\n⚠️  PROBLEM: Measured beamwidth is NARROWER than expected!")
        print(f"   This suggests array factor is dropping too steeply.")


if __name__ == "__main__":
    main()
