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

# Commented out - replaced by main_with_args() at the end of the file
# if __name__ == '__main__':
#     main()
# -----------------------------
# Web viewer & manager (Flask)
# -----------------------------
# This lightweight web UI provides:
# - A simple HTML/JS front-end to view nodes on a 2D map and issue add/connect/sweep commands
# - REST endpoints that call into the RISNetwork instance
#
# Requirements: pip install flask
# Run the app: python RISNet_emulator_core.py --web

from flask import Flask, jsonify, request, Response
import threading

# Try to import Waitress for production WSGI server
try:
    from waitress import serve as waitress_serve
    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False

app = Flask(__name__)
_net = None  # will be set when main() creates the RISNetwork

# Serve a modern HTML/JS UI (inspired by ris_simulator_7_barusiapbeamsweeping.html)
INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RISNet Manager v2.0</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    input[type="range"] {
      -webkit-appearance: none; appearance: none; width: 100%; height: 6px;
      border-radius: 5px; background: #d3d3d3; outline: none;
      opacity: 0.7; transition: opacity .2s;
    }
    input[type="range"]:hover { opacity: 1; }
    input[type="range"]::-webkit-slider-thumb {
      -webkit-appearance: none; appearance: none;
      width: 16px; height: 16px; border-radius: 50%;
      background: #4F46E5; cursor: pointer;
    }
    input[type="range"]::-moz-range-thumb {
      width: 16px; height: 16px; border-radius: 50%;
      background: #4F46E5; cursor: pointer;
    }
    #canvas{
      background-size: 10% 10%;
      background-image:
        linear-gradient(to right, #e5e7eb 1px, transparent 1px),
        linear-gradient(to bottom, #e5e7eb 1px, transparent 1px);
    }
  </style>
</head>
<body class="bg-gray-50">
  <div class="container mx-auto p-6 max-w-7xl">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
      <h1 class="text-3xl font-bold text-gray-800 mb-2">RISNet Manager v2.0</h1>
      <p class="text-gray-600">Reconfigurable Intelligent Surface Network Emulator</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Control Panel -->
      <div class="lg:col-span-1">
        <!-- Controller Panel -->
        <div class="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg shadow-lg p-5 mb-4 text-white">
          <h2 class="text-xl font-bold mb-4">🎮 RIS Controller</h2>

          <!-- Node Count Stats -->
          <div class="bg-white bg-opacity-10 rounded-lg p-3 mb-3">
            <div class="text-xs font-medium mb-2">Network Status</div>
            <div class="grid grid-cols-3 gap-2 text-xs">
              <div>
                <div class="text-white text-opacity-70">APs</div>
                <div class="font-bold text-lg" id="ap-count">0</div>
              </div>
              <div>
                <div class="text-white text-opacity-70">RIS</div>
                <div class="font-bold text-lg" id="ris-count">0</div>
              </div>
              <div>
                <div class="text-white text-opacity-70">UEs</div>
                <div class="font-bold text-lg" id="ue-count">0</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Add Node Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">Add Node</h3>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Type</label>
              <select id="add_type" class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
                <option value="ap">Access Point (AP)</option>
                <option value="ris">RIS Surface</option>
                <option value="ue">User Equipment (UE)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Name</label>
              <input id="add_name" placeholder="e.g., ap1, ris1, ue1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">X (m)</label>
                <input id="add_x" type="number" placeholder="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Y (m)</label>
                <input id="add_y" type="number" placeholder="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
              </div>
            </div>
            <div id="ris-params" style="display:none;">
              <label class="block text-xs font-medium text-gray-700 mb-1">RIS Parameters (N, bits)</label>
              <input id="add_N" placeholder="32,2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            </div>
            <button onclick="addNode()" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
              </svg>
              Add Node
            </button>
          </div>
        </div>

        <!-- Actions Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4">
          <h3 class="font-bold text-gray-800 mb-3">Actions</h3>
          <div class="space-y-2">
            <input id="act_ap" placeholder="AP name (e.g., ap1)" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            <input id="act_ris" placeholder="RIS name (e.g., ris1)" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            <input id="act_ue" placeholder="UE name (e.g., ue1)" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
            <div class="grid grid-cols-2 gap-2">
              <button onclick="connect()" class="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">Connect</button>
              <button onclick="sweep()" class="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg transition-colors">Sweep</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Visualization -->
      <div class="lg:col-span-2">
        <!-- Metrics Dashboard -->
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-4 mb-4 text-white">
          <div class="flex items-center gap-3">
            <div class="text-sm font-bold whitespace-nowrap">Live Metrics:</div>
            <div class="flex flex-wrap gap-2 flex-1">
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80 leading-tight">SNR</div>
                <div class="font-bold text-base" id="metric-snr">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80 leading-tight">Power (dBm)</div>
                <div class="font-bold text-base" id="metric-power">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80 leading-tight">Gain</div>
                <div class="font-bold text-base" id="metric-gain">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80 leading-tight">Beam Angle</div>
                <div class="font-bold text-base" id="metric-angle">--</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 2D Visualization -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <div class="flex items-center justify-between mb-3">
            <h3 class="font-bold text-gray-800">2D Network View</h3>
            <div class="flex items-center gap-2">
              <label class="text-xs font-medium text-gray-700">Scale:</label>
              <input id="scale" type="number" value="30" class="w-16 px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"/>
              <span class="text-xs text-gray-500">px/m</span>
            </div>
          </div>
          <div id="canvas" class="border border-gray-300 rounded bg-gray-50" style="width: 100%; height: 500px;"></div>
        </div>

        <!-- Nodes List -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">Active Nodes</h3>
          <div id="nodes" class="text-sm text-gray-700"></div>
        </div>

        <!-- Results Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4">
          <h3 class="font-bold text-gray-800 mb-3">Last Result</h3>
          <pre id="result" class="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto font-mono">No results yet. Run Connect or Sweep.</pre>
        </div>
      </div>
    </div>
  </div>

<script>
const canvas = document.getElementById('canvas');
const scaleInput = document.getElementById('scale');
let scale = parseFloat(scaleInput.value);
scaleInput.onchange = ()=>{ scale = parseFloat(scaleInput.value); draw(); };

// Drag state
let dragState = {
  isDragging: false,
  node: null,
  startX: 0,
  startY: 0,
  offsetX: 0,
  offsetY: 0
};

// Show/hide RIS parameters based on node type
document.getElementById('add_type').onchange = (e) => {
  document.getElementById('ris-params').style.display = e.target.value === 'ris' ? 'block' : 'none';
};

function api(path, opts){
  return fetch(path, opts).then(r=>r.json());
}

async function refresh(){
  const data = await api('/api/nodes');
  window.nodes = data.nodes;
  draw();
  renderList();
  updateCounts();
}

function updateCounts(){
  if(!window.nodes) return;
  const counts = {AP:0, RIS:0, UE:0};
  window.nodes.forEach(n => counts[n.type]++);
  document.getElementById('ap-count').textContent = counts.AP;
  document.getElementById('ris-count').textContent = counts.RIS;
  document.getElementById('ue-count').textContent = counts.UE;
}

// Convert canvas coordinates to world coordinates
function canvasToWorld(canvasX, canvasY, ox, oy) {
  return {
    x: (canvasX - ox) / scale,
    y: (oy - canvasY) / scale
  };
}

// Update node position on server
async function updateNodePosition(name, x, y) {
  try {
    await api('/api/update_position', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, x, y})
    });
  } catch(e) {
    console.error('Failed to update position:', e);
  }
}

