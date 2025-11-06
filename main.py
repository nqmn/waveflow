"""
RISNet - minimal RIS emulator core (Phase 1 + 2)
- Python 3.8+
- Dependencies: numpy, matplotlib (optional for visualization)

Features:
- Node classes: AccessPoint, RIS, UE
- Realistic near-field RIS phase design + beam gain model (simplified)
- RISNetwork manager with add/list/connect/sweep commands
- Simple interactive CLI (cmd-based)

Usage:
$ python RISNet_emulator_core.py
inside CLI:
  add ap ap1 2 0
  add ris ris1 8 0 0 32 2
  add ue ue1 10 3
  list
  connect ap1 ris1 ue1
  sweep ap1 ris1 ue1
  quit

This is a starting point meant to be extended.
"""

import sys
import shlex
import cmd
import pprint
import numpy as np
import math

# -----------------------------
# Physics / hardware helpers
# -----------------------------

# Global defaults
C = 3e8

# Useful helpers
def path_loss_dB(distance, freq):
    if distance <= 0:
        return 0.0
    return 20 * np.log10(4 * np.pi * distance * freq / C)

def rician_fading(K_factor_dB, size=1):
    K_linear = 10 ** (K_factor_dB / 10)
    los_component = np.sqrt(K_linear / (K_linear + 1))
    scatter_std = np.sqrt(1 / (K_linear + 1))
    scatter = scatter_std * (np.random.randn(size) + 1j * np.random.randn(size)) / np.sqrt(2)
    h = los_component + scatter
    return np.abs(h)

# -----------------------------
# RIS phase and beam functions
# -----------------------------

def compute_ris_phases(target_pos, element_pos, ap_pos, wavelength):
    """
    Compute ideal RIS reflection phase (radians) to focus energy at target_pos.
    φ_n = k * (r_AP,n + r_n,UE), returned mod 2π and referenced to element 0
    """
    k = 2 * np.pi / wavelength
    r_ap = np.linalg.norm(element_pos - ap_pos, axis=1)
    r_tgt = np.linalg.norm(element_pos - target_pos, axis=1)
    ideal_phases = k * (r_ap + r_tgt)
    ideal_phases = ideal_phases - ideal_phases[0]
    return np.mod(ideal_phases, 2 * np.pi)


def mutual_coupling_penalty(spacing_wavelengths, coupling_enabled=True):
    if not coupling_enabled:
        return 0.0
    if spacing_wavelengths <= 0.5:
        return 2.0
    elif spacing_wavelengths <= 0.7:
        return 1.0
    return 0.0

# realistic_beam_gain uses local parameters; keep defaults modest

def realistic_beam_gain(beam_angle_deg,
                        eval_target_pos,
                        element_pos,
                        ap_pos,
                        freq=10e9,
                        phase_bits=2,
                        phase_rms_deg=8.0,
                        amplitude_std=0.15,
                        coupling_enabled=True,
                        K_FACTOR_DB=10,
                        P_tx_dBm=20,
                        noise_floor_dBm=-90):
    """
    Return SNR_dB, P_rx_dBm, pattern_gain_linear for AP->RIS->eval_target
    beam_angle_deg: absolute steering angle (degrees) for the RIS focusing
    eval_target_pos: 3-vector where we evaluate received power
    element_pos: Nx3 element coordinates
    ap_pos: 3-vector
    """
    wavelength = C / freq
    # Build a beam target point at same range as eval_target but steered to beam_angle
    beam_distance = np.linalg.norm(eval_target_pos - np.mean(element_pos, axis=0))
    beam_target_pos = np.mean(element_pos, axis=0) + beam_distance * np.array([
        np.cos(np.radians(beam_angle_deg)), np.sin(np.radians(beam_angle_deg)), 0.0
    ])

    # Ideal shifter phases (radians) to focus to beam_target_pos
    ideal_phases = compute_ris_phases(beam_target_pos, element_pos, ap_pos, wavelength)

    # Quantize phases
    if phase_bits == 0:
        quantized_phases = ideal_phases.copy()
    else:
        levels = 2 ** phase_bits
        step = 2 * np.pi / levels
        quantized_phases = np.round(ideal_phases / step) * step

    # Phase errors (radians)
    phase_errors = np.deg2rad(np.random.normal(0, phase_rms_deg, element_pos.shape[0]))
    actual_phases = quantized_phases + phase_errors

    # Distances
    r_ap = np.linalg.norm(element_pos - ap_pos, axis=1)
    r_tgt = np.linalg.norm(element_pos - eval_target_pos, axis=1)

    # element amplitude variations
    element_gains = 1 + np.random.normal(0, amplitude_std, element_pos.shape[0])

    k = 2 * np.pi / wavelength
    contributions = element_gains * np.exp(1j * (actual_phases - k * (r_ap + r_tgt)))
    array_response = np.sum(contributions)
    pattern_gain_linear = (np.abs(array_response) / element_pos.shape[0]) ** 2

    # coupling
    coupling_loss = mutual_coupling_penalty(np.linalg.norm(element_pos[1] - element_pos[0]) / wavelength,
                                           coupling_enabled)

    # Path loss (AP->RIS + RIS->UE)
    d_ap_ris = np.linalg.norm(np.mean(element_pos, axis=0) - ap_pos)
    d_ris_tgt = np.linalg.norm(eval_target_pos - np.mean(element_pos, axis=0))
    PL_total = path_loss_dB(d_ap_ris, freq) + path_loss_dB(d_ris_tgt, freq)

    # Rician fading
    fading_coeff = rician_fading(K_FACTOR_DB)
    fading_dB = 20 * np.log10(fading_coeff + 1e-12)

    P_rx_dBm = (P_tx_dBm + 10 * np.log10(pattern_gain_linear + 1e-12) - coupling_loss - PL_total + fading_dB)
    SNR_dB = P_rx_dBm - noise_floor_dBm
    return float(SNR_dB), float(P_rx_dBm), float(pattern_gain_linear)

