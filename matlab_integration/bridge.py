"""
MATLAB Engine Bridge for RISNet.

Provides a singleton bridge to MATLAB engine with lazy loading.
The MATLAB engine is only started when first accessed.
"""

from typing import Optional, Dict, Any, Tuple, TYPE_CHECKING
from pathlib import Path
import numpy as np

if TYPE_CHECKING:
    import matlab.engine

# Lazy-loaded modules
_matlab_engine_module = None
_matlab_module = None


def _get_matlab_engine():
    """Lazy load matlab.engine module."""
    global _matlab_engine_module
    if _matlab_engine_module is None:
        import matlab.engine
        _matlab_engine_module = matlab.engine
    return _matlab_engine_module


def _get_matlab():
    """Lazy load matlab module."""
    global _matlab_module
    if _matlab_module is None:
        import matlab
        _matlab_module = matlab
    return _matlab_module


class MatlabBridge:
    """
    Bridge between RISNet Python and MATLAB engine.

    Uses singleton pattern to maintain single MATLAB instance.
    Engine is started lazily on first access.

    Usage:
        bridge = MatlabBridge.get_instance()
        bridge.plot_ris_geometry(...)
    """

    _instance: Optional['MatlabBridge'] = None
    _engine: Optional['matlab.engine.MatlabEngine'] = None

    def __init__(self, scripts_path: Optional[str] = None):
        """
        Initialize bridge (does not start MATLAB yet).

        Args:
            scripts_path: Path to MATLAB scripts directory.
                         Defaults to ./scripts relative to this file.
        """
        self.scripts_path = scripts_path or str(
            Path(__file__).parent / "scripts"
        )
        self._connected = False

    @classmethod
    def get_instance(cls, scripts_path: Optional[str] = None) -> 'MatlabBridge':
        """
        Get singleton instance of MatlabBridge.

        Args:
            scripts_path: Optional path to MATLAB scripts

        Returns:
            MatlabBridge instance
        """
        if cls._instance is None:
            cls._instance = cls(scripts_path)
        return cls._instance

    def _connect(self) -> None:
        """Start or connect to MATLAB engine (lazy)."""
        if not self._connected:
            matlab_engine = _get_matlab_engine()
            MatlabBridge._engine = matlab_engine.start_matlab()
            MatlabBridge._engine.addpath(self.scripts_path, nargout=0)
            self._connected = True

    def disconnect(self) -> None:
        """Shutdown MATLAB engine and release resources."""
        if MatlabBridge._engine is not None:
            MatlabBridge._engine.quit()
            MatlabBridge._engine = None
            self._connected = False
        MatlabBridge._instance = None

    @property
    def engine(self) -> 'matlab.engine.MatlabEngine':
        """
        Get MATLAB engine, starting it if needed.

        Returns:
            MATLAB engine instance
        """
        if not self._connected:
            self._connect()
        return MatlabBridge._engine

    def _to_matlab(self, arr: np.ndarray):
        """Convert numpy array to MATLAB double."""
        matlab = _get_matlab()
        if arr is None:
            return matlab.double([])
        if arr.ndim == 1:
            return matlab.double(arr.tolist())
        return matlab.double(arr.tolist())

    def _from_matlab(self, mat_arr) -> np.ndarray:
        """Convert MATLAB array to numpy."""
        return np.array(mat_arr)

    # ─────────────────────────────────────────────────────────
    # Geometry Plotting
    # ─────────────────────────────────────────────────────────

    def plot_ris_geometry(
        self,
        ris_position: np.ndarray,
        element_positions: np.ndarray,
        ap_positions: Optional[np.ndarray] = None,
        ue_positions: Optional[np.ndarray] = None,
        beam_angle_deg: Optional[float] = None,
        title: str = "RIS Geometry",
        ap_names: Optional[list] = None,
        ue_names: Optional[list] = None,
        ris_normal_deg: Optional[float] = None,
        beam_arc_range: Optional[Tuple[float, float]] = None
    ) -> None:
        """
        Send RIS geometry to MATLAB for 3D visualization.

        Args:
            ris_position: RIS center [x, y, z]
            element_positions: (N*N, 3) array of element positions
            ap_positions: (N_ap, 3) array of AP positions or None
            ue_positions: (N_ue, 3) array of UE positions or None
            beam_angle_deg: Optional beam steering angle (absolute direction)
            title: Plot title
            ap_names: List of AP names
            ue_names: List of UE names
            ris_normal_deg: RIS normal angle in degrees
            beam_arc_range: (min_angle, max_angle) for field of view visualization
        """
        matlab = _get_matlab()
        self.engine.plot_ris_geometry(
            self._to_matlab(ris_position),
            self._to_matlab(element_positions),
            self._to_matlab(ap_positions) if ap_positions is not None else matlab.double([]),
            self._to_matlab(ue_positions) if ue_positions is not None else matlab.double([]),
            float(beam_angle_deg) if beam_angle_deg is not None else matlab.double([]),
            title,
            ap_names if ap_names else [],
            ue_names if ue_names else [],
            float(ris_normal_deg) if ris_normal_deg is not None else matlab.double([]),
            self._to_matlab(np.array(beam_arc_range)) if beam_arc_range else matlab.double([]),
            nargout=0
        )

    # ─────────────────────────────────────────────────────────
    # Phase Heatmap
    # ─────────────────────────────────────────────────────────

    def show_phase_heatmap(
        self,
        phases: np.ndarray,
        N: int,
        title: str = "RIS Phase Distribution",
        colormap: str = "hsv",
        show_quantized: bool = False,
        bits: Optional[int] = None
    ) -> None:
        """
        Display phase matrix as heatmap in MATLAB.

        Args:
            phases: 1D array of phases (radians) or 2D (N, N)
            N: Array size (NxN elements)
            title: Plot title
            colormap: MATLAB colormap name
            show_quantized: Show quantization levels
            bits: Quantization bits (required if show_quantized)
        """
        # Reshape to 2D if needed
        if phases.ndim == 1:
            phases_2d = phases.reshape(N, N)
        else:
            phases_2d = phases

        # Convert to degrees for visualization
        phases_deg = np.degrees(phases_2d) % 360

        self.engine.show_phase_heatmap(
            self._to_matlab(phases_deg),
            float(N),
            title,
            colormap,
            show_quantized,
            float(bits) if bits else 0.0,
            nargout=0
        )

    # ─────────────────────────────────────────────────────────
    # Array Response / Beam Computation
    # ─────────────────────────────────────────────────────────

    def compute_array_response(
        self,
        element_positions: np.ndarray,
        phases: np.ndarray,
        frequency: float,
        theta_range: Tuple[float, float] = (-90, 90),
        phi_range: Tuple[float, float] = (-90, 90),
        resolution: float = 1.0
    ) -> Dict[str, np.ndarray]:
        """
        Compute array factor/response pattern in MATLAB.

        Args:
            element_positions: (N*N, 3) element positions
            phases: 1D array of phases (radians)
            frequency: Operating frequency (Hz)
            theta_range: Elevation angle range (degrees)
            phi_range: Azimuth angle range (degrees)
            resolution: Angular resolution (degrees)

        Returns:
            Dict with 'theta', 'phi', 'AF_dB' arrays
        """
        matlab = _get_matlab()
        theta, phi, AF_dB = self.engine.compute_array_response(
            self._to_matlab(element_positions),
            self._to_matlab(phases),
            float(frequency),
            matlab.double(list(theta_range)),
            matlab.double(list(phi_range)),
            float(resolution),
            nargout=3
        )

        return {
            'theta': self._from_matlab(theta),
            'phi': self._from_matlab(phi),
            'AF_dB': self._from_matlab(AF_dB)
        }

    def compute_beam_pattern(
        self,
        N: int,
        frequency: float,
        beam_angle_deg: float,
        element_spacing: Optional[float] = None,
        bits: Optional[int] = None,
        plot: bool = True
    ) -> Dict[str, Any]:
        """
        Compute and optionally plot beam pattern.

        Args:
            N: Array size (NxN)
            frequency: Operating frequency (Hz)
            beam_angle_deg: Desired beam steering angle
            element_spacing: Element spacing (default: lambda/2)
            bits: Phase quantization bits (None = continuous)
            plot: Whether to plot in MATLAB

        Returns:
            Dict with 'angles', 'pattern_dB', 'main_lobe_width', 'sidelobe_level'
        """
        c = 3e8
        wavelength = c / frequency
        spacing = element_spacing or (wavelength / 2)

        angles, pattern_dB, metrics = self.engine.compute_beam_pattern(
            float(N),
            float(frequency),
            float(beam_angle_deg),
            float(spacing),
            float(bits) if bits else 0.0,
            plot,
            nargout=3
        )

        return {
            'angles': self._from_matlab(angles),
            'pattern_dB': self._from_matlab(pattern_dB),
            'main_lobe_width': float(metrics['main_lobe_width']),
            'sidelobe_level': float(metrics['sidelobe_level'])
        }

    def plot_farfield_3d(
        self,
        element_positions: np.ndarray,
        phases: np.ndarray,
        frequency: float,
        beam_angle_deg: float,
        N: int,
        style: str = 'cst',
        resolution: float = 2.0,
        bits: int = 0
    ) -> Dict[str, Any]:
        """
        Plot CST-style 3D far-field radiation pattern.

        Args:
            element_positions: (N*N, 3) element positions
            phases: 1D array of phases (radians)
            frequency: Operating frequency (Hz)
            beam_angle_deg: Beam steering angle (azimuth deflection)
            N: Array size (NxN)
            style: Plot style - 'cst', 'polar3d', 'sphere', or 'cartesian'
            resolution: Angular resolution in degrees (default: 2)
            bits: Phase quantization bits (default: 0 = continuous)

        Returns:
            Dict with 'peak_theta', 'peak_phi', 'hpbw', 'array_size'
        """
        result = self.engine.plot_farfield_3d(
            self._to_matlab(element_positions),
            self._to_matlab(phases),
            float(frequency),
            float(beam_angle_deg),
            float(N),
            style,
            float(resolution),
            float(bits),
            nargout=1
        )

        return {
            'peak_gain_dB': float(result['peak_gain_dB']),
            'peak_theta': float(result['peak_theta']),
            'peak_phi': float(result['peak_phi']),
            'hpbw': float(result['hpbw']),
            'array_size': int(result['array_size'])
        }

    def sweep_beam_snr(
        self,
        element_positions: np.ndarray,
        frequency: float,
        N: int,
        bits: int,
        ap_pos: np.ndarray,
        ris_pos: np.ndarray,
        ue_pos: Optional[np.ndarray] = None,
        tx_power_dBm: float = 20.0,
        angle_range: Tuple[float, float] = (-60, 60),
        angle_step: float = 1.0,
        ris_normal_deg: float = 0.0,
        max_steering_deg: float = 60.0
    ) -> Dict[str, Any]:
        """
        Sweep beam angles and compute directivity/SNR for each to find optimal.

        Two modes:
        1. Discovery mode (ue_pos=None): Sweep to find peak directivity
        2. UE-aware mode (ue_pos provided): Compute SNR at UE direction

        Args:
            element_positions: (N*N, 3) element positions
            frequency: Operating frequency (Hz)
            N: Array size (NxN)
            bits: Phase quantization bits (0 = continuous)
            ap_pos: AP position [x, y, z]
            ris_pos: RIS center position [x, y, z]
            ue_pos: UE position [x, y, z] or None for discovery mode
            tx_power_dBm: Transmit power in dBm
            angle_range: (min_angle, max_angle) in degrees relative to RIS normal
            angle_step: Angle step in degrees
            ris_normal_deg: RIS normal angle in degrees (0 = +x direction)
            max_steering_deg: Maximum steering angle from normal

        Returns:
            Dict with optimal_angle (relative to normal), optimal_snr/directivity, etc.
        """
        matlab = _get_matlab()

        # Pass empty array for discovery mode
        ue_pos_matlab = self._to_matlab(ue_pos) if ue_pos is not None else matlab.double([])

        result = self.engine.sweep_beam_snr(
            self._to_matlab(element_positions),
            float(frequency),
            float(N),
            float(bits),
            self._to_matlab(ap_pos),
            self._to_matlab(ris_pos),
            ue_pos_matlab,
            float(tx_power_dBm),
            matlab.double(list(angle_range)),
            float(angle_step),
            float(ris_normal_deg),
            float(max_steering_deg),
            nargout=1
        )

        # Convert MATLAB arrays to Python lists
        angles = self._from_matlab(result['angles']).flatten().tolist()
        snr_values = self._from_matlab(result['snr_values']).flatten().tolist()

        return {
            'optimal_angle': float(result['optimal_angle']),
            'optimal_snr': float(result['optimal_snr']),
            'deflection_angle': float(result['deflection_angle']),
            'snr_at_deflection': float(result['snr_at_deflection']),
            'incident_angle': float(result['incident_angle']),
            'target_angle': float(result['target_angle']),
            'd_ap_ris': float(result['d_ap_ris']),
            'd_ris_ue': float(result['d_ris_ue']),
            'ris_normal_deg': float(result['ris_normal_deg']),
            'angles': angles,
            'snr_values': snr_values,
            'discovery_mode': ue_pos is None
        }

    # ─────────────────────────────────────────────────────────
    # Generic MATLAB Execution
    # ─────────────────────────────────────────────────────────

    def run_script(self, script_name: str, *args, nargout: int = 0):
        """
        Run arbitrary MATLAB script with arguments.

        Args:
            script_name: Name of MATLAB function/script
            *args: Arguments to pass
            nargout: Number of output arguments

        Returns:
            Script output(s)
        """
        func = getattr(self.engine, script_name)
        return func(*args, nargout=nargout)

    def eval(self, matlab_code: str) -> None:
        """
        Evaluate MATLAB code string.

        Args:
            matlab_code: MATLAB code to execute
        """
        self.engine.eval(matlab_code, nargout=0)

    def workspace_put(self, name: str, value: Any) -> None:
        """
        Put variable into MATLAB workspace.

        Args:
            name: Variable name in MATLAB
            value: Value (numpy array or scalar)
        """
        if isinstance(value, np.ndarray):
            value = self._to_matlab(value)
        self.engine.workspace[name] = value

    def workspace_get(self, name: str) -> Any:
        """
        Get variable from MATLAB workspace.

        Args:
            name: Variable name in MATLAB

        Returns:
            Variable value
        """
        return self.engine.workspace[name]
