"""API routes blueprint for RISNet"""

from flask import Blueprint, request, jsonify
import numpy as np

bp = Blueprint('api', __name__, url_prefix='/api')

# Global network instance (will be set by main.py)
_net = None
_controller = None


def set_network(net, controller):
    """Set global network and controller instances"""
    global _net, _controller
    _net = net
    _controller = controller


# =====================================================================
# Core API Routes
# =====================================================================

@bp.route('/nodes', methods=['GET'])
def api_nodes():
    """Get all nodes"""
    nodes = []
    for name, node in _net.nodes.items():
        nodes.append(node.to_dict())
    return jsonify({'nodes': nodes})


@bp.route('/add', methods=['POST'])
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


@bp.route('/connect')
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


@bp.route('/sweep')
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


@bp.route('/find_paths')
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


@bp.route('/update_position', methods=['POST'])
def api_update_position():
    """Update node position"""
    data = request.get_json() or {}
    name = data.get('name')
    x = float(data.get('x', 0))
    y = float(data.get('y', 0))

    _net.update_node_position(name, x, y)
    return jsonify({'ok': True, 'name': name, 'pos': [x, y]})


@bp.route('/walls/add', methods=['POST'])
def api_add_wall():
    """Add wall to environment"""
    data = request.get_json() or {}
    start = data.get('start', [0, 0])
    end = data.get('end', [5, 5])
    attenuation_dB = data.get('attenuation_dB', 20.0)

    _net.add_wall(start, end, attenuation_dB)
    return jsonify({'ok': True})


@bp.route('/walls/clear', methods=['POST'])
def api_clear_walls():
    """Clear all walls"""
    _net.clear_walls()
    return jsonify({'ok': True})


@bp.route('/config', methods=['GET', 'POST'])
def api_config():
    """Get or update configuration"""
    # Note: requires _config global - can be added if needed
    return jsonify({'ok': False, 'error': 'not implemented'})


@bp.route('/ris/<ris_name>/phases')
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


@bp.route('/ris/<ris_name>/phases/summary')
def api_ris_phases_summary(ris_name):
    """Get summary statistics of RIS phase configuration"""
    ris = _net.get(ris_name)
    if not ris:
        return jsonify({'error': f'RIS {ris_name} not found'}), 404
    if not hasattr(ris, 'current_phases') or ris.current_phases is None:
        return jsonify({'error': 'No phase configuration computed yet. Run connect() first.'}), 400

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
# Waveform-Level API Routes
# =====================================================================

@bp.route('/waveform/snr', methods=['POST'])
def api_waveform_snr():
    """Compute SNR at waveform level"""
    data = request.get_json() or {}
    ap_name = data.get('ap')
    ris_name = data.get('ris')
    ue_name = data.get('ue')
    num_symbols = int(data.get('num_symbols', 10))

    try:
        from controller.waveform_controller import WaveformController
        waveform_ctrl = WaveformController(_net, _net.environment)
        result = waveform_ctrl.compute_waveform_snr(ap_name, ris_name, ue_name, num_symbols)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/waveform/compare', methods=['POST'])
def api_waveform_compare():
    """Compare system-level vs waveform-level results"""
    data = request.get_json() or {}
    ap_name = data.get('ap')
    ris_name = data.get('ris')
    ue_name = data.get('ue')

    try:
        from controller.waveform_controller import WaveformController
        waveform_ctrl = WaveformController(_net, _net.environment)
        result = waveform_ctrl.compare_system_vs_waveform(ap_name, ris_name, ue_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/waveform/beam_sweep', methods=['POST'])
def api_waveform_beam_sweep():
    """Perform beam sweep at waveform level"""
    data = request.get_json() or {}
    ap_name = data.get('ap')
    ris_name = data.get('ris')
    ue_name = data.get('ue')
    angle_range = float(data.get('angle_range', 60))
    angle_step = float(data.get('angle_step', 5))

    try:
        from controller.waveform_controller import WaveformController
        waveform_ctrl = WaveformController(_net, _net.environment)
        result = waveform_ctrl.compute_beam_sweep_waveform(ap_name, ris_name, ue_name, angle_range, angle_step)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/waveform/validate', methods=['GET'])
def api_waveform_validate():
    """Validate network topology"""
    try:
        from core.validation import WaveformValidator
        validator = WaveformValidator(_net)
        result = validator.validate_topology()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400