function draw(){
  canvas.innerHTML = '';
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','100%'); svg.setAttribute('height','500');
  const ox = 400, oy = 250;
  if(!window.nodes) return;

  // Add mouse event handlers to SVG
  svg.onmousemove = (e) => {
    if(!dragState.isDragging) return;

    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    // Update node visual position
    const newX = mouseX - dragState.offsetX;
    const newY = mouseY - dragState.offsetY;

    if(dragState.element) {
      if(dragState.element.tagName === 'rect') {
        dragState.element.setAttribute('x', newX - 8);
        dragState.element.setAttribute('y', newY - 8);
      } else {
        dragState.element.setAttribute('cx', newX);
        dragState.element.setAttribute('cy', newY);
      }
    }
    if(dragState.text) {
      dragState.text.setAttribute('x', newX + 14);
      dragState.text.setAttribute('y', newY + 5);
    }
  };

  svg.onmouseup = async (e) => {
    if(!dragState.isDragging) return;

    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const finalX = mouseX - dragState.offsetX;
    const finalY = mouseY - dragState.offsetY;

    // Convert to world coordinates
    const worldPos = canvasToWorld(finalX, finalY, ox, oy);

    // Update in local state
    const node = window.nodes.find(n => n.name === dragState.node.name);
    if(node) {
      node.pos[0] = worldPos.x;
      node.pos[1] = worldPos.y;
    }

    // Update on server
    await updateNodePosition(dragState.node.name, worldPos.x, worldPos.y);

    // Reset drag state
    dragState.isDragging = false;
    dragState.node = null;
    dragState.element = null;
    dragState.text = null;
    svg.style.cursor = 'default';

    // Redraw to ensure consistency
    draw();
  };

  window.nodes.forEach(n=>{
    const x = ox + n.pos[0]*scale;
    const y = oy - n.pos[1]*scale;
    let el;

    if(n.type=='AP'){
      el = document.createElementNS('http://www.w3.org/2000/svg','rect');
      el.setAttribute('width',16); el.setAttribute('height',16);
      el.setAttribute('x',x-8); el.setAttribute('y',y-8);
      el.setAttribute('fill','#10b981'); el.setAttribute('stroke','#059669'); el.setAttribute('stroke-width','2');
    } else if(n.type=='RIS'){
      el = document.createElementNS('http://www.w3.org/2000/svg','circle');
      el.setAttribute('r',10); el.setAttribute('cx',x); el.setAttribute('cy',y);
      el.setAttribute('fill','#6366f1'); el.setAttribute('stroke','#4f46e5'); el.setAttribute('stroke-width','2');
    } else {
      el = document.createElementNS('http://www.w3.org/2000/svg','circle');
      el.setAttribute('r',8); el.setAttribute('cx',x); el.setAttribute('cy',y);
      el.setAttribute('fill','#ef4444'); el.setAttribute('stroke','#dc2626'); el.setAttribute('stroke-width','2');
    }

    // Make draggable
    el.style.cursor = 'move';
    el.onmousedown = (e) => {
      e.stopPropagation();
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      dragState.isDragging = true;
      dragState.node = n;
      dragState.element = el;
      dragState.text = text;
      dragState.offsetX = mouseX - x;
      dragState.offsetY = mouseY - y;
      svg.style.cursor = 'grabbing';
    };

    svg.appendChild(el);

    const text = document.createElementNS('http://www.w3.org/2000/svg','text');
    text.setAttribute('x',x+14); text.setAttribute('y',y+5);
    text.textContent = n.name;
    text.setAttribute('font-size','13');
    text.setAttribute('font-weight','600');
    text.setAttribute('fill','#374151');
    text.style.pointerEvents = 'none'; // Don't interfere with dragging
    svg.appendChild(text);
  });
  canvas.appendChild(svg);
}

