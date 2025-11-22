"""
High-level MATLAB integration for RISNetwork.

Provides convenient methods to visualize and compute RIS properties in MATLAB.
All imports are lazy-loaded to avoid MATLAB startup overhead until needed.
"""

from typing import Optional, Dict, Any, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from ..core.network import RISNetwork
    from ..core.nodes import RIS
    from .bridge import MatlabBridge


class MatlabIntegration:
    """
    High-level integration between RISNetwork and MATLAB.

    Provides methods to:
    - Plot RIS geometry in 3D
    - Show phase distribution heatmaps
    - Compute and visualize beam patterns
    - Compute full 2D array response

    Usage:
        from risnet.core.network import RISNetwork
        from risnet.matlab import MatlabIntegration

        net = RISNetwork()
        net.add_ris("RIS1", 10, 5, 3, N=32, bits=2)

        matlab = MatlabIntegration(net)
        matlab.plot_ris("RIS1")
        matlab.show_ris_phases("RIS1")
    """

    def __init__(self, network: 'RISNetwork'):
        """
        Initialize MATLAB integration.

        Args:
            network: RISNetwork instance to integrate with
        """
        self.network = network
        self._bridge: Optional['MatlabBridge'] = None

    @property
    def bridge(self) -> 'MatlabBridge':
        """
        Get MatlabBridge instance (lazy-loaded).

        Returns:
            MatlabBridge singleton instance
        """
        if self._bridge is None:
            from .bridge import MatlabBridge
            self._bridge = MatlabBridge.get_instance()
        return self._bridge

    def disconnect(self) -> None:
        """Disconnect from MATLAB engine."""
        if self._bridge is not None:
            self._bridge.disconnect()
            self._bridge = None

    def plot_ris(
        self,
        ris_name: str,
        ap_name: Optional[str] = None,
        ue_name: Optional[str] = None,
        show_beam: bool = True
    ) -> None:
        """
        Plot RIS geometry in MATLAB 3D view.

        Args:
            ris_name: Name of RIS node to plot
            ap_name: Optional AP name to include in plot
            ue_name: Optional UE name to include in plot
            show_beam: Show beam direction arrow if beam is configured
        """
        ris: 'RIS' = self.network.ris_nodes[ris_name]

        # Get element positions
        if ris.element_positions is None:
            ris.update_geometry()
        elem_pos = ris.element_positions

        # Get optional node positions
        ap_pos = None
        ue_pos = None
        if ap_name and ap_name in self.network.ap_nodes:
            ap_pos = self.network.ap_nodes[ap_name].pos
        if ue_name and ue_name in self.network.ue_nodes:
            ue_pos = self.network.ue_nodes[ue_name].pos

        # Get beam angle if configured
        beam_angle = None
        if show_beam and ris.current_beam_angle is not None:
            beam_angle = ris.current_beam_angle

        self.bridge.plot_ris_geometry(
            ris_position=ris.pos,
            element_positions=elem_pos,
            ap_position=ap_pos,
            ue_position=ue_pos,
            beam_angle_deg=beam_angle,
            title=f"RIS: {ris_name} ({ris.N}x{ris.N})"
        )

    def show_ris_phases(
        self,
        ris_name: str,
        show_quantized: bool = True,
        colormap: str = "hsv"
    ) -> None:
        """
        Display RIS phase distribution as heatmap.

        Args:
            ris_name: Name of RIS node
            show_quantized: If True, show quantized phases; else ideal phases
            colormap: MATLAB colormap name ('hsv', 'jet', 'parula', etc.)
        """
        ris: 'RIS' = self.network.ris_nodes[ris_name]

        # Select phase array
        if show_quantized and ris.quantized_phases is not None:
            phases = ris.quantized_phases
            phase_type = "quantized"
        elif ris.current_phases is not None:
            phases = ris.current_phases
            phase_type = "ideal"
        else:
            raise ValueError(f"No phases configured for RIS '{ris_name}'. "
                           "Run network.connect() first.")

        title = f"Phases: {ris_name} ({phase_type}, {ris.bits}-bit)"

        self.bridge.show_phase_heatmap(
            phases=phases,
            N=ris.N,
            title=title,
            colormap=colormap,
            show_quantized=show_quantized,
            bits=ris.bits if show_quantized else None
        )

    def compute_beam_pattern(
        self,
        ris_name: str,
        beam_angle_deg: Optional[float] = None,
        plot: bool = True
    ) -> Dict[str, Any]:
        """
        Compute beam pattern in MATLAB.

        Args:
            ris_name: Name of RIS node
            beam_angle_deg: Steering angle (uses current if None)
            plot: Whether to display plot in MATLAB

        Returns:
            Dict with 'angles', 'pattern_dB', 'main_lobe_width', 'sidelobe_level'
        """
        ris: 'RIS' = self.network.ris_nodes[ris_name]

        # Use provided angle or current beam angle
        angle = beam_angle_deg
        if angle is None:
            angle = ris.current_beam_angle if ris.current_beam_angle is not None else 0.0

        return self.bridge.compute_beam_pattern(
            N=ris.N,
            frequency=ris.freq,
            beam_angle_deg=angle,
            element_spacing=ris.spacing,
            bits=ris.bits,
            plot=plot
        )

    def compute_array_response(
        self,
        ris_name: str,
        theta_range: tuple = (-90, 90),
        phi_range: tuple = (-90, 90),
        resolution: float = 1.0
    ) -> Dict[str, np.ndarray]:
        """
        Compute full 2D array response in MATLAB.

        Args:
            ris_name: Name of RIS node
            theta_range: Elevation angle range (degrees)
            phi_range: Azimuth angle range (degrees)
            resolution: Angular resolution (degrees)

        Returns:
            Dict with 'theta', 'phi', 'AF_dB' arrays
        """
        ris: 'RIS' = self.network.ris_nodes[ris_name]

        # Ensure geometry and phases are computed
        if ris.element_positions is None:
            ris.update_geometry()

        phases = ris.quantized_phases
        if phases is None:
            phases = ris.current_phases
        if phases is None:
            raise ValueError(f"No phases configured for RIS '{ris_name}'. "
                           "Run network.connect() first.")

        return self.bridge.compute_array_response(
            element_positions=ris.element_positions,
            phases=phases,
            frequency=ris.freq,
            theta_range=theta_range,
            phi_range=phi_range,
            resolution=resolution
        )

    def send_to_matlab(
        self,
        ris_name: str,
        var_prefix: str = "ris"
    ) -> Dict[str, str]:
        """
        Send RIS data to MATLAB workspace for custom processing.

        Args:
            ris_name: Name of RIS node
            var_prefix: Prefix for MATLAB variable names

        Returns:
            Dict mapping data type to MATLAB variable name
        """
        ris: 'RIS' = self.network.ris_nodes[ris_name]

        if ris.element_positions is None:
            ris.update_geometry()

        var_names = {}

        # Send element positions
        pos_var = f"{var_prefix}_elem_pos"
        self.bridge.workspace_put(pos_var, ris.element_positions)
        var_names['element_positions'] = pos_var

        # Send RIS center position
        center_var = f"{var_prefix}_center"
        self.bridge.workspace_put(center_var, ris.pos)
        var_names['center'] = center_var

        # Send phases if available
        if ris.quantized_phases is not None:
            phase_var = f"{var_prefix}_phases"
            self.bridge.workspace_put(phase_var, ris.quantized_phases)
            var_names['phases'] = phase_var

        # Send configuration
        config_var = f"{var_prefix}_config"
        self.bridge.eval(f"{config_var} = struct();")
        self.bridge.eval(f"{config_var}.N = {ris.N};")
        self.bridge.eval(f"{config_var}.bits = {ris.bits};")
        self.bridge.eval(f"{config_var}.freq = {ris.freq};")
        self.bridge.eval(f"{config_var}.spacing = {ris.spacing};")
        var_names['config'] = config_var

        return var_names

    def run_custom(
        self,
        script_name: str,
        *args,
        nargout: int = 0
    ):
        """
        Run custom MATLAB script.

        Args:
            script_name: Name of MATLAB function (must be on path)
            *args: Arguments to pass
            nargout: Number of expected outputs

        Returns:
            Script outputs
        """
        return self.bridge.run_script(script_name, *args, nargout=nargout)
