/**
 * RISNet Web Interface Logic
 */

// Global State
let state = {
    nodes: [],
    walls: [],
    paths: [],
    config: {},
    scale: 30, // px/m
    draggedType: null
};

// DOM Elements
const canvas = document.getElementById('canvas');
const canvasSvg = document.getElementById('canvas-svg');
const scaleInput = document.getElementById('scale');

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    console.log('RISNet Web Interface Loaded');

    // Initialize inputs
    if (scaleInput) {
        scaleInput.addEventListener('change', (e) => {
            state.scale = parseInt(e.target.value) || 30;
            renderNetwork();
        });
    }

    // Setup Canvas Drag & Drop
    canvas.addEventListener('dragover', (e) => e.preventDefault());
    canvas.addEventListener('drop', handleDrop);

    // Initial Data Fetch
    fetchConfig();
    fetchNodes();

    // Start polling for metrics
    setInterval(updateMetrics, 1000);
});

// ==========================================
// API Interactions
// ==========================================

async function fetchNodes() {
    try {
        const res = await fetch('/api/nodes');
        const data = await res.json();
        state.nodes = data.nodes || [];
        renderNetwork();
        updateSelects();
    } catch (e) {
        console.error('Error fetching nodes:', e);
    }
}

async function fetchConfig() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        state.config = data;

        // Update UI based on config
        if (data.controller) {
            document.getElementById('controller-enabled').checked = data.controller.enabled;
            document.getElementById('algorithm-select').value = data.controller.algorithm;
        }
    } catch (e) {
        console.error('Error fetching config:', e);
    }
}

async function addNode(type, x, y, name = null) {
    const payload = {
        type: type,
        x: x,
        y: y,
        z: 0
    };
    if (name) payload.name = name;

    // Add default params based on type
    if (type === 'ap') {
        payload.power_dBm = 20.0;
        payload.freq = 5.8e9;
    } else if (type === 'ris') {
        payload.N = 16;
        payload.bits = 2;
    }

    try {
        const res = await fetch('/api/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            logResult(`Added ${type.toUpperCase()}: ${data.node.name}`);
            fetchNodes();
        }
    } catch (e) {
        console.error('Error adding node:', e);
    }
}

async function updateNodePosition(name, x, y) {
    try {
        const res = await fetch('/api/update_position', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                x: x,
                y: y,
                z: 0
            })
        });
        fetchNodes();
    } catch (e) {
        console.error('Error updating position:', e);
    }
}

// ==========================================
// Actions
// ==========================================

function dragStart(event, type) {
    state.draggedType = type;
    event.dataTransfer.setData('text/plain', type);
}

function handleDrop(event) {
    event.preventDefault();
    const type = state.draggedType;
    if (!type) return;

    const rect = canvas.getBoundingClientRect();
    const x = (event.clientX - rect.left - rect.width / 2) / state.scale;
    const y = (event.clientY - rect.top - rect.height / 2) / state.scale; // Invert Y if needed, but let's keep standard cartesian? SVG y is down.
    // Actually, let's map SVG coordinates to simulation coordinates.
    // Center of canvas is (0,0).
    // SVG (0,0) is top-left.
    // Center is (width/2, height/2).
    // Sim X = (SVG_X - Width/2) / Scale
    // Sim Y = (SVG_Y - Height/2) / Scale  (Note: Sim Y usually up, SVG Y down. Let's assume Sim Y is down for now or invert)
    // Let's assume standard computer graphics: Y increases downwards.

    // Re-calculating based on SVG coordinate system center
    const svgX = event.clientX - rect.left;
    const svgY = event.clientY - rect.top;

    const simX = (svgX - rect.width / 2) / state.scale;
    const simY = (svgY - rect.height / 2) / state.scale;

    addNode(type, simX, simY);
    state.draggedType = null;
}

function quickAddNode(type) {
    const name = document.getElementById('quick_add_name').value;
    const x = parseFloat(document.getElementById('quick_add_x').value) || 0;
    const y = parseFloat(document.getElementById('quick_add_y').value) || 0;
    addNode(type, x, y, name);
}

async function connect() {
    const ap = document.getElementById('act_ap').value;
    const ris = document.getElementById('act_ris').value;
    const ue = document.getElementById('act_ue').value;

    if (!ap || !ue) {
        alert('AP and UE are required');
        return;
    }

    const url = `/api/connect?ap=${ap}&ue=${ue}` + (ris ? `&ris=${ris}` : '');

    try {
        const res = await fetch(url);
        const data = await res.json();
        if (data.error) {
            logResult('Error: ' + data.error);
        } else {
            logResult(JSON.stringify(data, null, 2));
            // Visualize connection?
            // For now just log
        }
    } catch (e) {
        logResult('Error connecting: ' + e);
    }
}

