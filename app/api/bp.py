"""API routes blueprint for RISNet"""

from flask import Blueprint, request, jsonify
import numpy as np
from app.validators import InputValidator, ValidationError

bp = Blueprint('api', __name__, url_prefix='/api')

# Global network instance (will be set by main.py)
_net = None
_controller = None
_state_manager = None


def set_network(net, controller, state_manager=None):
    """Set global network and controller instances"""
    global _net, _controller, _state_manager
    _net = net
    _controller = controller
    _state_manager = state_manager


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
    try:
        data = request.get_json() or {}
        typ = InputValidator.validate_node_type(data.get('type', ''))
        name = InputValidator.validate_node_name(data.get('name', ''))
        x, y, z = InputValidator.validate_coordinates(
            data.get('x', 0),
            data.get('y', 0),
            data.get('z', 0)
        )

        if typ == 'ap':
            power = InputValidator.validate_positive_float(
                data.get('power_dBm', 20.0), 'power_dBm', min_val=0.0
            )
            freq = InputValidator.validate_positive_float(
                data.get('freq', 5.8e9), 'freq', min_val=1e6
            )
            bw = InputValidator.validate_positive_float(
                data.get('bandwidth_MHz', 20.0), 'bandwidth_MHz', min_val=1.0
            )
            _net.add_ap(name, x, y, z, power, freq, bw)

        elif typ == 'ris':
            N, bits = InputValidator.validate_ris_params(
                data.get('N', 16),
                data.get('bits', 2)
            )
            freq = InputValidator.validate_positive_float(
                data.get('freq', 10e9), 'freq', min_val=1e6
            )
            _net.add_ris(name, x, y, z, N, bits, freq)

        elif typ == 'ue':
            _net.add_ue(name, x, y, z)

        return jsonify({'ok': True, 'node': {'name': name, 'type': typ, 'pos': [x, y, z]}})

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500


@bp.route('/connect')
def api_connect():
    """Legacy connect endpoint (AP->RIS->UE)"""
    try:
        ap = request.args.get('ap', '')
        ris = request.args.get('ris', '')
        ue = request.args.get('ue', '')
        angle = request.args.get('angle')

        # Validate nodes exist
        InputValidator.validate_nodes_exist(_net, ap, ris, ue)

        # Validate angle if provided
        if angle is not None:
            angle = InputValidator.validate_angle(angle, 'beam_angle_deg')

        res = _net.connect(ap, ris, ue, beam_angle_deg=angle)
        return jsonify(res)
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
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
    try:
        ap = request.args.get('ap', '')
        ue = request.args.get('ue', '')
        algorithm = request.args.get('algorithm', 'dijkstra')

        # Validate nodes exist
        InputValidator.validate_nodes_exist(_net, ap, ue)

        # Validate algorithm
        algorithm = InputValidator.validate_algorithm(algorithm)

        paths = _controller.find_all_paths(ap, ue, algorithm)
        return jsonify({
            'paths': paths,
            'stats': _controller.stats
        })
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@bp.route('/update_position', methods=['POST'])
def api_update_position():
    """Update node position"""
    try:
        data = request.get_json() or {}
        name = InputValidator.validate_node_name(data.get('name', ''))
        x, y, z = InputValidator.validate_coordinates(
            data.get('x', 0),
            data.get('y', 0),
            data.get('z', 0)
        )

        # Validate node exists
        InputValidator.validate_node_exists(_net, name)

        _net.update_node_position(name, x, y, z)
        return jsonify({'ok': True, 'name': name, 'pos': [x, y, z]})
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500


@bp.route('/walls/add', methods=['POST'])
def api_add_wall():
    """Add wall to environment"""
    try:
        data = request.get_json() or {}
        start = data.get('start', [0, 0])
        end = data.get('end', [5, 5])
        attenuation_dB = data.get('attenuation_dB', 20.0)

        # Validate start/end coordinates
        if not isinstance(start, (list, tuple)) or len(start) < 2:
            raise ValidationError("start must be [x, y]")
        if not isinstance(end, (list, tuple)) or len(end) < 2:
            raise ValidationError("end must be [x, y]")

        start_x, start_y, _ = InputValidator.validate_coordinates(start[0], start[1])
        end_x, end_y, _ = InputValidator.validate_coordinates(end[0], end[1])
        attn = InputValidator.validate_positive_float(
            attenuation_dB, 'attenuation_dB', min_val=0.0
        )

        _net.add_wall([start_x, start_y], [end_x, end_y], attn)
        return jsonify({'ok': True})
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500


@bp.route('/walls/clear', methods=['POST'])
def api_clear_walls():
    """Clear all walls"""
    _net.clear_walls()
    return jsonify({'ok': True})


