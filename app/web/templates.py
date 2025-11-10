"""HTML templates for RISNet web interface"""

INDEX_HTML = r"""<!DOCTYPE html>
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

        <!-- Add Node Panel - Icon Drag & Drop -->
        <div class="bg-white rounded-lg shadow-lg p-4 mb-4">
          <h3 class="font-bold text-gray-800 mb-3">Add Nodes</h3>
          <p class="text-xs text-gray-600 mb-3">Drag icons to canvas or click to add:</p>
          <div class="flex gap-3 justify-around mb-4 p-3 bg-gray-50 rounded-lg">
            <!-- AP Icon -->
            <div draggable="true" ondragstart="dragStart(event, 'ap')" class="cursor-move p-3 bg-blue-100 rounded-lg hover:bg-blue-200 transition text-center" title="Drag to add Access Point">
              <div class="text-3xl">📡</div>
              <div class="text-xs font-medium text-gray-700 mt-1">AP</div>
            </div>
            <!-- RIS Icon -->
            <div draggable="true" ondragstart="dragStart(event, 'ris')" class="cursor-move p-3 bg-purple-100 rounded-lg hover:bg-purple-200 transition text-center" title="Drag to add RIS">
              <div class="text-3xl">🔷</div>
              <div class="text-xs font-medium text-gray-700 mt-1">RIS</div>
            </div>
            <!-- UE Icon -->
            <div draggable="true" ondragstart="dragStart(event, 'ue')" class="cursor-move p-3 bg-green-100 rounded-lg hover:bg-green-200 transition text-center" title="Drag to add User Equipment">
              <div class="text-3xl">📱</div>
              <div class="text-xs font-medium text-gray-700 mt-1">UE</div>
            </div>
          </div>

          <!-- Quick Add Panel -->
          <div class="bg-gray-50 rounded-lg p-3 border border-gray-200">
            <div class="text-xs font-medium text-gray-700 mb-2">Quick Add:</div>
            <div class="space-y-2">
              <div>
                <label class="text-xs text-gray-600">Name (auto: ap1, ris1, ue1...)</label>
                <input id="quick_add_name" placeholder="Leave blank for auto" class="w-full px-2 py-1 border border-gray-300 rounded text-sm" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="text-xs text-gray-600">X (m)</label>
                  <input id="quick_add_x" type="number" placeholder="0" class="w-full px-2 py-1 border border-gray-300 rounded text-sm" />
                </div>
                <div>
                  <label class="text-xs text-gray-600">Y (m)</label>
                  <input id="quick_add_y" type="number" placeholder="0" class="w-full px-2 py-1 border border-gray-300 rounded text-sm" />
                </div>
              </div>
              <div class="grid grid-cols-3 gap-2">
                <button type="button" onclick="quickAddNode('ap')" class="text-sm bg-blue-600 hover:bg-blue-700 text-white font-medium py-1 px-2 rounded">
                  + AP
                </button>
                <button type="button" onclick="quickAddNode('ris')" class="text-sm bg-purple-600 hover:bg-purple-700 text-white font-medium py-1 px-2 rounded">
                  + RIS
                </button>
                <button type="button" onclick="quickAddNode('ue')" class="text-sm bg-green-600 hover:bg-green-700 text-white font-medium py-1 px-2 rounded">
                  + UE
                </button>
              </div>
            </div>
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
          <div id="canvas" class="border-2 border-dashed border-gray-300 rounded bg-gray-50 hover:bg-gray-100 transition" style="width: 100%; height: 500px; cursor: grab; position: relative;" title="Drag nodes here to add them">
            <svg id="canvas-svg" style="width: 100%; height: 100%;"></svg>
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #999; font-size: 14px; pointer-events: none;">
              Drag node icons here or use Quick Add
            </div>
          </div>
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

<script src="/static/app.js"></script>
</body>
</html>
"""