async function findPaths() {
    const ap = document.getElementById('act_ap').value;
    const ue = document.getElementById('act_ue').value;
    const algo = document.getElementById('algorithm-select').value;

    if (!ap || !ue) {
        alert('AP and UE are required');
        return;
    }

    try {
        const res = await fetch(`/api/find_paths?ap=${ap}&ue=${ue}&algorithm=${algo}`);
        const data = await res.json();

        if (data.error) {
            logResult('Error: ' + data.error);
        } else {
            state.paths = data.paths || [];
            renderNetwork(); // Will draw paths

            // Update stats
            document.getElementById('paths-found').innerText = state.paths.length;
            if (data.stats) {
                document.getElementById('decision-time').innerText = (data.stats.time_ms || 0).toFixed(2) + ' ms';
            }

            // List paths
            const list = document.getElementById('paths-list');
            list.innerHTML = state.paths.map((p, i) =>
                `<div class="p-2 border-b hover:bg-gray-50">
                    <strong>Path ${i + 1}:</strong> ${p.nodes.join(' → ')} 
                    <span class="text-green-600">SNR: ${p.snr_dB.toFixed(2)} dB</span>
                </div>`
            ).join('');

            logResult(`Found ${state.paths.length} paths`);
        }
    } catch (e) {
        logResult('Error finding paths: ' + e);
    }
}

async function sweep() {
    const ap = document.getElementById('act_ap').value;
    const ris = document.getElementById('act_ris').value;
    const ue = document.getElementById('act_ue').value;

    if (!ap || !ris || !ue) {
        alert('AP, RIS, and UE are required for sweep');
        return;
    }

    try {
        logResult('Sweeping...');
        const res = await fetch(`/api/sweep?ap=${ap}&ris=${ris}&ue=${ue}`);
        const data = await res.json();
        logResult(JSON.stringify(data, null, 2));
    } catch (e) {
        logResult('Error sweeping: ' + e);
    }
}

async function addWall() {
    // Simple wall for now: (-2, -2) to (2, 2)
    // In future, could add UI for coords
    try {
        await fetch('/api/walls/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start: [-2, -2],
                end: [2, 2],
                attenuation_dB: 20
            })
        });
        logResult('Added wall');
        // We don't have an API to get walls yet, so we can't render them unless we track locally or update API
        // For now, just log.
    } catch (e) {
        console.error(e);
    }
}

async function clearWalls() {
    await fetch('/api/walls/clear', { method: 'POST' });
    logResult('Cleared walls');
}

async function loadPhases() {
    const risName = document.getElementById('phase-ris-select').value;
    if (!risName) return;

    try {
        const res = await fetch(`/api/ris/${risName}/phases`);
        const data = await res.json();

        if (data.error) {
            logResult(data.error);
            return;
        }

        // Update stats
        document.getElementById('stat-grid').innerText = data.grid_size + 'x' + data.grid_size;
        document.getElementById('stat-bits').innerText = data.bits;
        document.getElementById('stat-states').innerText = data.phase_states;
        document.getElementById('stat-elements').innerText = data.total_elements;

        document.getElementById('phase-stats').classList.remove('hidden');
        document.getElementById('phase-grid-container').classList.remove('hidden');

        drawPhaseGrid(data.phase_grid, data.grid_size);

    } catch (e) {
        logResult('Error loading phases: ' + e);
    }
}

// ==========================================
// Visualization
// ==========================================

