"""
Investigate SNR calculation in detail
"""

import numpy as np
import json
from core.network import RISNetwork
from core.physics import Physics, C


def detailed_snr_breakdown(net, codebook, ap_angle, ue_angle, ris_normal):
    """Show complete SNR calculation breakdown"""

    ap = net.get('AP1')
    ris = net.get('R1')
    ue = net.get('UE1')

    abs_beam = ap_angle + codebook

    print(f"\n{'='*80}")
    print(f"CODEBOOK {codebook}° → BEAM {abs_beam:.2f}°")
    print(f"{'='*80}")

    # Run connect
    result = net.connect('AP1', 'R1', 'UE1', beam_angle_deg=abs_beam,
                        seed=42, use_get_snr=False, fixed_ris_normal=ris_normal)

    angular_offset = abs(abs_beam - ue_angle)
    if angular_offset > 180:
        angular_offset = 360 - angular_offset

    print(f"\nGeometry:")
    print(f"  Beam angle: {abs_beam:.2f}°")
    print(f"  UE angle: {ue_angle:.2f}°")
    print(f"  Angular offset: {angular_offset:.6f}°")

    print(f"\nResult:")
    print(f"  SNR: {result['snr_dB']:.6f} dB")
    print(f"  Gain: {result['gain_dBi']:.6f} dBi")
    print(f"  Power: {result['pwr_dBm']:.6f} dBm")
    print(f"  Quant loss: {result['quant_loss_dB']:.6f} dB")

    # Manual calculation to verify
    d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
    d_ris_ue = np.linalg.norm(ue.pos - ris.pos)

    pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)
    pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)

    print(f"\nPath loss:")
    print(f"  AP → RIS: {d_ap_ris:.2f}m, PL = {pl_ap_ris:.2f} dB")
    print(f"  RIS → UE: {d_ris_ue:.2f}m, PL = {pl_ris_ue:.2f} dB")
    print(f"  Total: {pl_ap_ris + pl_ris_ue:.2f} dB")

    # Check array factor
    if 'current_phases' in result and result['current_phases'] is not None:
        phases = np.array(result['current_phases'])

        N = ris.N
        wavelength = C / ris.freq
        element_spacing = wavelength / 2
        coords = np.arange(N) - (N - 1) / 2.0
        xs, ys = np.meshgrid(coords, coords, indexing="ij")
        element_positions = np.stack([xs, ys, np.zeros_like(xs)], axis=-1) * element_spacing
        element_positions = element_positions.reshape(-1, 3)
        element_positions += ris.pos

        # AF at UE
        af_at_ue = Physics.compute_array_factor(
            phases=phases,
            element_positions=element_positions,
            target_angle_deg=ue_angle,
            frequency=ris.freq,
            weights=None,
            ris_position=ris.pos,
            ap_position=ap.pos
        )

        # AF at beam
        af_at_beam = Physics.compute_array_factor(
            phases=phases,
            element_positions=element_positions,
            target_angle_deg=abs_beam,
            frequency=ris.freq,
            weights=None,
            ris_position=ris.pos,
            ap_position=ap.pos
        )

        print(f"\nArray Factor:")
        print(f"  AF at UE ({ue_angle:.2f}°): {af_at_ue:.6f} dB")
        print(f"  AF at beam ({abs_beam:.2f}°): {af_at_beam:.6f} dB")

        # Expected AF based on angular offset
        # For a uniform planar array, main lobe 3dB beamwidth ≈ λ/D where D = array size
        # For 16x16 array with λ/2 spacing: D = 8λ
        # 3dB beamwidth ≈ λ/(8λ) = 0.125 rad ≈ 7.2°

        beamwidth_3db = np.degrees(wavelength / (N * element_spacing))
        print(f"\nExpected 3dB beamwidth: {beamwidth_3db:.2f}°")

        if angular_offset < beamwidth_3db / 2:
            expected_af_range = "0 to -3 dB (main lobe)"
        elif angular_offset < beamwidth_3db:
            expected_af_range = "-3 to -6 dB (main lobe edge)"
        elif angular_offset < 2 * beamwidth_3db:
            expected_af_range = "-6 to -13 dB (first sidelobe region)"
        else:
            expected_af_range = "< -13 dB (far sidelobes)"

        print(f"  Expected AF for {angular_offset:.2f}° offset: {expected_af_range}")

        if abs(af_at_ue - af_at_beam) < 0.1:
            print(f"\n⚠️  WARNING: AF at UE ≈ AF at beam despite {angular_offset:.2f}° offset!")
        elif af_at_ue < -10 and angular_offset < beamwidth_3db:
            print(f"\n⚠️  WARNING: AF drop ({af_at_ue:.2f} dB) too large for {angular_offset:.2f}° offset!")

    return result


def main():
    print("="*80)
    print("DETAILED SNR CALCULATION INVESTIGATION")
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

    print(f"\nGeometry:")
    print(f"  AP: {ap.pos}")
    print(f"  RIS: {ris.pos}")
    print(f"  UE: {ue.pos}")
    print(f"  AP angle: {ap_angle:.2f}°")
    print(f"  UE angle: {ue_angle:.2f}°")
    print(f"  Deflection: {abs(angle_diff):.2f}°")

    # Test angles around peak
    test_codebooks = [-50, -45, -40]

    results = {}
    for codebook in test_codebooks:
        res = detailed_snr_breakdown(net, codebook, ap_angle, ue_angle, ris_normal)
        results[codebook] = res

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    print(f"\n{'Codebook':>10} {'Offset':>10} {'AF at UE':>12} {'SNR':>10}")
    print("-"*50)

    for codebook in test_codebooks:
        abs_beam = ap_angle + codebook
        offset = abs(abs_beam - ue_angle)
        if offset > 180:
            offset = 360 - offset

        res = results[codebook]

        # Get AF from result if available
        if 'current_phases' in res and res['current_phases'] is not None:
            phases = np.array(res['current_phases'])
            N = ris.N
            wavelength = C / ris.freq
            element_spacing = wavelength / 2
            coords = np.arange(N) - (N - 1) / 2.0
            xs, ys = np.meshgrid(coords, coords, indexing="ij")
            element_positions = np.stack([xs, ys, np.zeros_like(xs)], axis=-1) * element_spacing
            element_positions = element_positions.reshape(-1, 3)
            element_positions += ris.pos

            af = Physics.compute_array_factor(
                phases=phases,
                element_positions=element_positions,
                target_angle_deg=ue_angle,
                frequency=ris.freq,
                weights=None,
                ris_position=ris.pos,
                ap_position=ap.pos
            )
        else:
            af = 0.0

        print(f"{codebook:>10.0f}° {offset:>9.2f}° {af:>11.2f} dB {res['snr_dB']:>9.2f} dB")


if __name__ == "__main__":
    main()
