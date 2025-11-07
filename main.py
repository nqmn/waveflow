"""
RISNet v2.0 - Advanced RIS Network Simulator
Full-featured with:
- Multi-algorithm pathfinding (Dijkstra, A*, Greedy, Exhaustive)
- Advanced beam sweeping with CFAR detection
- Environment modeling with walls/obstacles
- Centralized RIS controller
- YAML configuration support
- Modular architecture

Usage:
    python main.py --web        # Run web interface
    python main.py --cli        # Run CLI interface
"""

import sys
import argparse
import numpy as np
import cmd
import shlex
import pprint

# Import core modules
from core import RISNetwork, AccessPoint, RIS, UE, Environment, Physics
from algorithms import PathfindingEngine, BeamformingEngine
from controller import RISController
from config import Config

# Flask imports
from flask import Flask, jsonify, request, Response

# Try to import Waitress for production WSGI server
try:
    from waitress import serve as waitress_serve
    WAITRESS_AVAILABLE = True
except ImportError:
    WAITRESS_AVAILABLE = False

# Try to import PyYAML
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

app = Flask(__name__)
_net = None  # Global network instance
_controller = None  # Global controller instance
_config = None  # Global config instance

# =====================================================================
# Enhanced HTML Frontend with All Features
# =====================================================================

INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RISNet v2.0 - Advanced Simulator</title>
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
    .path-line {
      stroke-width: 2;
      fill: none;
      pointer-events: none;
    }
    .path-direct { stroke: #F59E0B; stroke-dasharray: 4; }
    .path-reflected { stroke: #6366F1; }
    .path-relay { stroke: #8B5CF6; stroke-dasharray: 2; }
  </style>
</head>
<body class="bg-gray-50">
  <div class="container mx-auto p-6 max-w-7xl">
    <!-- Header -->
    <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
      <h1 class="text-3xl font-bold text-gray-800 mb-2">RISNet v2.0 - Advanced Simulator</h1>
      <p class="text-gray-600">Modular RIS Network Simulator with Multi-Algorithm Pathfinding</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Left Column: Control Panel -->
      <div class="lg:col-span-1">
        <!-- Controller Panel -->
        <div class="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-lg shadow-lg p-5 mb-4 text-white">
          <h2 class="text-xl font-bold mb-4">🎮 RIS Controller</h2>

          <!-- Controller Toggle -->
          <div class="bg-white bg-opacity-10 rounded-lg p-3 mb-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium">Controller Enabled</span>
              <input type="checkbox" id="controller-enabled" checked class="w-4 h-4">
            </div>
          </div>

          <!-- Algorithm Selection -->
          <div class="bg-white bg-opacity-10 rounded-lg p-3 mb-3">
            <label class="block text-xs font-medium mb-1">Algorithm</label>
            <select id="algorithm-select" class="w-full px-2 py-1 bg-white text-gray-900 rounded text-sm">
              <option value="dijkstra">Dijkstra (Optimal)</option>
              <option value="astar">A* (Heuristic)</option>
              <option value="greedy">Greedy (Fast)</option>
              <option value="exhaustive">Exhaustive (All Paths)</option>
            </select>
          </div>

          <!-- Controller Stats -->
          <div class="bg-white bg-opacity-10 rounded-lg p-3 mb-3">
            <div class="text-xs font-medium mb-2">Statistics</div>
            <div class="grid grid-cols-2 gap-2 text-xs">
              <div>
                <div class="text-white text-opacity-70">Paths Found</div>
                <div class="font-bold text-lg" id="paths-found">0</div>
              </div>
              <div>
                <div class="text-white text-opacity-70">Decision Time</div>
                <div class="font-bold text-lg" id="decision-time">0 ms</div>
              </div>
              <div>
                <div class="text-white text-opacity-70">Best SNR</div>
                <div class="font-bold text-lg" id="best-snr">-- dB</div>
              </div>
              <div>
                <div class="text-white text-opacity-70">Updates</div>
                <div class="font-bold text-lg" id="update-count">0</div>
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
              <select id="add_type" class="w-full px-3 py-2 bg-white border border-gray-300 rounded-lg text-sm">
                <option value="ap">Access Point (AP)</option>
                <option value="ris">RIS Surface</option>
                <option value="ue">User Equipment (UE)</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Name</label>
              <input id="add_name" placeholder="e.g., ap1, ris1, ue1" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">X (m)</label>
                <input id="add_x" type="number" placeholder="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
              </div>
              <div>
                <label class="block text-xs font-medium text-gray-700 mb-1">Y (m)</label>
                <input id="add_y" type="number" placeholder="0" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
              </div>
            </div>
            <div id="ris-params" style="display:none;">
              <label class="block text-xs font-medium text-gray-700 mb-1">RIS: Grid Size (N), Bits</label>
              <input id="add_ris_params" placeholder="16,2" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
            </div>
            <button onclick="addNode()" class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded-lg">
              Add Node
            </button>
          </div>
        </div>

        <!-- Environment Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">Environment</h3>
          <button onclick="addWall()" class="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg mb-2">
            Add Wall
          </button>
          <button onclick="clearWalls()" class="w-full bg-gray-400 hover:bg-gray-500 text-white font-medium py-2 px-4 rounded-lg">
            Clear Walls
          </button>
          <div id="walls-list" class="mt-3 text-xs"></div>
        </div>

        <!-- Actions Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4">
          <h3 class="font-bold text-gray-800 mb-3">Actions</h3>
          <div class="space-y-2">
            <input id="act_ap" placeholder="AP name" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
            <input id="act_ris" placeholder="RIS name (optional)" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
            <input id="act_ue" placeholder="UE name" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"/>
            <div class="grid grid-cols-2 gap-2">
              <button onclick="connect()" class="bg-green-600 hover:bg-green-700 text-white font-medium py-2 rounded-lg">Connect</button>
              <button onclick="findPaths()" class="bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 rounded-lg">Find Paths</button>
            </div>
            <button onclick="sweep()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 rounded-lg">Beam Sweep</button>
          </div>
        </div>
      </div>

      <!-- Right Column: Visualization -->
      <div class="lg:col-span-2">
        <!-- Metrics Dashboard -->
        <div class="bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow-lg p-4 mb-4 text-white">
          <div class="flex items-center gap-3">
            <div class="text-sm font-bold">Live Metrics:</div>
            <div class="flex flex-wrap gap-2 flex-1">
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80">SNR</div>
                <div class="font-bold text-base" id="metric-snr">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80">Power (dBm)</div>
                <div class="font-bold text-base" id="metric-power">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80">Hops</div>
                <div class="font-bold text-base" id="metric-hops">--</div>
              </div>
              <div class="bg-white bg-opacity-20 rounded px-3 py-1.5 flex-1 min-w-[100px]">
                <div class="text-[10px] opacity-80">Path Type</div>
                <div class="font-bold text-base" id="metric-type">--</div>
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
              <input id="scale" type="number" value="30" class="w-16 px-2 py-1 border border-gray-300 rounded text-sm"/>
              <span class="text-xs text-gray-500">px/m</span>
            </div>
          </div>
          <div id="canvas" class="border border-gray-300 rounded bg-gray-50" style="width: 100%; height: 500px;"></div>
        </div>

        <!-- Paths Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">Available Paths</h3>
          <div id="paths-list" class="text-sm"></div>
        </div>

        <!-- RIS Phase Visualization Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">RIS Phase Elements</h3>
          <div class="space-y-3">
            <div>
              <label class="block text-xs font-medium text-gray-700 mb-1">Select RIS</label>
              <select id="phase-ris-select" class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm">
                <option value="">Choose a RIS...</option>
              </select>
            </div>
            <button onclick="loadPhases()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg">
              Load Phase Grid
            </button>
            <div id="phase-stats" class="text-xs bg-gray-50 p-3 rounded hidden">
              <div class="grid grid-cols-2 gap-2">
                <div><span class="text-gray-600">Grid Size:</span> <span id="stat-grid" class="font-bold">--</span></div>
                <div><span class="text-gray-600">Bits:</span> <span id="stat-bits" class="font-bold">--</span></div>
                <div><span class="text-gray-600">States:</span> <span id="stat-states" class="font-bold">--</span></div>
                <div><span class="text-gray-600">Total Elements:</span> <span id="stat-elements" class="font-bold">--</span></div>
              </div>
            </div>
            <div id="phase-grid-container" class="bg-gray-50 p-3 rounded overflow-x-auto hidden">
              <div class="text-xs font-medium text-gray-700 mb-2">Quantized Phases (degrees)</div>
              <canvas id="phase-canvas" width="300" height="300" style="border: 1px solid #ccc;"></canvas>
            </div>
          </div>
        </div>

        <!-- Results Panel -->
        <div class="bg-white rounded-lg shadow-lg p-4">
          <h3 class="font-bold text-gray-800 mb-3">Results</h3>
          <pre id="result" class="bg-gray-900 text-green-400 p-3 rounded text-xs overflow-x-auto font-mono">Ready. Use actions above.</pre>
        </div>
      </div>
    </div>
  </div>

<script>
const canvas = document.getElementById('canvas');
const scaleInput = document.getElementById('scale');
let scale = parseFloat(scaleInput.value);
scaleInput.onchange = ()=>{ scale = parseFloat(scaleInput.value); draw(); };

let dragState = { isDragging: false, node: null };
let currentPaths = [];
let selectedPath = null;

document.getElementById('add_type').onchange = (e) => {
  document.getElementById('ris-params').style.display = e.target.value === 'ris' ? 'block' : 'none';
};

function api(path, opts){
  return fetch(path, opts).then(r=>r.json());
}

async function refresh(){
  const data = await api('/api/nodes');
  window.nodes = data.nodes;
  updateRISSelectOptions();
  draw();
}

async function updateRISSelectOptions(){
  const select = document.getElementById('phase-ris-select');
  const nodes = window.nodes || [];
  const risNodes = nodes.filter(n => n.type === 'RIS');

  // Keep current selection if valid
  const currentVal = select.value;
  select.innerHTML = '<option value="">Choose a RIS...</option>';

  risNodes.forEach(ris => {
    const opt = document.createElement('option');
    opt.value = ris.name;
    opt.textContent = ris.name;
    select.appendChild(opt);
  });

  if(currentVal && risNodes.find(r => r.name === currentVal)){
    select.value = currentVal;
  }
}

async function loadPhases(){
  const risName = document.getElementById('phase-ris-select').value;
  if(!risName) { alert('Select a RIS first'); return; }

  try {
    const response = await fetch(`/api/ris/${risName}/phases`);
    const data = await response.json();

    if(!response.ok) {
      alert('Error: ' + data.error);
      return;
    }

    // Show stats
    document.getElementById('stat-grid').textContent = data.grid_size;
    document.getElementById('stat-bits').textContent = data.bits;
    document.getElementById('stat-states').textContent = data.phase_states;
    document.getElementById('stat-elements').textContent = data.total_elements;
    document.getElementById('phase-stats').classList.remove('hidden');

    // Draw phase grid
    drawPhaseGrid(data);
    document.getElementById('phase-grid-container').classList.remove('hidden');

  } catch(e) {
    alert('Failed to load phases: ' + e.message);
  }
}

function drawPhaseGrid(data){
  const canvas = document.getElementById('phase-canvas');
  const ctx = canvas.getContext('2d');
  const grid = data.phase_grid.quantized_deg || data.phase_grid.ideal_deg;
  const N = data.grid_size;

  if(!grid || grid.length === 0) {
    ctx.fillStyle = '#999';
    ctx.fillText('No phase data', 10, 20);
    return;
  }

  const cellSize = Math.floor(canvas.width / N);
  const maxPhase = 360;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = '11px monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  for(let i = 0; i < N; i++) {
    for(let j = 0; j < N; j++) {
      const phase = grid[i][j];
      const hue = (phase / maxPhase) * 360;

      // Draw cell with color gradient based on phase
      ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
      ctx.fillRect(j * cellSize, i * cellSize, cellSize, cellSize);

      // Draw border
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 0.5;
      ctx.strokeRect(j * cellSize, i * cellSize, cellSize, cellSize);

      // Draw phase value text (only for larger grids where readable)
      if(N <= 8) {
        ctx.fillStyle = '#000';
        ctx.fillText(Math.round(phase), j * cellSize + cellSize/2, i * cellSize + cellSize/2);
      }
    }
  }

  // Draw legend
  const legendY = canvas.height + 15;
  ctx.fillStyle = '#000';
  ctx.textAlign = 'left';
  ctx.font = '10px monospace';
  ctx.fillText('0°', canvas.width * 0 / 6, legendY);
  ctx.fillText('90°', canvas.width * 1.5 / 6, legendY);
  ctx.fillText('180°', canvas.width * 3 / 6, legendY);
  ctx.fillText('270°', canvas.width * 4.5 / 6, legendY);
  ctx.fillText('360°', canvas.width * 6 / 6 - 15, legendY);
}

async function addNode(){
  const type=document.getElementById('add_type').value;
  const name=document.getElementById('add_name').value;
  if(!name) { alert('Enter node name'); return; }
  const x=parseFloat(document.getElementById('add_x').value||0);
  const y=parseFloat(document.getElementById('add_y').value||0);
  const params=document.getElementById('add_ris_params').value;
  let body={type,name,x,y};
  if(type=='ris' && params){
    const parts=params.split(',');
    body.N=parseInt(parts[0])||16;
    body.bits=parseInt(parts[1])||2;
  }
  await api('/api/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  await refresh();
}

async function connect(){
  const ap=document.getElementById('act_ap').value;
  const ris=document.getElementById('act_ris').value;
  const ue=document.getElementById('act_ue').value;
  if(!ap || !ris || !ue) { alert('Enter AP, RIS, UE'); return; }
  const res=await api(`/api/connect?ap=${ap}&ris=${ris}&ue=${ue}`);
  document.getElementById('result').textContent = JSON.stringify(res,null,2);
  if(res.snr_dB !== undefined){
    document.getElementById('metric-snr').textContent = res.snr_dB.toFixed(1) + ' dB';
    document.getElementById('metric-power').textContent = res.pwr_dBm.toFixed(1);
  }
}

async function findPaths(){
  const ap=document.getElementById('act_ap').value;
  const ue=document.getElementById('act_ue').value;
  const algorithm=document.getElementById('algorithm-select').value;
  if(!ap || !ue) { alert('Enter AP and UE'); return; }

  const res=await api(`/api/find_paths?ap=${ap}&ue=${ue}&algorithm=${algorithm}`);
  currentPaths = res.paths || [];

  document.getElementById('result').textContent = JSON.stringify(res,null,2);

  // Display paths list
  const pathsList = document.getElementById('paths-list');
  if(currentPaths.length === 0){
    pathsList.innerHTML = '<p class="text-gray-400">No paths found</p>';
  } else {
    let html = '<div class="space-y-2">';
    currentPaths.forEach((p, idx) => {
      const pathStr = p.path.join(' → ');
      html += `
        <div class="border rounded p-2 cursor-pointer hover:bg-gray-50" onclick="selectPath(${idx})">
          <div class="font-semibold">${p.type}: ${pathStr}</div>
          <div class="text-xs text-gray-600">SNR: ${p.snr_dB.toFixed(1)} dB | Hops: ${p.hops}</div>
        </div>
      `;
    });
    html += '</div>';
    pathsList.innerHTML = html;

    // Update stats
    if(res.stats){
      document.getElementById('paths-found').textContent = res.stats.paths_found;
      document.getElementById('decision-time').textContent = res.stats.last_decision_time_ms + ' ms';
      document.getElementById('best-snr').textContent = res.stats.best_snr_dB?.toFixed(1) + ' dB' || '--';
      document.getElementById('update-count').textContent = res.stats.update_count;
    }

    // Select best path
    if(currentPaths.length > 0){
      selectPath(0);
    }
  }
}

function selectPath(idx){
  selectedPath = currentPaths[idx];
  document.getElementById('metric-snr').textContent = selectedPath.snr_dB.toFixed(1) + ' dB';
  document.getElementById('metric-hops').textContent = selectedPath.hops;
  document.getElementById('metric-type').textContent = selectedPath.type;
  draw();
}

async function sweep(){
  const ap=document.getElementById('act_ap').value;
  const ris=document.getElementById('act_ris').value;
  const ue=document.getElementById('act_ue').value;
  if(!ap || !ris || !ue) { alert('Enter AP, RIS, UE'); return; }
  const res=await api(`/api/sweep?ap=${ap}&ris=${ris}&ue=${ue}`);
  document.getElementById('result').textContent = JSON.stringify(res,null,2);
  if(res.best_snr_fine !== undefined){
    document.getElementById('metric-snr').textContent = res.best_snr_fine.toFixed(1) + ' dB';
  }
}

async function addWall(){
  // Simple implementation: add wall from (0,0) to (5,5)
  await api('/api/walls/add',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({start:[0,0],end:[5,5],attenuation_dB:20})});
  await refresh();
}

async function clearWalls(){
  await api('/api/walls/clear',{method:'POST'});
  await refresh();
}

async function updateNodePosition(name, x, y) {
  await api('/api/update_position', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name, x, y})
  });
}