function renderNetwork() {
    // Clear SVG
    canvasSvg.innerHTML = '';

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    const cx = width / 2;
    const cy = height / 2;

    // Helper to transform coords
    const toSvg = (x, y) => ({
        x: cx + x * state.scale,
        y: cy + y * state.scale
    });

    // Draw Grid (optional, CSS handles background grid)

    // Draw Paths
    state.paths.forEach((path, i) => {
        // path.nodes is list of names
        // We need coords.
        let points = [];
        path.nodes.forEach(name => {
            const node = state.nodes.find(n => n.name === name);
            if (node) {
                const pos = toSvg(node.pos[0], node.pos[1]);
                points.push(`${pos.x},${pos.y}`);
            }
        });

        if (points.length > 1) {
            const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
            polyline.setAttribute('points', points.join(' '));
            polyline.setAttribute('class', 'path-line ' + (path.nodes.length > 2 ? 'path-relay' : 'path-direct'));
            polyline.setAttribute('stroke', i === 0 ? '#10B981' : '#6366F1'); // Best path green
            polyline.setAttribute('stroke-opacity', i === 0 ? 1 : 0.3);
            canvasSvg.appendChild(polyline);
        }
    });

    // Draw Nodes
    state.nodes.forEach(node => {
        const pos = toSvg(node.pos[0], node.pos[1]);

        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.setAttribute('transform', `translate(${pos.x}, ${pos.y})`);
        g.setAttribute('class', 'cursor-pointer');
        g.onclick = () => selectNode(node);

        // Icon background
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('r', 15);
        circle.setAttribute('fill', getNodeColor(node.type));
        circle.setAttribute('stroke', '#fff');
        circle.setAttribute('stroke-width', 2);
        g.appendChild(circle);

        // Label
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('y', 25);
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('class', 'text-xs font-bold fill-gray-700 pointer-events-none');
        text.textContent = node.name;
        g.appendChild(text);

        // Icon text
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        icon.setAttribute('y', 5);
        icon.setAttribute('text-anchor', 'middle');
        icon.setAttribute('class', 'text-sm pointer-events-none');
        icon.textContent = getNodeIcon(node.type);
        g.appendChild(icon);

        canvasSvg.appendChild(g);
    });
}

function getNodeColor(type) {
    switch (type) {
        case 'ap': return '#BFDBFE'; // blue-200
        case 'ris': return '#E9D5FF'; // purple-200
        case 'ue': return '#BBF7D0'; // green-200
        default: return '#ccc';
    }
}

function getNodeIcon(type) {
    switch (type) {
        case 'ap': return '📡';
        case 'ris': return '🔷';
        case 'ue': return '📱';
        default: return '?';
    }
}

function drawPhaseGrid(grid, size) {
    const c = document.getElementById('phase-canvas');
    const ctx = c.getContext('2d');
    const cellSize = c.width / size;

    ctx.clearRect(0, 0, c.width, c.height);

    for (let i = 0; i < size; i++) {
        for (let j = 0; j < size; j++) {
            // Phase is in radians. Map 0-2PI to color
            const phase = grid[i][j]; // Assuming grid is 2D array
            // If grid is flat, use grid[i*size + j]
            // Let's assume 2D for now based on typical numpy output, but check API.
            // API likely returns list of lists.

            const val = (phase % (2 * Math.PI)) / (2 * Math.PI);
            const hue = val * 360;

            ctx.fillStyle = `hsl(${hue}, 70%, 60%)`;
            ctx.fillRect(j * cellSize, i * cellSize, cellSize, cellSize);
        }
    }
}

// ==========================================
// Helpers
// ==========================================

function updateSelects() {
    const risSelect = document.getElementById('phase-ris-select');
    const current = risSelect.value;
    risSelect.innerHTML = '<option value="">Choose a RIS...</option>';

    state.nodes.filter(n => n.type === 'ris').forEach(n => {
        const opt = document.createElement('option');
        opt.value = n.name;
        opt.textContent = n.name;
        risSelect.appendChild(opt);
    });

    if (current) risSelect.value = current;
}

function selectNode(node) {
    // Auto-fill action inputs based on type
    if (node.type === 'ap') document.getElementById('act_ap').value = node.name;
    if (node.type === 'ris') document.getElementById('act_ris').value = node.name;
    if (node.type === 'ue') document.getElementById('act_ue').value = node.name;
}

function logResult(msg) {
    const el = document.getElementById('result');
    el.innerText = typeof msg === 'object' ? JSON.stringify(msg, null, 2) : msg;
}

function updateMetrics() {
    // Placeholder for live metrics polling
    // Could fetch /api/metrics if it existed
}

function switchTab(tab) {
    const visualTab = document.getElementById('tab-visual');
    const manualTab = document.getElementById('tab-manual');
    const visualContent = document.getElementById('content-visual');
    const manualContent = document.getElementById('content-manual');

    if (tab === 'visual') {
        visualContent.classList.remove('hidden');
        manualContent.classList.add('hidden');

        visualTab.classList.add('bg-white', 'shadow', 'text-gray-800');
        visualTab.classList.remove('text-gray-500');

        manualTab.classList.remove('bg-white', 'shadow', 'text-gray-800');
        manualTab.classList.add('text-gray-500');
    } else {
        visualContent.classList.add('hidden');
        manualContent.classList.remove('hidden');

        manualTab.classList.add('bg-white', 'shadow', 'text-gray-800');
        manualTab.classList.remove('text-gray-500');

        visualTab.classList.remove('bg-white', 'shadow', 'text-gray-800');
        visualTab.classList.add('text-gray-500');
    }
}
