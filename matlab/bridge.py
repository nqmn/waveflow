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
        ap_position: Optional[np.ndarray] = None,
        ue_position: Optional[np.ndarray] = None,
        beam_angle_deg: Optional[float] = None,
        title: str = "RIS Geometry"
    ) -> None:
        """
        Send RIS geometry to MATLAB for 3D visualization.

        Args:
            ris_position: RIS center [x, y, z]
            element_positions: (N*N, 3) array of element positions
            ap_position: Optional AP position [x, y, z]
            ue_position: Optional UE position [x, y, z]
            beam_angle_deg: Optional beam steering angle
            title: Plot title
        """
        matlab = _get_matlab()
        self.engine.plot_ris_geometry(
            self._to_matlab(ris_position),
            self._to_matlab(element_positions),
            self._to_matlab(ap_position) if ap_position is not None else matlab.double([]),
            self._to_matlab(ue_position) if ue_position is not None else matlab.double([]),
            float(beam_angle_deg) if beam_angle_deg is not None else matlab.double([]),
            title,
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