@bp.route('/config', methods=['GET', 'POST'])
def api_config():
    """Get or update network configuration"""
    try:
        if request.method == 'GET':
            # Return current configuration
            config = {
                'impairments': _net.impairments if hasattr(_net, 'impairments') else {},
                'controller': {
                    'enabled': _controller.enabled if hasattr(_controller, 'enabled') else True,
                    'algorithm': _controller.algorithm if hasattr(_controller, 'algorithm') else 'dijkstra',
                    'strategy': _controller.strategy if hasattr(_controller, 'strategy') else 'max-snr'
                } if _controller else {},
                'nodes_count': len(_net.nodes) if hasattr(_net, 'nodes') else 0
            }
            return jsonify(config)

        else:  # POST - update configuration
            data = request.get_json() or {}

            # Update impairments if provided
            if 'impairments' in data:
                impairments = data['impairments']
                if isinstance(impairments, dict):
                    # Validate impairment values
                    for key, val in impairments.items():
                        if not isinstance(val, (int, float)):
                            raise ValidationError(f"Impairment '{key}' must be numeric")
                    _net.set_impairments(impairments)
                else:
                    raise ValidationError("Impairments must be a dictionary")

            # Update controller settings if provided
            if 'controller' in data and _controller:
                ctrl_data = data['controller']
                if isinstance(ctrl_data, dict):
                    if 'enabled' in ctrl_data:
                        if ctrl_data['enabled']:
                            _controller.enable()
                        else:
                            _controller.disable()

                    if 'algorithm' in ctrl_data:
                        algo = InputValidator.validate_algorithm(ctrl_data['algorithm'])
                        _controller.set_algorithm(algo)

                    if 'strategy' in ctrl_data:
                        strategy = ctrl_data['strategy']
                        if isinstance(strategy, str):
                            _controller.set_strategy(strategy)
                        else:
                            raise ValidationError("strategy must be a string")

            return jsonify({'ok': True, 'message': 'Configuration updated'})

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500


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


# =====================================================================
# State Management API Routes
# =====================================================================

@bp.route('/state/save', methods=['POST'])
def api_state_save():
    """Save network state to disk"""
    if not _state_manager:
        return jsonify({'error': 'State manager not configured'}), 500

    success = _state_manager.save_network(_net)
    if success:
        return jsonify({'ok': True, 'message': 'Network state saved'})
    else:
        return jsonify({'error': 'Failed to save network state'}), 500


@bp.route('/state/load', methods=['POST'])
def api_state_load():
    """Load network state from disk"""
    if not _state_manager:
        return jsonify({'error': 'State manager not configured'}), 500

    success = _state_manager.load_network(_net)
    if success:
        return jsonify({'ok': True, 'message': 'Network state loaded'})
    else:
        return jsonify({'ok': False, 'message': 'No saved state found'})


@bp.route('/state/clear', methods=['POST'])
def api_state_clear():
    """Clear network (remove all nodes) and delete saved state"""
    _net.nodes.clear()

    if _state_manager:
        _state_manager.clear_state()

    return jsonify({'ok': True, 'message': 'Network cleared'})


# =====================================================================
# Network Initialization API Routes
# =====================================================================

@bp.route('/init/topology', methods=['POST'])
def api_init_topology():
    """Initialize network with a pre-defined topology

    Supports different topology templates:
    - 'simple': 1 AP, 1 RIS, 1 UE
    - 'triangle': 1 AP, 2 RIS, 1 UE
    - 'grid': 2 AP, 4 RIS, 4 UE
    """
    try:
        data = request.get_json() or {}
        topology_type = data.get('type', 'simple').lower()

        # Clear existing network
        _net.nodes.clear()

        if topology_type == 'simple':
            # 1 AP, 1 RIS, 1 UE
            _net.add_ap('AP1', 0.0, 0.0)
            _net.add_ris('R1', 5.0, 0.0, N=16, bits=2)
            _net.add_ue('UE1', 10.0, 0.0)

        elif topology_type == 'triangle':
            # 1 AP, 2 RIS, 1 UE (triangular arrangement)
            _net.add_ap('AP1', 0.0, 0.0)
            _net.add_ris('R1', 5.0, 3.0, N=16, bits=2)
            _net.add_ris('R2', 5.0, -3.0, N=16, bits=2)
            _net.add_ue('UE1', 10.0, 0.0)

        elif topology_type == 'grid':
            # 2 AP, 4 RIS, 4 UE (2x2 grid)
            # APs at left
            _net.add_ap('AP1', 0.0, 2.5)
            _net.add_ap('AP2', 0.0, -2.5)

            # RIS in center (2x2 grid)
            _net.add_ris('R1', 5.0, 2.5, N=16, bits=2)
            _net.add_ris('R2', 5.0, -2.5, N=16, bits=2)
            _net.add_ris('R3', 8.0, 2.5, N=16, bits=2)
            _net.add_ris('R4', 8.0, -2.5, N=16, bits=2)

            # UE at right
            _net.add_ue('UE1', 13.0, 2.5)
            _net.add_ue('UE2', 13.0, -2.5)
            _net.add_ue('UE3', 13.0, 5.0)
            _net.add_ue('UE4', 13.0, -5.0)

        else:
            raise ValidationError(
                f"Unknown topology type '{topology_type}'. "
                "Valid types: simple, triangle, grid"
            )

        return jsonify({
            'ok': True,
            'message': f'Initialized {topology_type} topology',
            'nodes_count': len(_net.nodes)
        })

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500


@bp.route('/init/load', methods=['POST'])
def api_init_load():
    """Load topology from file

    Request body:
    {
        "filepath": "path/to/topology.json"
    }
    """
    try:
        data = request.get_json() or {}
        filepath = data.get('filepath')

        if not filepath or not isinstance(filepath, str):
            raise ValidationError("filepath must be a non-empty string")

        # Security: prevent directory traversal attacks
        if '..' in filepath or filepath.startswith('/'):
            raise ValidationError("Invalid filepath - cannot use absolute paths or '..'")

        import os
        if not os.path.exists(filepath):
            raise ValidationError(f"File not found: {filepath}")

        success = _state_manager.load_network(_net) if _state_manager else False

        if success:
            return jsonify({
                'ok': True,
                'message': f'Loaded topology from {filepath}',
                'nodes_count': len(_net.nodes)
            })
        else:
            raise ValidationError(f"Failed to load topology from {filepath}")

    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f"Internal error: {str(e)}"}), 500