# -----------------------------
# Node classes
# -----------------------------

class Node:
    def __init__(self, name, x, y, z=0.0):
        self.name = name
        self.pos = np.array([float(x), float(y), float(z)])

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.name}', pos={self.pos.tolist()})"


class AccessPoint(Node):
    def __init__(self, name, x, y, z=0.0, power_dBm=20.0, freq=10e9):
        super().__init__(name, x, y, z)
        self.power_dBm = power_dBm
        self.freq = freq


class RIS(Node):
    def __init__(self, name, x, y, z=0.0, N=32, bits=2, spacing=None, freq=10e9):
        super().__init__(name, x, y, z)
        self.N = int(N)
        self.bits = int(bits)
        self.freq = freq
        self.spacing = spacing if spacing is not None else (C / freq) / 2.0
        self.element_positions = None
        self.phase_rms = 8.0
        self.amp_std = 0.15
        self.coupling_enabled = True
        self.K_db = 10
        self.P_tx_dBm = 20
        self.noise_floor = -90
        self.update_geometry()

    def update_geometry(self):
        # linear vertical array along y axis centered at RIS pos
        self.element_positions = np.zeros((self.N, 3))
        for n in range(self.N):
            y_off = (n - (self.N - 1) / 2.0) * self.spacing
            self.element_positions[n] = self.pos + np.array([0.0, y_off, 0.0])

    def set_bits(self, bits):
        self.bits = int(bits)


class UE(Node):
    def __init__(self, name, x, y, z=0.0):
        super().__init__(name, x, y, z)

# -----------------------------
# RISNetwork manager
# -----------------------------

class RISNetwork:
    def __init__(self):
        self.nodes = {}

    # node management
    def add_ap(self, name, x, y, z=0.0, power_dBm=20.0, freq=10e9):
        self.nodes[name] = AccessPoint(name, x, y, z, power_dBm, freq)

    def add_ris(self, name, x, y, z=0.0, N=32, bits=2, freq=10e9):
        self.nodes[name] = RIS(name, x, y, z, N, bits, None, freq)

    def add_ue(self, name, x, y, z=0.0):
        self.nodes[name] = UE(name, x, y, z)

    def list_nodes(self):
        for k, v in self.nodes.items():
            print(f"{k:10s} {v}")

    def get(self, name):
        return self.nodes.get(name, None)

    # compute cascaded AP->RIS->UE link for a given steering angle
    def connect(self, ap_name, ris_name, ue_name, beam_angle_deg=None):
        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)
        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in connect")

        # if no beam angle provided, steer to direct geometric direction
        if beam_angle_deg is None:
            # compute baseline angle from RIS->AP direction (absolute)
            vec = ap.pos - ris.pos
            base_dir = np.degrees(np.arctan2(vec[1], vec[0]))
            # compute target angle relative to base so we can use same local coord
            vec_tgt = ue.pos - ris.pos
            tgt_abs_angle = np.degrees(np.arctan2(vec_tgt[1], vec_tgt[0]))
            beam_angle_deg = tgt_abs_angle

        snr_db, pwr_dbm, gain = realistic_beam_gain(beam_angle_deg,
                                                     ue.pos,
                                                     ris.element_positions,
                                                     ap.pos,
                                                     freq=ap.freq,
                                                     phase_bits=ris.bits,
                                                     phase_rms_deg=ris.phase_rms,
                                                     amplitude_std=ris.amp_std,
                                                     coupling_enabled=ris.coupling_enabled,
                                                     K_FACTOR_DB=ris.K_db,
                                                     P_tx_dBm=ap.power_dBm,
                                                     noise_floor_dBm=ris.noise_floor)

        return {"snr_dB": snr_db, "pwr_dBm": pwr_dbm, "gain_linear": gain, "beam_angle": beam_angle_deg}

    # coarse sweep helper
    def sweep(self, ap_name, ris_name, ue_name, fov=60, step=10, fine_span=5, fine_res=1):
        ap = self.get(ap_name)
        ris = self.get(ris_name)
        ue = self.get(ue_name)
        if ap is None or ris is None or ue is None:
            raise ValueError("Invalid node name in sweep")

        vec = ap.pos - ris.pos
        base_dir = np.degrees(np.arctan2(vec[1], vec[0]))
        # local beams relative to base_dir
        local_coarse = np.arange(-fov, fov + 1, step)
        abs_angles = base_dir + local_coarse

        snr_coarse = []
        pwr_coarse = []
        for la, abs_a in zip(local_coarse, abs_angles):
            res = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a)
            snr_coarse.append(res['snr_dB'])
            pwr_coarse.append(res['pwr_dBm'])

        best_idx = int(np.argmax(snr_coarse))
        best_local = local_coarse[best_idx]

        # fine
        local_fine = np.arange(best_local - fine_span, best_local + fine_span + fine_res, fine_res)
        abs_angles_fine = base_dir + local_fine
        snr_fine = []
        for abs_a in abs_angles_fine:
            r = self.connect(ap_name, ris_name, ue_name, beam_angle_deg=abs_a)
            snr_fine.append(r['snr_dB'])

        best_fine_idx = int(np.argmax(snr_fine))
        best_local_fine = local_fine[best_fine_idx]

        return {
            'local_coarse': local_coarse,
            'snr_coarse': np.array(snr_coarse),
            'pwr_coarse': np.array(pwr_coarse),
            'local_fine': local_fine,
            'snr_fine': np.array(snr_fine),
            'best_local_fine': best_local_fine,
            'best_snr_fine': float(np.max(snr_fine))
        }