function renderList(){
  const div = document.getElementById('nodes');
  div.innerHTML = '';
  if(!window.nodes || window.nodes.length === 0) {
    div.innerHTML = '<p class="text-gray-400 text-sm">No nodes added yet.</p>';
    return;
  }
  const ul = document.createElement('ul');
  ul.className = 'space-y-1';
  window.nodes.forEach(n=>{
    const li = document.createElement('li');
    li.className = 'flex items-center gap-2 py-1';
    const badge = document.createElement('span');
    badge.className = 'px-2 py-0.5 rounded text-xs font-semibold';
    if(n.type === 'AP') badge.className += ' bg-green-100 text-green-800';
    else if(n.type === 'RIS') badge.className += ' bg-indigo-100 text-indigo-800';
    else badge.className += ' bg-red-100 text-red-800';
    badge.textContent = n.type;
    li.appendChild(badge);
    const text = document.createElement('span');
    text.textContent = `${n.name} @ (${n.pos.map(p=>p.toFixed(1)).join(', ')})`;
    li.appendChild(text);
    ul.appendChild(li);
  });
  div.appendChild(ul);
}

async function addNode(){
  const type=document.getElementById('add_type').value;
  const name=document.getElementById('add_name').value;
  if(!name) { alert('Please enter a node name'); return; }
  const x=parseFloat(document.getElementById('add_x').value||0);
  const y=parseFloat(document.getElementById('add_y').value||0);
  const nval=document.getElementById('add_N').value;
  let body={type,name,x,y};
  if(type=='ris' && nval){
    const parts=nval.split(',');
    body.N=parseInt(parts[0])||32;
    body.bits=parseInt(parts[1])||2;
  }
  await api('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  await refresh();
}

async function connect(){
  const ap=document.getElementById('act_ap').value;
  const ris=document.getElementById('act_ris').value;
  const ue=document.getElementById('act_ue').value;
  if(!ap || !ris || !ue) { alert('Please enter AP, RIS, and UE names'); return; }
  const res=await api(`/api/connect?ap=${ap}&ris=${ris}&ue=${ue}`);
  document.getElementById('result').textContent = JSON.stringify(res,null,2);
  if(res.snr_dB !== undefined){
    document.getElementById('metric-snr').textContent = res.snr_dB.toFixed(1) + ' dB';
    document.getElementById('metric-power').textContent = res.pwr_dBm.toFixed(1);
    document.getElementById('metric-gain').textContent = res.gain_linear.toFixed(3);
    document.getElementById('metric-angle').textContent = res.beam_angle.toFixed(1) + '°';
  }
}

async function sweep(){
  const ap=document.getElementById('act_ap').value;
  const ris=document.getElementById('act_ris').value;
  const ue=document.getElementById('act_ue').value;
  if(!ap || !ris || !ue) { alert('Please enter AP, RIS, and UE names'); return; }
  const res=await api(`/api/sweep?ap=${ap}&ris=${ris}&ue=${ue}`);
  document.getElementById('result').textContent = JSON.stringify(res,null,2);
  if(res.best_snr_fine !== undefined){
    document.getElementById('metric-snr').textContent = res.best_snr_fine.toFixed(1) + ' dB';
    document.getElementById('metric-angle').textContent = res.best_local_fine.toFixed(1) + '°';
  }
}

// Initial refresh
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>
"""

# REST endpoints
@app.route('/')
def index():
    return Response(INDEX_HTML, mimetype='text/html')

@app.route('/api/nodes')
def api_nodes():
    nodes = []
    for name, node in _net.nodes.items():
        ntype = node.__class__.__name__
        nodes.append({'name': name, 'type': ntype, 'pos': node.pos.tolist()})
    return jsonify({'nodes': nodes})

@app.route('/api/add', methods=['POST'])
def api_add():
    data = request.get_json() or {}
    typ = data.get('type')
    name = data.get('name')
    x = float(data.get('x',0))
    y = float(data.get('y',0))
    if typ == 'ap':
        _net.add_ap(name, x, y)
    elif typ == 'ris':
        N = int(data.get('N', 32)); bits = int(data.get('bits', 2))
        _net.add_ris(name, x, y, 0.0, N, bits)
    elif typ == 'ue':
        _net.add_ue(name, x, y)
    else:
        return jsonify({'error': 'unknown type'}), 400
    return jsonify({'ok': True})

@app.route('/api/connect')
def api_connect():
    ap = request.args.get('ap')
    ris = request.args.get('ris')
    ue = request.args.get('ue')
    angle = request.args.get('angle')
    angle = float(angle) if angle is not None else None
    try:
        res = _net.connect(ap, ris, ue, beam_angle_deg=angle)
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/sweep')
def api_sweep():
    ap = request.args.get('ap')
    ris = request.args.get('ris')
    ue = request.args.get('ue')
    try:
        out = _net.sweep(ap, ris, ue)
        # convert numpy arrays to lists
        out['snr_coarse'] = out['snr_coarse'].tolist()
        out['pwr_coarse'] = out['pwr_coarse'].tolist()
        out['snr_fine'] = out['snr_fine'].tolist()
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update_position', methods=['POST'])
def api_update_position():
    """Update node position when dragged in the visualization"""
    data = request.get_json() or {}
    name = data.get('name')
    x = float(data.get('x', 0))
    y = float(data.get('y', 0))

    node = _net.get(name)
    if node is None:
        return jsonify({'error': 'Node not found'}), 404

    node.pos[0] = x
    node.pos[1] = y

    # Update RIS geometry if it's a RIS node
    if hasattr(node, 'update_geometry'):
        node.update_geometry()

    return jsonify({'ok': True, 'name': name, 'pos': [x, y]})

# -----------------------------
# Integrate web option into main
# -----------------------------

def run_web(app, host='127.0.0.1', port=5000):
    """Run the Flask app using Waitress (production WSGI) or Flask dev server as fallback"""
    if WAITRESS_AVAILABLE:
        print(f'Using Waitress WSGI server (production-ready)')
        print(f'Server running on http://{host}:{port}')
        print('Press Ctrl+C to quit')
        waitress_serve(app, host=host, port=port, threads=4)
    else:
        print('Waitress not found. Using Flask development server.')
        print('For production, install waitress: pip install waitress')
        app.run(host=host, port=port, threaded=True)

# Patch main to accept --web
import argparse

def main_with_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--web', action='store_true', help='run web UI')
    args = parser.parse_args()

    net = RISNetwork()
    global _net
    _net = net

    if args.web:
        # CLI thread disabled when running in web mode (causes EOF errors)
        # The web UI provides all necessary interaction through the browser
        print('\n' + '='*60)
        print('RISNet Web Manager v2.0')
        print('='*60)
        run_web(app)
    else:
        cli = RISNetCLI(net)
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print('\nexiting')

if __name__ == '__main__':
    main_with_args()