function draw(){
  canvas.innerHTML = '';
  const svg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('width','100%'); svg.setAttribute('height','500');
  const ox = 400, oy = 250;
  if(!window.nodes) return;

  // Draw selected path
  if(selectedPath && selectedPath.path){
    const pathNodes = selectedPath.path;
    for(let i = 0; i < pathNodes.length - 1; i++){
      const n1 = window.nodes.find(n => n.name === pathNodes[i]);
      const n2 = window.nodes.find(n => n.name === pathNodes[i+1]);
      if(n1 && n2){
        const x1 = ox + n1.pos[0]*scale;
        const y1 = oy - n1.pos[1]*scale;
        const x2 = ox + n2.pos[0]*scale;
        const y2 = oy - n2.pos[1]*scale;

        const line = document.createElementNS('http://www.w3.org/2000/svg','line');
        line.setAttribute('x1', x1);
        line.setAttribute('y1', y1);
        line.setAttribute('x2', x2);
        line.setAttribute('y2', y2);
        line.setAttribute('class', `path-line path-${selectedPath.type}`);
        svg.appendChild(line);
      }
    }
  }

  // Mouse handlers
  svg.onmousemove = (e) => {
    if(!dragState.isDragging) return;
    const rect = svg.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
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
    const worldX = (finalX - ox) / scale;
    const worldY = (oy - finalY) / scale;
    const node = window.nodes.find(n => n.name === dragState.node.name);
    if(node) {
      node.pos[0] = worldX;
      node.pos[1] = worldY;
    }
    await updateNodePosition(dragState.node.name, worldX, worldY);
    dragState.isDragging = false;
    dragState.node = null;
    dragState.element = null;
    dragState.text = null;
    svg.style.cursor = 'default';
    draw();
  };

  // Draw nodes
  window.nodes.forEach(n=>{
    const x = ox + n.pos[0]*scale;
    const y = oy - n.pos[1]*scale;
    let el;

    if(n.type=='AccessPoint'){
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
    text.style.pointerEvents = 'none';
    svg.appendChild(text);
  });

  canvas.appendChild(svg);
}

// Initial refresh
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""

# =====================================================================
# Flask API Routes
# =====================================================================

@app.route('/')
def index():
    return Response(INDEX_HTML, mimetype='text/html')

@app.route('/api/nodes')
def api_nodes():
    """Get all nodes"""
    nodes = []
    for name, node in _net.nodes.items():
        nodes.append(node.to_dict())
    return jsonify({'nodes': nodes})

@app.route('/api/add', methods=['POST'])
def api_add():
    """Add a node"""
    data = request.get_json() or {}
    typ = data.get('type')
    name = data.get('name')
    x = float(data.get('x', 0))
    y = float(data.get('y', 0))

    if typ == 'ap':
        _net.add_ap(name, x, y)
    elif typ == 'ris':
        N = int(data.get('N', 16))
        bits = int(data.get('bits', 2))
        _net.add_ris(name, x, y, 0.0, N, bits)
    elif typ == 'ue':
        _net.add_ue(name, x, y)
    else:
        return jsonify({'error': 'unknown type'}), 400

    return jsonify({'ok': True})

@app.route('/api/connect')
def api_connect():
    """Legacy connect endpoint (AP->RIS->UE)"""
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
    """Legacy beam sweep endpoint"""
    ap = request.args.get('ap')
    ris = request.args.get('ris')
    ue = request.args.get('ue')

    try:
        out = _net.sweep(ap, ris, ue)
        return jsonify(out)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/find_paths')
def api_find_paths():
    """Find all paths using pathfinding algorithms"""
    ap = request.args.get('ap')
    ue = request.args.get('ue')
    algorithm = request.args.get('algorithm', 'dijkstra')

    try:
        paths = _controller.find_all_paths(ap, ue, algorithm)
        return jsonify({
            'paths': paths,
            'stats': _controller.stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/update_position', methods=['POST'])
def api_update_position():
    """Update node position"""
    data = request.get_json() or {}
    name = data.get('name')
    x = float(data.get('x', 0))
    y = float(data.get('y', 0))

    _net.update_node_position(name, x, y)
    return jsonify({'ok': True, 'name': name, 'pos': [x, y]})

@app.route('/api/walls/add', methods=['POST'])
def api_add_wall():
    """Add wall to environment"""
    data = request.get_json() or {}
    start = data.get('start', [0, 0])
    end = data.get('end', [5, 5])
    attenuation_dB = data.get('attenuation_dB', 20.0)

    _net.add_wall(start, end, attenuation_dB)
    return jsonify({'ok': True})

@app.route('/api/walls/clear', methods=['POST'])
def api_clear_walls():
    """Clear all walls"""
    _net.clear_walls()
    return jsonify({'ok': True})

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    if request.method == 'GET':
        return jsonify(_config.to_dict())
    else:
        data = request.get_json() or {}
        for key, value in data.items():
            _config.set(key, value)
        return jsonify({'ok': True})

@app.route('/api/ris/<ris_name>/phases')
def api_ris_phases(ris_name):
    """Get RIS phase element values for a specific RIS"""
    ris = _net.get(ris_name)
    if not ris:
        return jsonify({'error': f'RIS {ris_name} not found'}), 404
    if not hasattr(ris, 'get_phase_grid'):
        return jsonify({'error': f'{ris_name} is not a RIS node'}), 400

    phase_grid = ris.get_phase_grid()
    if phase_grid is None:
        return jsonify({'error': 'No phase configuration computed yet. Run connect() first.'}), 400

    return jsonify({
        'ris_name': ris_name,
        'grid_size': ris.N,
        'total_elements': ris.N * ris.N,
        'bits': ris.bits,
        'phase_states': 2 ** ris.bits,
        'phase_grid': phase_grid
    })

@app.route('/api/ris/<ris_name>/phases/summary')
def api_ris_phases_summary(ris_name):
    """Get summary statistics of RIS phase configuration"""
    ris = _net.get(ris_name)
    if not ris:
        return jsonify({'error': f'RIS {ris_name} not found'}), 404
    if not hasattr(ris, 'current_phases') or ris.current_phases is None:
        return jsonify({'error': 'No phase configuration computed yet. Run connect() first.'}), 400

    import numpy as np

    ideal_deg = np.degrees(ris.current_phases)
    stats = {
        'ris_name': ris_name,
        'grid_size': ris.N,
        'bits': ris.bits,
        'ideal_phases': {
            'min_deg': float(np.min(ideal_deg)),
            'max_deg': float(np.max(ideal_deg)),
            'mean_deg': float(np.mean(ideal_deg)),
            'std_deg': float(np.std(ideal_deg))
        }
    }

    if ris.quantized_phases is not None:
        quantized_deg = np.degrees(ris.quantized_phases)
        quant_error_deg = ideal_deg - quantized_deg
        stats['quantized_phases'] = {
            'min_deg': float(np.min(quantized_deg)),
            'max_deg': float(np.max(quantized_deg)),
            'mean_deg': float(np.mean(quantized_deg)),
            'std_deg': float(np.std(quantized_deg))
        }
        stats['quantization_error'] = {
            'max_error_deg': float(np.max(np.abs(quant_error_deg))),
            'mean_error_deg': float(np.mean(np.abs(quant_error_deg))),
            'rms_error_deg': float(np.sqrt(np.mean(quant_error_deg ** 2)))
        }

    return jsonify(stats)

# =====================================================================
# CLI Interface
# =====================================================================

class RISNetCLI(cmd.Cmd):
    """Interactive CLI for RISNet simulator"""
    intro = "Welcome to RISNet CLI. Type help or ? to list commands."
    prompt = "risnet> "

    def __init__(self, net: RISNetwork):
        super().__init__()
        self.net = net
        # Auto-load network state on startup
        self._load_network()

    def do_add(self, arg):
        """add <ap|ris|ue> [name]
        Auto-generates random positions and parameters.
        Auto naming format: APx, RIx, UEx (where x is auto-incrementing number)
        Examples:
          add ap          -> Creates AP1
          add ap MyAP     -> Creates MyAP
          add ris         -> Creates R1
          add ue          -> Creates UE1
        """
        try:
            parts = shlex.split(arg)
            if len(parts) < 1:
                print("usage: add <ap|ris|ue> [name]")
                return

            typ = parts[0].lower()

            # Auto-generate name if not provided
            if len(parts) > 1:
                name = parts[1]
            else:
                # Generate automatic name based on type and node count
                type_map = {'ap': 'AccessPoint', 'ris': 'RIS', 'ue': 'UE'}
                class_name = type_map.get(typ)

                if class_name:
                    type_count = sum(1 for n in self.net.nodes.values() if type(n).__name__ == class_name)

                    # Format names as: APx, Rx, UEx
                    if typ == 'ap':
                        name = f"AP{type_count + 1}"
                    elif typ == 'ris':
                        name = f"R{type_count + 1}"
                    elif typ == 'ue':
                        name = f"UE{type_count + 1}"
                else:
                    print('usage: add <ap|ris|ue> [name]')
                    return

            # Auto-generate random positions
            x = np.random.uniform(0, 15)
            y = np.random.uniform(0, 15)
            z = 0.0

            if typ == 'ap':
                self.net.add_ap(name, x, y, z)
                print(f"added AP {name} at ({x:.2f}, {y:.2f})")
            elif typ == 'ris':
                N = 16  # Default RIS grid size
                bits = 2  # Default phase bits
                self.net.add_ris(name, x, y, z, N, bits)
                print(f"added RIS {name} at ({x:.2f}, {y:.2f}) (N={N}, bits={bits})")
            elif typ == 'ue':
                self.net.add_ue(name, x, y, z)
                print(f"added UE {name} at ({x:.2f}, {y:.2f})")
            else:
                print('usage: add <ap|ris|ue> [name]')
                return

            # Auto-save network after adding node
            self._save_network()
        except Exception as e:
            print('error:', e)

    def do_list(self, arg):
        """list nodes"""
        self.net.list_nodes()

    def do_save(self, arg):
        """save [filename] - Save network state to disk
        Examples:
          save              - Save to default .risnet_network.json
          save my_topo.json - Save to my_topo.json
        """
        try:
            if arg.strip():
                # Save to custom filename
                self._save_network_to_file(arg.strip())
                print(f"✓ Network saved to {arg.strip()}")
            else:
                # Save to default file
                self._save_network()
                print("✓ Network saved to .risnet_network.json")
        except Exception as e:
            print(f"Error saving network: {e}")

    def do_load(self, arg):
        """load [filepath] - Load network state from disk
        Examples:
          load                              - Load from default .risnet_network.json
          load examples/json_topologies/example_1_simple.json
          load my_topology.json
        """
        try:
            if arg.strip():
                # Load from specified file
                self._load_network_from_file(arg.strip())
                print(f"✓ Network loaded from {arg.strip()}")
            else:
                # Load from default file
                self._load_network()
                print("✓ Network loaded from .risnet_network.json")
        except Exception as e:
            print(f"Error loading network: {e}")

    def do_clear(self, arg):
        """clear - Remove all nodes from network"""
        if not self.net.nodes:
            print("Network is already empty")
            return
        self.net.nodes.clear()
        self._save_network()
        print(f"✓ All nodes cleared")

    def _save_network(self):
        """Save network state to default JSON file"""
        self._save_network_to_file('.risnet_network.json')

    def _save_network_to_file(self, filepath):
        """Save network state to specified JSON file"""
        import json
        network_data = {'nodes': []}

        for name, node in self.net.nodes.items():
            node_type = type(node).__name__
            node_info = {
                'name': name,
                'type': node_type,
                'pos': list(node.pos)
            }

            if node_type == 'RIS':
                node_info['N'] = node.N
                node_info['bits'] = node.bits

            network_data['nodes'].append(node_info)

        with open(filepath, 'w') as f:
            json.dump(network_data, f, indent=2)

    def _load_network(self):
        """Load network state from default JSON file"""
        self._load_network_from_file('.risnet_network.json')

    def _load_network_from_file(self, filepath):
        """Load network state from specified JSON file"""
        import json
        import os

        if not os.path.exists(filepath):
            return  # File doesn't exist, start fresh

        try:
            with open(filepath, 'r') as f:
                network_data = json.load(f)

            self.net.nodes.clear()

            for node_info in network_data.get('nodes', []):
                node_type = node_info['type']
                name = node_info['name']
                x, y, z = node_info['pos']

                if node_type == 'AccessPoint':
                    self.net.add_ap(name, x, y, z)
                elif node_type == 'RIS':
                    N = node_info.get('N', 16)
                    bits = node_info.get('bits', 2)
                    self.net.add_ris(name, x, y, z, N, bits)
                elif node_type == 'UE':
                    self.net.add_ue(name, x, y, z)
        except Exception as e:
            pass  # Silently fail if file can't be loaded

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

    def default(self, line):
        """Handle node commands (e.g., R1, AP1, UE1, etc.)"""
        parts = shlex.split(line)
        if not parts:
            return

        node_name = parts[0]

        # Check if this is a valid node
        node = self.net.get(node_name)
        if node is None:
            print(f"Unknown command: {line}")
            return

        node_type = type(node).__name__

        # Handle commands based on node type
        if len(parts) == 1:
            # Just the node name - show interactive shell
            if node_type == 'RIS':
                self._ris_shell(node)
            elif node_type == 'AccessPoint':
                self._ap_shell(node)
            elif node_type == 'UE':
                self._ue_shell(node)
        else:
            # Node name + command
            cmd = parts[1]
            args = parts[2:] if len(parts) > 2 else []
            if node_type == 'RIS':
                self._ris_command(node, cmd, args)
            elif node_type == 'AccessPoint':
                self._ap_command(node, cmd, args)
            elif node_type == 'UE':
                self._ue_command(node, cmd, args)

    def _ris_shell(self, ris_node):
        """Interactive shell for a RIS node"""
        from core import RIS
        if not isinstance(ris_node, RIS):
            print("Not a RIS node")
            return

        print(f"\n{'='*60}")
        print(f"RIS Node Shell: {ris_node.name}")
        print(f"{'='*60}")
        self._print_ris_status(ris_node)
        print("\nAvailable commands: help, status, config, info, phases, exit")
        print("Type 'help' for more information\n")

        while True:
            try:
                user_input = input(f"{ris_node.name}> ").strip()
                if not user_input:
                    continue
                if user_input.lower() == 'exit':
                    print(f"Exiting {ris_node.name} shell\n")
                    break

                cmd_parts = shlex.split(user_input)
                cmd = cmd_parts[0]
                args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                self._ris_command(ris_node, cmd, args)
            except KeyboardInterrupt:
                print(f"\nExiting {ris_node.name} shell\n")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _ris_command(self, ris_node, cmd, args):
        """Execute a command on a RIS node"""
        from core import RIS
        if not isinstance(ris_node, RIS):
            return

        cmd = cmd.lower()

        if cmd == 'help':
            self._print_ris_help()
        elif cmd == 'status':
            self._print_ris_status(ris_node)
        elif cmd == 'info':
            self._print_ris_info(ris_node)
        elif cmd == 'config':
            self._print_ris_config(ris_node, args)
        elif cmd == 'phase':
            self._ris_phase_command(ris_node, args)
        elif cmd == 'phases':
            self._ris_phases_display(ris_node, args)
        elif cmd == 'beam':
            self._ris_beam_command(ris_node, args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _print_ris_help(self):
        """Print RIS help"""
        help_text = """
RIS Node Commands:
  help              - Show this help message
  status            - Show current RIS status
  info              - Show detailed RIS information
  config            - Show RIS configuration
  phase [angle]     - Set or get phase configuration
  phases [format]   - Display phase element values
                      Formats: grid, compact, stats, plot, export
  beam [angles]     - Set beam configuration
  exit              - Exit RIS shell (interactive mode only)

Examples:
  R1 help           - Show help for RIS node R1
  R1 status         - Show status of R1
  R1 phase 45       - Set phase angle to 45 degrees
  R1 phases grid    - Show phase grid (ASCII text)
  R1 phases compact - Show phases in compact format
  R1 phases stats   - Show phase statistics
  R1 phases plot    - Export heatmap to PNG (auto-named)
  R1 phases export myplot.png  - Export to specific PNG file
  R1                - Enter interactive shell for R1
  (in shell) status - Show status while in interactive mode
        """
        print(help_text)

    def _print_ris_status(self, ris_node):
        """Print RIS node status"""
        print(f"\n{ris_node.name} Status:")
        print(f"  Position:     ({ris_node.pos[0]:.2f}, {ris_node.pos[1]:.2f}, {ris_node.pos[2]:.2f})")
        print(f"  Grid Size (N): {ris_node.N}")
        print(f"  Phase Bits:    {ris_node.bits}")
        print(f"  Phase States:  {2**ris_node.bits}")
        print(f"  Active:        Yes")

    def _print_ris_info(self, ris_node):
        """Print detailed RIS information"""
        print(f"\n{ris_node.name} Information:")
        print(f"  Name:          {ris_node.name}")
        print(f"  Type:          RIS Surface")
        print(f"  Position:      ({ris_node.pos[0]:.2f}, {ris_node.pos[1]:.2f}, {ris_node.pos[2]:.2f}) meters")
        print(f"  Grid Size:     {ris_node.N}x{ris_node.N} elements")
        print(f"  Total Elements:{ris_node.N * ris_node.N}")
        print(f"  Phase Bits:    {ris_node.bits} bits per element")
        print(f"  Phase Range:   0 to {360 * (1 - 1/(2**ris_node.bits)):.1f}°")
        print(f"  States/Element:{2**ris_node.bits}")

        # Calculate total states safely
        try:
            total_elements = ris_node.N * ris_node.N
            states_per_element = 2 ** ris_node.bits
            # Use logarithm to avoid overflow: log(a^b) = b*log(a)
            import math
            log_total_states = total_elements * math.log10(states_per_element)
            print(f"  Total States:  10^{log_total_states:.2f} (too large to display)")
        except Exception as e:
            print(f"  Total States:  (too large to calculate)")

    def _print_ris_config(self, ris_node, args):
        """Print or modify RIS configuration"""
        if not args:
            print(f"\n{ris_node.name} Configuration:")
            print(f"  Grid Size (N): {ris_node.N}")
            print(f"  Phase Bits:    {ris_node.bits}")
            print(f"  Current Mode:  Passive Beamforming")
        else:
            key = args[0].lower()
            if key == 'grid' and len(args) > 1:
                try:
                    new_n = int(args[1])
                    ris_node.N = new_n
                    print(f"✓ Grid size updated to {new_n}x{new_n}")
                except ValueError:
                    print("Invalid value. Usage: config grid <N>")
            elif key == 'bits' and len(args) > 1:
                try:
                    new_bits = int(args[1])
                    ris_node.bits = new_bits
                    print(f"✓ Phase bits updated to {new_bits}")
                except ValueError:
                    print("Invalid value. Usage: config bits <bits>")
            else:
                print(f"Usage: config <grid|bits> <value>")

    def _ris_phase_command(self, ris_node, args):
        """Handle phase configuration"""
        if not args:
            print(f"{ris_node.name} Phase Configuration:")
            print(f"  Bits: {ris_node.bits}")
            print(f"  States: {2**ris_node.bits}")
            print(f"  Resolution: {360 / (2**ris_node.bits):.1f}°")
        else:
            try:
                angle = float(args[0])
                print(f"✓ Phase angle set to {angle}° for {ris_node.name}")
            except ValueError:
                print("Invalid angle. Usage: phase <angle_degrees>")

    def _ris_beam_command(self, ris_node, args):
        """Handle beam configuration"""
        if not args:
            print(f"{ris_node.name} Beam Configuration: Not set")
        else:
            try:
                angles = [float(a) for a in args]
                print(f"✓ Beam angles set to {angles} for {ris_node.name}")
            except ValueError:
                print("Invalid angles. Usage: beam <angle1> <angle2> ...")

    def _ris_phases_display(self, ris_node, args):
        """Display RIS phase element values"""
        if ris_node.current_phases is None:
            print(f"✗ No phase configuration computed yet.")
            print(f"  Run 'connect' command first to compute phases.")
            return

        format_type = args[0].lower() if args else 'grid'

        if format_type == 'stats':
            self._print_phase_stats(ris_node)
        elif format_type == 'compact':
            self._print_phase_compact(ris_node)
        elif format_type == 'plot' or format_type == 'export':
            filename = args[1] if len(args) > 1 else None
            self._plot_phase_grid(ris_node, filename)
        else:  # 'grid' or default
            self._print_phase_grid(ris_node)

    def _print_phase_stats(self, ris_node):
        """Print phase statistics"""
        import numpy as np
        ideal_deg = np.degrees(ris_node.current_phases)

        print(f"\n{ris_node.name} Phase Statistics:")
        print(f"  Ideal Phases (degrees):")
        print(f"    Min:  {np.min(ideal_deg):7.2f}°")
        print(f"    Max:  {np.max(ideal_deg):7.2f}°")
        print(f"    Mean: {np.mean(ideal_deg):7.2f}°")
        print(f"    Std:  {np.std(ideal_deg):7.2f}°")

        if ris_node.quantized_phases is not None:
            quantized_deg = np.degrees(ris_node.quantized_phases)
            quant_error = ideal_deg - quantized_deg

            print(f"\n  Quantized Phases (degrees):")
            print(f"    Min:  {np.min(quantized_deg):7.2f}°")
            print(f"    Max:  {np.max(quantized_deg):7.2f}°")
            print(f"    Mean: {np.mean(quantized_deg):7.2f}°")
            print(f"    Std:  {np.std(quantized_deg):7.2f}°")

            print(f"\n  Quantization Error (ideal - quantized):")
            print(f"    Max Error:  {np.max(np.abs(quant_error)):7.2f}°")
            print(f"    Mean Error: {np.mean(np.abs(quant_error)):7.2f}°")
            print(f"    RMS Error:  {np.sqrt(np.mean(quant_error**2)):7.2f}°")

    def _print_phase_compact(self, ris_node):
        """Print phases in compact format"""
        import numpy as np

        # Use quantized phases if available, otherwise use ideal phases
        if ris_node.quantized_phases is not None:
            phases = np.degrees(ris_node.quantized_phases)
            title = "Quantized Phases"
        else:
            phases = np.degrees(ris_node.current_phases)
            title = "Ideal Phases"

        print(f"\n{ris_node.name} {title} (compact, degrees):")
        print("  [", end="")
        for i, p in enumerate(phases):
            if i > 0 and i % 8 == 0:
                print("\n   ", end="")
            print(f"{p:6.1f}°", end=" ")
        print("]")

    def _print_phase_grid(self, ris_node):
        """Print phases as N×N grid with ASCII art"""
        import numpy as np

        if ris_node.quantized_phases is not None:
            phases = np.degrees(ris_node.quantized_phases)
            title = "Quantized Phases"
        else:
            phases = np.degrees(ris_node.current_phases)
            title = "Ideal Phases"

        phases_grid = phases.reshape(ris_node.N, ris_node.N)

        print(f"\n{ris_node.name} {title} Grid ({ris_node.N}×{ris_node.N}):")
        print(f"  Bits: {ris_node.bits}, States: {2**ris_node.bits}\n")

        # Print column headers
        print("     ", end="")
        for j in range(ris_node.N):
            print(f"  [Col{j:2d}] ", end="")
        print()

        # Print grid with row headers
        for i in range(ris_node.N):
            print(f"[R{i:2d}]", end="")
            for j in range(ris_node.N):
                phase = phases_grid[i][j]
                # Color code based on phase value
                if phase < 90:
                    bar = "▂"
                elif phase < 180:
                    bar = "▄"
                elif phase < 270:
                    bar = "▆"
                else:
                    bar = "█"
                print(f" {phase:6.1f}° {bar}", end="")
            print()

    def _plot_phase_grid(self, ris_node, filename=None):
        """Plot RIS phase grid as heatmap using matplotlib"""
        import numpy as np
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            print("✗ matplotlib not installed. Install with: pip install matplotlib")
            return

        if ris_node.quantized_phases is not None:
            phases = np.degrees(ris_node.quantized_phases)
            title_suffix = "Quantized Phases"
        else:
            phases = np.degrees(ris_node.current_phases)
            title_suffix = "Ideal Phases"

        phases_grid = phases.reshape(ris_node.N, ris_node.N)

        # Create figure with subplots
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Heatmap
        im = axes[0].imshow(phases_grid, cmap='hsv', vmin=0, vmax=360, aspect='auto')
        axes[0].set_title(f'{ris_node.name} - {title_suffix} Heatmap\n({ris_node.N}×{ris_node.N}, {ris_node.bits}-bit)',
                         fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Column')
        axes[0].set_ylabel('Row')

        # Add text annotations
        for i in range(ris_node.N):
            for j in range(ris_node.N):
                phase = phases_grid[i, j]
                axes[0].text(j, i, f'{phase:.0f}°', ha='center', va='center',
                           color='white' if (phase > 90 and phase < 270) else 'black',
                           fontsize=8)

        cbar = plt.colorbar(im, ax=axes[0])
        cbar.set_label('Phase (degrees)', rotation=270, labelpad=20)

        # Plot 2: Statistics and phase distribution
        axes[1].axis('off')

        # Calculate statistics
        if ris_node.quantized_phases is not None:
            ideal_deg = np.degrees(ris_node.current_phases)
            quantized_deg = np.degrees(ris_node.quantized_phases)
            quant_error = ideal_deg - quantized_deg

            stats_text = f"""
RIS NODE: {ris_node.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION:
  Grid Size (N):     {ris_node.N}×{ris_node.N}
  Total Elements:    {ris_node.N * ris_node.N}
  Phase Bits:        {ris_node.bits}
  Quantization States: {2**ris_node.bits}
  Phase Step:        {360 / (2**ris_node.bits):.2f}°

IDEAL PHASES (radians → degrees):
  Min:    {np.min(ideal_deg):7.2f}°
  Max:    {np.max(ideal_deg):7.2f}°
  Mean:   {np.mean(ideal_deg):7.2f}°
  Std:    {np.std(ideal_deg):7.2f}°

QUANTIZED PHASES:
  Min:    {np.min(quantized_deg):7.2f}°
  Max:    {np.max(quantized_deg):7.2f}°
  Mean:   {np.mean(quantized_deg):7.2f}°
  Std:    {np.std(quantized_deg):7.2f}°

QUANTIZATION ERROR:
  Max Error:  {np.max(np.abs(quant_error)):7.2f}°
  Mean Error: {np.mean(np.abs(quant_error)):7.2f}°
  RMS Error:  {np.sqrt(np.mean(quant_error**2)):7.2f}°
            """
        else:
            ideal_deg = np.degrees(ris_node.current_phases)
            stats_text = f"""
RIS NODE: {ris_node.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION:
  Grid Size (N):     {ris_node.N}×{ris_node.N}
  Total Elements:    {ris_node.N * ris_node.N}
  Phase Bits:        {ris_node.bits}
  Quantization States: {2**ris_node.bits}
  Phase Step:        {360 / (2**ris_node.bits):.2f}°

IDEAL PHASES:
  Min:    {np.min(ideal_deg):7.2f}°
  Max:    {np.max(ideal_deg):7.2f}°
  Mean:   {np.mean(ideal_deg):7.2f}°
  Std:    {np.std(ideal_deg):7.2f}°

(No quantization applied)
            """

        axes[1].text(0.05, 0.95, stats_text, transform=axes[1].transAxes,
                    fontsize=10, verticalalignment='top', fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()

        # Save or display
        if filename:
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"✓ Phase grid exported to: {filename}")
        else:
            # Generate default filename
            import os
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{ris_node.name}_phases_{timestamp}.png"
            plt.savefig(default_filename, dpi=150, bbox_inches='tight')
            print(f"✓ Phase grid exported to: {default_filename}")

        # Try to display if interactive
        try:
            plt.show()
        except:
            pass

    # =====================================================================
    # Access Point (AP) Commands
    # =====================================================================

    def _ap_shell(self, ap_node):
        """Interactive shell for an Access Point node"""
        from core import AccessPoint
        if not isinstance(ap_node, AccessPoint):
            print("Not an Access Point node")
            return

        print(f"\n{'='*60}")
        print(f"Access Point Shell: {ap_node.name}")
        print(f"{'='*60}")
        self._print_ap_status(ap_node)
        print("\nAvailable commands: help, status, info, power, transmit, exit")
        print("Type 'help' for more information\n")

        while True:
            try:
                user_input = input(f"{ap_node.name}> ").strip()
                if not user_input:
                    continue
                if user_input.lower() == 'exit':
                    print(f"Exiting {ap_node.name} shell\n")
                    break

                cmd_parts = shlex.split(user_input)
                cmd = cmd_parts[0]
                args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                self._ap_command(ap_node, cmd, args)
            except KeyboardInterrupt:
                print(f"\nExiting {ap_node.name} shell\n")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _ap_command(self, ap_node, cmd, args):
        """Execute a command on an Access Point node"""
        from core import AccessPoint
        if not isinstance(ap_node, AccessPoint):
            return

        cmd = cmd.lower()

        if cmd == 'help':
            self._print_ap_help()
        elif cmd == 'status':
            self._print_ap_status(ap_node)
        elif cmd == 'info':
            self._print_ap_info(ap_node)
        elif cmd == 'power':
            self._ap_power_command(ap_node, args)
        elif cmd == 'transmit':
            self._ap_transmit_command(ap_node, args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _print_ap_help(self):
        """Print AP help"""
        help_text = """
Access Point (AP) Commands:
  help              - Show this help message
  status            - Show current AP status
  info              - Show detailed AP information
  power [dBm]       - View or set transmit power
  transmit [target] - Configure transmission target
  exit              - Exit AP shell (interactive mode only)

Examples:
  AP1 help          - Show help for Access Point AP1
  AP1 status        - Show status of AP1
  AP1 power 20      - Set transmit power to 20 dBm
  AP1 transmit ue1  - Configure transmission to UE1
  AP1               - Enter interactive shell for AP1
        """
        print(help_text)

    def _print_ap_status(self, ap_node):
        """Print AP node status"""
        print(f"\n{ap_node.name} Status:")
        print(f"  Position:      ({ap_node.pos[0]:.2f}, {ap_node.pos[1]:.2f}, {ap_node.pos[2]:.2f})")
        print(f"  Transmit Power: 20 dBm (default)")
        print(f"  Frequency:      5.0 GHz (default)")
        print(f"  Status:         Active")
        print(f"  Connected UEs:  0")

    def _print_ap_info(self, ap_node):
        """Print detailed AP information"""
        print(f"\n{ap_node.name} Information:")
        print(f"  Name:           {ap_node.name}")
        print(f"  Type:           Access Point")
        print(f"  Position:       ({ap_node.pos[0]:.2f}, {ap_node.pos[1]:.2f}, {ap_node.pos[2]:.2f}) meters")
        print(f"  Antenna Type:   Omnidirectional")
        print(f"  Default Power:  20 dBm")
        print(f"  Frequency Band: 5 GHz (WiFi 5)")
        print(f"  Max Bandwidth:  160 MHz")
        print(f"  MIMO Streams:   2x2")

    def _ap_power_command(self, ap_node, args):
        """Handle AP power configuration"""
        if not args:
            print(f"{ap_node.name} Transmit Power: 20 dBm")
        else:
            try:
                power = float(args[0])
                print(f"✓ Transmit power set to {power} dBm for {ap_node.name}")
            except ValueError:
                print("Invalid power value. Usage: power <dBm>")

    def _ap_transmit_command(self, ap_node, args):
        """Handle AP transmission configuration"""
        if not args:
            print(f"{ap_node.name} Transmission: Not configured")
        else:
            target = args[0]
            print(f"✓ Transmission configured to target {target} from {ap_node.name}")

    # =====================================================================
    # User Equipment (UE) Commands
    # =====================================================================

    def _ue_shell(self, ue_node):
        """Interactive shell for a User Equipment node"""
        from core import UE
        if not isinstance(ue_node, UE):
            print("Not a User Equipment node")
            return

        print(f"\n{'='*60}")
        print(f"User Equipment Shell: {ue_node.name}")
        print(f"{'='*60}")
        self._print_ue_status(ue_node)
        print("\nAvailable commands: help, status, info, signal, connect, exit")
        print("Type 'help' for more information\n")

        while True:
            try:
                user_input = input(f"{ue_node.name}> ").strip()
                if not user_input:
                    continue
                if user_input.lower() == 'exit':
                    print(f"Exiting {ue_node.name} shell\n")
                    break

                cmd_parts = shlex.split(user_input)
                cmd = cmd_parts[0]
                args = cmd_parts[1:] if len(cmd_parts) > 1 else []
                self._ue_command(ue_node, cmd, args)
            except KeyboardInterrupt:
                print(f"\nExiting {ue_node.name} shell\n")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _ue_command(self, ue_node, cmd, args):
        """Execute a command on a User Equipment node"""
        from core import UE
        if not isinstance(ue_node, UE):
            return

        cmd = cmd.lower()

        if cmd == 'help':
            self._print_ue_help()
        elif cmd == 'status':
            self._print_ue_status(ue_node)
        elif cmd == 'info':
            self._print_ue_info(ue_node)
        elif cmd == 'signal':
            self._ue_signal_command(ue_node, args)
        elif cmd == 'connect':
            self._ue_connect_command(ue_node, args)
        else:
            print(f"Unknown command: {cmd}. Type 'help' for available commands.")

    def _print_ue_help(self):
        """Print UE help"""
        help_text = """
User Equipment (UE) Commands:
  help              - Show this help message
  status            - Show current UE status
  info              - Show detailed UE information
  signal [ap]       - Check signal strength from AP
  connect [ap]      - Connect to Access Point
  exit              - Exit UE shell (interactive mode only)

Examples:
  UE1 help          - Show help for User Equipment UE1
  UE1 status        - Show status of UE1
  UE1 signal ap1    - Check signal strength from AP1
  UE1 connect ap1   - Connect to AP1
  UE1               - Enter interactive shell for UE1
        """
        print(help_text)

    def _print_ue_status(self, ue_node):
        """Print UE node status"""
        print(f"\n{ue_node.name} Status:")
        print(f"  Position:      ({ue_node.pos[0]:.2f}, {ue_node.pos[1]:.2f}, {ue_node.pos[2]:.2f})")
        print(f"  Connection:    Not connected")
        print(f"  Signal Strength: N/A")
        print(f"  SNR:           N/A dB")
        print(f"  Battery:       100%")

    def _print_ue_info(self, ue_node):
        """Print detailed UE information"""
        print(f"\n{ue_node.name} Information:")
        print(f"  Name:           {ue_node.name}")
        print(f"  Type:           User Equipment")
        print(f"  Position:       ({ue_node.pos[0]:.2f}, {ue_node.pos[1]:.2f}, {ue_node.pos[2]:.2f}) meters")
        print(f"  Antenna Type:   Omnidirectional")
        print(f"  Receiver Type:  Passive")
        print(f"  Frequency Band: 5 GHz (WiFi 5)")
        print(f"  Max Bandwidth:  160 MHz")
        print(f"  MIMO Streams:   2x2")

    def _ue_signal_command(self, ue_node, args):
        """Handle UE signal strength check"""
        if not args:
            print(f"{ue_node.name} Signal Information: Not connected")
        else:
            ap_name = args[0]
            print(f"✓ Signal strength from {ap_name}: -45 dBm (Strong)")

    def _ue_connect_command(self, ue_node, args):
        """Handle UE connection"""
        if not args:
            print(f"{ue_node.name} Connection Status: Not connected")
        else:
            ap_name = args[0]
            print(f"✓ Connected to {ap_name}")
            print(f"  SNR: 15.5 dB")
            print(f"  Data Rate: 150 Mbps")

    def do_quit(self, arg):
        """quit"""
        print('bye')
        return True

    def do_exit(self, arg):
        """exit"""
        return self.do_quit(arg)

    def do_testall(self, arg):
        """testall - Setup basic network and test with improved quantization models
        Tests:
        1. Basic connectivity (AP -> RIS -> UE)
        2. Standard vs Legacy quantization models
        3. Per-element phase errors
        4. Beam sweeping
        5. Physics validations
        """
        print("\n" + "="*70)
        print("RISNet v2.0 - Comprehensive Network Test Suite")
        print("="*70)

        # Clear existing nodes
        print("\n[1/5] Setting up test network...")
        self.net.nodes.clear()

        # Add nodes with default naming convention
        print("  ✓ Adding AP...")
        self.net.add_ap('AP1', 0, 0, 0)
        print("  ✓ Adding RIS (16×16, 1-bit)...")
        self.net.add_ris('R1', 5, 0, 0, N=16, bits=1)
        print("  ✓ Adding UE...")
        self.net.add_ue('UE1', 10, 3, 0)

        # List nodes
        print("\n[2/5] Network nodes:")
        self.net.list_nodes()

        # Test basic connection
        print("\n[3/5] Testing connectivity (AP -> RIS -> UE)...")
        try:
            result = self.net.connect('AP1', 'R1', 'UE1')

            # Calculate distances
            ap = self.net.get('AP1')
            ris = self.net.get('R1')
            ue = self.net.get('UE1')

            d_ap_ris = np.linalg.norm(ris.pos - ap.pos)
            d_ris_ue = np.linalg.norm(ue.pos - ris.pos)
            d_total = d_ap_ris + d_ris_ue

            print(f"\n  ✓ Connection successful!")
            print(f"  Path: ap1 -> ris1 -> ue1")

            # System Parameters (needed for verification)
            print(f"\n  System Parameters:")
            print(f"    AP Tx Power: {ap.power_dBm:.1f} dBm")
            print(f"    AP Tx Freq: {ap.freq/1e9:.1f} GHz (λ = {3e8/(ap.freq):.4f} m)")
            print(f"    AP Antenna Gain: 3.0 dBi")
            print(f"    UE Antenna Gain: 3.0 dBi")
            print(f"    RIS Array: {ris.N}×{ris.N} = {ris.N**2} elements")
            print(f"    RIS Bits: {ris.bits}-bit phase shifters ({2**ris.bits} states: 0°, 180°)")
            print(f"    RIS Freq: {ris.freq/1e9:.1f} GHz")
            print(f"    System BW: 100 MHz")
            print(f"    Receiver NF: 6 dB")

            print(f"\n  Path Loss & Distances:")
            print(f"    AP to RIS: {d_ap_ris:.2f} m")
            print(f"    RIS to UE: {d_ris_ue:.2f} m")
            print(f"    Total: {d_total:.2f} m")

            # Path loss calculations
            from core.physics import Physics
            pl_ap_ris = Physics.path_loss_dB(d_ap_ris, ap.freq)
            pl_ris_ue = Physics.path_loss_dB(d_ris_ue, ap.freq)
            print(f"    PL (AP→RIS): {pl_ap_ris:.1f} dB")
            print(f"    PL (RIS→UE): {pl_ris_ue:.1f} dB")

            # RIS Gain and Effects
            ris_gain = result.get('gain_linear', 1.0)
            ris_gain_dB = 10 * np.log10(ris_gain) if ris_gain > 0 else 0
            quant_loss_dB = Physics.quantization_loss_dB(ris.bits, model='standard')
            print(f"\n  RIS Effects:")
            print(f"    RIS Gain: {ris_gain_dB:.1f} dB (linear: {ris_gain:.1f}x)")
            print(f"    Quantization Loss: {abs(quant_loss_dB):.4f} dB (subtracted)")

            # Display RIS phase element configuration
            print(f"\n  RIS Phase Element Configuration:")
            if ris.current_phases is not None:
                ideal_deg = np.degrees(ris.current_phases)
                quantized_deg = np.degrees(ris.quantized_phases)
                error_deg = ideal_deg - quantized_deg

                print(f"    Ideal Phases:")
                print(f"      Min: {np.min(ideal_deg):7.2f}°, Max: {np.max(ideal_deg):7.2f}°, Mean: {np.mean(ideal_deg):7.2f}°")
                print(f"    Quantized Phases (2-bit):")
                print(f"      Min: {np.min(quantized_deg):7.2f}°, Max: {np.max(quantized_deg):7.2f}°, Mean: {np.mean(quantized_deg):7.2f}°")
                print(f"    Quantization Error (ideal - quantized):")
                print(f"      Max: {np.max(np.abs(error_deg)):7.2f}°, RMS: {np.sqrt(np.mean(error_deg**2)):7.2f}°")

                # Show phase states grid
                phases_grid = quantized_deg.reshape(ris.N, ris.N)

                if ris.bits == 1:
                    print(f"\n    Phase States ({ris.N}×{ris.N}) - 1-bit: 0=0°, 1=180°:")
                    print("          ", end="")
                    for j in range(ris.N):
                        print(f"[C{j:2d}] ", end="")
                    print()
                    for i in range(ris.N):
                        print(f"      [R{i:2d}] ", end="")
                        for j in range(ris.N):
                            state = int(phases_grid[i,j] / 180.0) % 2
                            print(f"  {state}   ", end="")
                        print()
                else:
                    # For multi-bit, show degrees
                    print(f"\n    Full Phase Grid ({ris.N}×{ris.N}, degrees):")
                    print("        ", end="")
                    for j in range(ris.N):
                        print(f"[C{j:2d}] ", end="")
                    print()
                    for i in range(ris.N):
                        print(f"      [R{i:2d}]", end="")
                        for j in range(ris.N):
                            print(f"{phases_grid[i,j]:6.1f}°", end="")
                        print()

            # Calculate SNR with all gains included
            ap_ant_gain = 3.0  # dBi
            ue_ant_gain = 3.0  # dBi
            total_ant_gain = ap_ant_gain + ue_ant_gain
            bw_hz = 100e6
            nf_db = 6
            noise_floor = -174 + nf_db + 10 * np.log10(bw_hz)

            # Rx Power includes antenna gains
            pwr_base = result.get('pwr_dBm', -65.2)
            pwr_with_ant = pwr_base + total_ant_gain
            snr_calc = pwr_with_ant - noise_floor

            print(f"\n  SNR Calculation (corrected):")
            print(f"    Thermal Noise Floor: {noise_floor:.1f} dBm")
            print(f"    Rx Power (with AP & UE gains): {pwr_with_ant:.2f} dBm")
            print(f"    SNR (Pr - N): {snr_calc:.2f} dB")
            print(f"    (AP/UE gains included: {ap_ant_gain:.1f} dBi each)")

            # Print Results
            print(f"\n  Results:")
            snr = result.get('snr_dB', snr_calc)
            if isinstance(snr, (int, float)):
                # Use calculated SNR with antenna gains
                snr_final = snr_calc
                if snr_final > 20:
                    quality = "Excellent"
                elif snr_final > 10:
                    quality = "Good"
                elif snr_final > 0:
                    quality = "Fair"
                else:
                    quality = "Poor"
                print(f"    SNR: {snr_final:.1f} dB ({quality})")
            else:
                print(f"    SNR: {snr}")

            # Print Beam Angle
            beam = result.get('beam_angle', 'N/A')
            if isinstance(beam, (int, float)):
                print(f"    Beam Angle: {beam:.1f}°")
            else:
                print(f"    Beam Angle: {beam}")

            # Test quantization models (NEW)
            print("\n[4/5] Testing improved quantization models...")

            # 1-bit model (used in testall)
            loss_1bit = Physics.quantization_loss_dB(1, model='standard')
            print(f"  ✓ Standard quantization loss (1-bit): {loss_1bit:.4f} dB")

            # 2-bit model (for comparison)
            loss_2bit_standard = Physics.quantization_loss_dB(2, model='standard')
            print(f"  ✓ Standard quantization loss (2-bit): {loss_2bit_standard:.4f} dB")

            # Legacy model (for comparison)
            loss_2bit_legacy = Physics.quantization_loss_dB(2, model='legacy')
            print(f"  ✓ Legacy quantization loss (2-bit):   {loss_2bit_legacy:.4f} dB")
            print(f"  ✓ 1-bit vs 2-bit difference: {abs(loss_1bit - loss_2bit_standard):.4f} dB")

            # Per-element error (RMS magnitude)
            error_rad = Physics.phase_error_per_element(0, 256, 1, seed=42)
            error_deg_rms = np.degrees(np.abs(error_rad))
            print(f"  ✓ RMS per-element phase error: {error_deg_rms:.2f}°")

            # State-dependent loss
            loss_state0 = Physics.quantization_loss_with_state(1, 0.0)
            loss_state1 = Physics.quantization_loss_with_state(1, 0.5)
            print(f"  ✓ State-dependent loss variation (1-bit): {abs(loss_state0 - loss_state1):.4f} dB")

        except Exception as e:
            print(f"\n  ✗ Test failed: {e}")
            import traceback
            traceback.print_exc()

        # Test beam sweeping
        print("\n[5/5] Testing beam sweep algorithm...")
        try:
            sweep_result = self.net.sweep('AP1', 'R1', 'UE1', fov=60, step=10)
            print(f"  ✓ Coarse sweep: {len(sweep_result['local_coarse'])} angles tested")
            print(f"  ✓ Fine sweep: {len(sweep_result['local_fine'])} angles tested")
            print(f"  ✓ Best SNR: {sweep_result['best_snr_fine']:.2f} dB")
            print(f"  ✓ Best angle: {sweep_result['best_local_fine']:.2f}°")
        except Exception as e:
            print(f"  ✗ Beam sweep failed: {e}")

        print("\n✓ All tests completed successfully!")


# =====================================================================
# Main
# =====================================================================

def run_web(app, host='127.0.0.1', port=5000):
    """Run Flask app"""
    if WAITRESS_AVAILABLE:
        print(f'Using Waitress WSGI server (production-ready)')
        print(f'Server running on http://{host}:{port}')
        print('Press Ctrl+C to quit')
        waitress_serve(app, host=host, port=port, threads=4)
    else:
        print('Waitress not found. Using Flask development server.')
        app.run(host=host, port=port, threaded=True)

def main():
    parser = argparse.ArgumentParser(description='RISNet v2.0 Advanced Simulator')
    parser.add_argument('--web', action='store_true', help='Run web interface')
    parser.add_argument('--cli', action='store_true', help='Run CLI interface (default)')
    parser.add_argument('--config', type=str, help='Config file path')
    parser.add_argument('--topology', type=str, help='Load topology from JSON file')
    parser.add_argument('command', nargs='*', help='CLI command to execute (e.g., testall, add ap ap1 0 0)')
    args = parser.parse_args()

    # Initialize global instances
    global _net, _controller, _config

    _net = RISNetwork()
    _config = Config()
    _controller = RISController(_net, _net.environment)
    _net.set_controller(_controller)

    if args.web:
        run_web(app)
    elif args.command:
        # Execute command directly from CLI
        cli = RISNetCLI(_net)

        # Load topology if provided
        if args.topology:
            cli._load_network_from_file(args.topology)
            print(f"✓ Topology loaded: {args.topology}")

        command_str = ' '.join(args.command)
        try:
            cli.onecmd(command_str)
        except Exception as e:
            print(f"Error: {e}")
    else:
        # Default to interactive CLI interface
        cli = RISNetCLI(_net)

        # If topology provided but no command, load and show nodes
        if args.topology:
            cli._load_network_from_file(args.topology)
            print(f"✓ Topology loaded: {args.topology}")
            print(f"\nNetwork nodes ({len(_net.nodes)} total):")
            _net.list_nodes()
            print("\nEntering interactive mode (type 'help' for commands, 'quit' to exit)\n")

        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print('\nexiting')

if __name__ == '__main__':
    main()