# -----------------------------
# Minimal CLI (cmd)
# -----------------------------

class RISNetCLI(cmd.Cmd):
    intro = "Welcome to RISNet CLI. Type help or ? to list commands."
    prompt = "risnet> "

    def __init__(self, net: RISNetwork):
        super().__init__()
        self.net = net

    def do_add(self, arg):
        """add <ap|ris|ue> name x y [z] [other params]
        Examples:
          add ap ap1 2 0
          add ris ris1 8 0 0 32 2
          add ue ue1 10 3
        """
        try:
            parts = shlex.split(arg)
            if len(parts) < 4:
                print("not enough args")
                return
            typ = parts[0]
            name = parts[1]
            x = float(parts[2]); y = float(parts[3]); z = float(parts[4]) if len(parts) > 4 else 0.0
            if typ == 'ap':
                self.net.add_ap(name, x, y, z)
                print(f"added AP {name}")
            elif typ == 'ris':
                N = int(parts[5]) if len(parts) > 5 else 32
                bits = int(parts[6]) if len(parts) > 6 else 2
                self.net.add_ris(name, x, y, z, N, bits)
                print(f"added RIS {name} (N={N}, bits={bits})")
            elif typ == 'ue':
                self.net.add_ue(name, x, y, z)
                print(f"added UE {name}")
            else:
                print('unknown type')
        except Exception as e:
            print('error:', e)

    def do_list(self, arg):
        """list nodes"""
        self.net.list_nodes()

    def do_connect(self, arg):
        """connect ap ris ue [beam_angle_deg]
        Example: connect ap1 ris1 ue1 30
        If beam angle omitted, auto-steer geometrically.
        """
        parts = shlex.split(arg)
        if len(parts) < 3:
            print('usage: connect ap ris ue [beam_angle]')
            return
        ap, ris, ue = parts[0], parts[1], parts[2]
        angle = float(parts[3]) if len(parts) > 3 else None
        res = self.net.connect(ap, ris, ue, beam_angle_deg=angle)
        pprint.pprint(res)

    def do_sweep(self, arg):
        """sweep ap ris ue [fov step]
        Example: sweep ap1 ris1 ue1 60 10
        """
        parts = shlex.split(arg)
        if len(parts) < 3:
            print('usage: sweep ap ris ue [fov step]')
            return
        ap, ris, ue = parts[0], parts[1], parts[2]
        fov = float(parts[3]) if len(parts) > 3 else 60.0
        step = float(parts[4]) if len(parts) > 4 else 10.0
        out = self.net.sweep(ap, ris, ue, fov=fov, step=step)
        print('coarse local angles:', out['local_coarse'])
        print('coarse SNR:', out['snr_coarse'])
        print('best refined local angle:', out['best_local_fine'])
        print('best refined SNR:', out['best_snr_fine'])

    def do_quit(self, arg):
        """quit"""
        print('bye')
        return True

    def do_exit(self, arg):
        return self.do_quit(arg)

# -----------------------------
# Main
# -----------------------------

def main():
    net = RISNetwork()
    cli = RISNetCLI(net)
    print('\nRISNet emulator (minimal). Type help for commands.')
    try:
        cli.cmdloop()
    except KeyboardInterrupt:
        print('\nexiting')

if __name__ == '__main__':
    main()
