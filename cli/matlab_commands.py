"""MATLAB integration commands for RIS shell.

This module provides mixin methods for MATLAB visualization commands.
These are added to RISNodeShell via multiple inheritance.
"""


class MatlabCommandsMixin:
    """Mixin class providing MATLAB integration commands for RIS shell."""

    _matlab_bridge = None  # Shared across instances

    def _get_matlab_bridge(self):
        """Lazy-load MATLAB bridge."""
        if MatlabCommandsMixin._matlab_bridge is None:
            try:
                from matlab_integration.bridge import MatlabBridge
                MatlabCommandsMixin._matlab_bridge = MatlabBridge.get_instance()
                print("MATLAB engine connected.")
            except ImportError as e:
                if "matlab.engine" in str(e):
                    print("Error: MATLAB Engine for Python not installed.")
                    print("Install with: pip install matlabengine")
                    print("(Requires MATLAB to be installed on this system)")
                else:
                    print(f"Error: {e}")
                return None
            except Exception as e:
                print(f"Error connecting to MATLAB: {e}")
                return None
        return MatlabCommandsMixin._matlab_bridge

    def do_matlab_heatmap(self, arg):
        """matlab_heatmap - Send phase matrix to MATLAB for heatmap visualization

        Displays the current RIS phase distribution as a heatmap in MATLAB.
        Requires phases to be computed first (run 'connect' command).

        Options:
            matlab_heatmap             - Show quantized phases (default)
            matlab_heatmap ideal       - Show ideal (continuous) phases
            matlab_heatmap jet         - Use 'jet' colormap
            matlab_heatmap ideal parula - Ideal phases with parula colormap

        Examples:
            matlab_heatmap
            matlab_heatmap ideal
            matlab_heatmap hsv
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        parts = arg.split() if arg else []
        show_quantized = True
        colormap = "hsv"

        for part in parts:
            if part.lower() == 'ideal':
                show_quantized = False
            elif part.lower() in ['hsv', 'jet', 'parula', 'hot', 'cool', 'spring',
                                  'summer', 'autumn', 'winter', 'gray']:
                colormap = part.lower()

        # Get phases
        if show_quantized and self.ris_node.quantized_phases is not None:
            phases = self.ris_node.quantized_phases
            phase_type = "quantized"
        elif self.ris_node.current_phases is not None:
            phases = self.ris_node.current_phases
            phase_type = "ideal"
        else:
            print("No phases configured. Run 'connect' command first.")
            return

        title = f"{self.ris_node.name} Phases ({phase_type}, {self.ris_node.bits}-bit)"

        try:
            bridge.show_phase_heatmap(
                phases=phases,
                N=self.ris_node.N,
                title=title,
                colormap=colormap,
                show_quantized=show_quantized,
                bits=self.ris_node.bits if show_quantized else None
            )
            print(f"Phase heatmap sent to MATLAB ({phase_type}, colormap={colormap})")
        except Exception as e:
            print(f"Error: {e}")

    def do_matlab_beam(self, arg):
        """matlab_beam [angle] - Compute and plot beam pattern in MATLAB

        Computes the beam pattern for the current RIS configuration.
        Uses the LOCAL deflection angle (relative to RIS normal), not absolute.

        Options:
            matlab_beam              - Use deflection angle from active link
            matlab_beam 30           - Compute pattern for 30 degree steering
            matlab_beam noplot       - Compute without plotting (returns metrics)

        Examples:
            matlab_beam
            matlab_beam 45
            matlab_beam -20
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        parts = arg.split() if arg else []
        beam_angle = None
        plot = True

        for part in parts:
            if part.lower() == 'noplot':
                plot = False
            else:
                try:
                    beam_angle = float(part)
                except ValueError:
                    pass

        # Use beam steering angle from active link if not specified
        if beam_angle is None:
            # Get deflection angle from phase_metadata (the actual RIS steering angle)
            if hasattr(self.ris_node, 'phase_metadata') and self.ris_node.phase_metadata:
                deflection = self.ris_node.phase_metadata.get('deflection_angle_deg')
                if deflection is not None:
                    beam_angle = deflection
            if beam_angle is None:
                beam_angle = 0.0
                print("No beam angle configured, using 0 degrees.")
            else:
                print(f"Using beam steering angle from active link: {beam_angle:.1f} degrees")

        try:
            result = bridge.compute_beam_pattern(
                N=self.ris_node.N,
                frequency=self.ris_node.freq,
                beam_angle_deg=beam_angle,
                element_spacing=self.ris_node.spacing,
                bits=self.ris_node.bits,
                plot=plot
            )
            print(f"Beam pattern computed for {beam_angle:.1f} degrees")
            print(f"  Main lobe width: {result['main_lobe_width']:.1f} degrees")
            print(f"  Sidelobe level:  {result['sidelobe_level']:.1f} dB")
        except Exception as e:
            print(f"Error: {e}")

    def do_matlab_geometry(self, arg):
        """matlab_geometry - Plot RIS geometry in MATLAB 3D view

        Displays the RIS element positions in a 3D plot.
        Optionally includes AP and UE positions if network is available.

        Options:
            matlab_geometry           - Plot RIS elements only
            matlab_geometry AP1 UE1   - Include AP1 and UE1 positions

        Examples:
            matlab_geometry
            matlab_geometry AP1 UE1
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        parts = arg.split() if arg else []

        # Ensure geometry is computed
        if self.ris_node.element_positions is None:
            self.ris_node.update_geometry()

        ap_pos = None
        ue_pos = None

        # Try to get AP/UE positions from network
        if self.network is not None and len(parts) >= 1:
            ap_name = parts[0] if len(parts) >= 1 else None
            ue_name = parts[1] if len(parts) >= 2 else None

            if ap_name and ap_name in self.network.nodes:
                ap_pos = self.network.nodes[ap_name].pos
            if ue_name and ue_name in self.network.nodes:
                ue_pos = self.network.nodes[ue_name].pos

        beam_angle = self.ris_node.current_beam_angle

        try:
            bridge.plot_ris_geometry(
                ris_position=self.ris_node.pos,
                element_positions=self.ris_node.element_positions,
                ap_position=ap_pos,
                ue_position=ue_pos,
                beam_angle_deg=beam_angle,
                title=f"RIS: {self.ris_node.name} ({self.ris_node.N}x{self.ris_node.N})"
            )
            print(f"Geometry sent to MATLAB ({self.ris_node.N}x{self.ris_node.N} elements)")
            if ap_pos is not None:
                print(f"  AP: {parts[0]}")
            if ue_pos is not None:
                print(f"  UE: {parts[1] if len(parts) >= 2 else ''}")
        except Exception as e:
            print(f"Error: {e}")

    def do_matlab_response(self, arg):
        """matlab_response - Compute full 2D array response in MATLAB

        Computes the array factor over a 2D angular grid (theta x phi).
        Results are displayed as both 2D image and 3D surface in MATLAB.

        Options:
            matlab_response                  - Default resolution (1 degree)
            matlab_response 0.5              - 0.5 degree resolution
            matlab_response -45 45 -45 45    - Custom theta/phi ranges

        Examples:
            matlab_response
            matlab_response 0.5
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        parts = arg.split() if arg else []

        # Parse arguments
        resolution = 1.0
        theta_range = (-90, 90)
        phi_range = (-90, 90)

        if len(parts) == 1:
            try:
                resolution = float(parts[0])
            except ValueError:
                pass
        elif len(parts) == 4:
            try:
                theta_range = (float(parts[0]), float(parts[1]))
                phi_range = (float(parts[2]), float(parts[3]))
            except ValueError:
                print("Invalid range values.")
                print("Usage: matlab_response theta_min theta_max phi_min phi_max")
                return

        # Ensure geometry and phases are available
        if self.ris_node.element_positions is None:
            self.ris_node.update_geometry()

        phases = self.ris_node.quantized_phases
        if phases is None:
            phases = self.ris_node.current_phases
        if phases is None:
            print("No phases configured. Run 'connect' command first.")
            return

        try:
            print(f"Computing array response (resolution={resolution}deg)...")
            result = bridge.compute_array_response(
                element_positions=self.ris_node.element_positions,
                phases=phases,
                frequency=self.ris_node.freq,
                theta_range=theta_range,
                phi_range=phi_range,
                resolution=resolution
            )
            print(f"Array response computed and displayed in MATLAB")
            print(f"  Theta range: {theta_range[0]} to {theta_range[1]} degrees")
            print(f"  Phi range:   {phi_range[0]} to {phi_range[1]} degrees")
            print(f"  Resolution:  {resolution} degrees")
        except Exception as e:
            print(f"Error: {e}")

    def do_matlab_disconnect(self, arg):
        """matlab_disconnect - Disconnect from MATLAB engine

        Closes the MATLAB engine connection to free resources.
        The engine will be restarted automatically on next MATLAB command.
        """
        if MatlabCommandsMixin._matlab_bridge is not None:
            try:
                MatlabCommandsMixin._matlab_bridge.disconnect()
                MatlabCommandsMixin._matlab_bridge = None
                print("MATLAB engine disconnected.")
            except Exception as e:
                print(f"Error disconnecting: {e}")
        else:
            print("MATLAB engine not connected.")
