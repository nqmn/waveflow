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
        """matlab_geometry [fov] - Plot RIS geometry in MATLAB 3D view

        Displays the RIS element positions in a 3D plot with all network nodes.
        Shows all APs and UEs in the network, with connecting lines to RIS.
        Includes RIS normal, beam direction, and optional field of view arc.

        Options:
            matlab_geometry           - Plot all nodes
            matlab_geometry fov       - Include field of view arc visualization

        Examples:
            matlab_geometry
            matlab_geometry fov
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        import numpy as np

        parts = arg.split() if arg else []
        show_fov = 'fov' in [p.lower() for p in parts]

        # Ensure geometry is computed
        if self.ris_node.element_positions is None:
            self.ris_node.update_geometry()

        # Collect all APs and UEs from network
        ap_positions = []
        ap_names = []
        ue_positions = []
        ue_names = []

        if self.network is not None:
            for name, node in self.network.nodes.items():
                # Check if it's an AP (has power_dBm attribute)
                if hasattr(node, 'power_dBm'):
                    ap_positions.append(node.pos)
                    ap_names.append(name)
                # Check if it's a UE (has noise_figure_dB but not power_dBm)
                elif hasattr(node, 'noise_figure_dB') and not hasattr(node, 'power_dBm'):
                    ue_positions.append(node.pos)
                    ue_names.append(name)

        # Convert to numpy arrays
        ap_positions = np.array(ap_positions) if ap_positions else None
        ue_positions = np.array(ue_positions) if ue_positions else None

        # Get beam angle from phase metadata (absolute direction)
        beam_angle = None
        if hasattr(self.ris_node, 'phase_metadata') and self.ris_node.phase_metadata:
            beam_angle = self.ris_node.phase_metadata.get('reflected_azimuth_deg')
        if beam_angle is None:
            beam_angle = self.ris_node.current_beam_angle

        # Get RIS normal and compute FoV range
        ris_normal = getattr(self.ris_node, 'normal_angle_deg', 0.0)
        max_angle = getattr(self.ris_node, 'max_angle_deg', 60.0)

        # Compute beam arc range if requested
        beam_arc_range = None
        if show_fov:
            # FoV is relative to RIS normal
            beam_arc_range = (ris_normal - max_angle, ris_normal + max_angle)

        try:
            bridge.plot_ris_geometry(
                ris_position=self.ris_node.pos,
                element_positions=self.ris_node.element_positions,
                ap_positions=ap_positions,
                ue_positions=ue_positions,
                beam_angle_deg=beam_angle,
                title=f"RIS Network: {self.ris_node.name} ({self.ris_node.N}x{self.ris_node.N})",
                ap_names=ap_names,
                ue_names=ue_names,
                ris_normal_deg=ris_normal,
                beam_arc_range=beam_arc_range
            )
            print(f"Geometry sent to MATLAB ({self.ris_node.N}x{self.ris_node.N} elements)")
            print(f"  RIS: {self.ris_node.name} at ({self.ris_node.pos[0]:.2f}, {self.ris_node.pos[1]:.2f}, {self.ris_node.pos[2]:.2f})")
            print(f"  Normal: {ris_normal:.1f} deg")
            if beam_angle is not None:
                print(f"  Beam:   {beam_angle:.1f} deg")
            if ap_names:
                print(f"  APs:    {', '.join(ap_names)}")
            if ue_names:
                print(f"  UEs:    {', '.join(ue_names)}")
            if show_fov:
                print(f"  FoV:    [{ris_normal - max_angle:.1f}, {ris_normal + max_angle:.1f}] deg")
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

    def do_matlab_farfield(self, arg):
        """matlab_farfield [style] [resolution] - Plot 3D CST-style far-field radiation pattern

        Displays the RIS far-field radiation pattern in MATLAB with CST-style visualization.
        Shows RIS array surface with phase heatmap and 3D beam pattern above it.

        Styles:
            cst        - CST-style with RIS surface + 3D beam (default)
            polar3d    - 3D polar radiation pattern only
            sphere     - Pattern mapped onto unit sphere
            cartesian  - Standard 3D Cartesian surface plot

        Options:
            matlab_farfield                - Default CST style, 2 deg resolution
            matlab_farfield cst 1          - CST style with 1 deg resolution
            matlab_farfield polar3d        - Polar 3D style
            matlab_farfield sphere         - Sphere projection style

        Examples:
            matlab_farfield
            matlab_farfield cst
            matlab_farfield polar3d 1
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        parts = arg.split() if arg else []
        style = 'cst'
        resolution = 2.0

        for part in parts:
            if part.lower() in ['cst', 'polar3d', 'sphere', 'cartesian']:
                style = part.lower()
            else:
                try:
                    resolution = float(part)
                except ValueError:
                    pass

        # Ensure geometry and phases are available
        if self.ris_node.element_positions is None:
            self.ris_node.update_geometry()

        phases = self.ris_node.quantized_phases
        if phases is None:
            phases = self.ris_node.current_phases
        if phases is None:
            print("No phases configured. Run 'connect' command first.")
            return

        # Get beam angle from phase_metadata
        beam_angle = 0.0
        if hasattr(self.ris_node, 'phase_metadata') and self.ris_node.phase_metadata:
            deflection = self.ris_node.phase_metadata.get('deflection_angle_deg')
            if deflection is not None:
                beam_angle = deflection

        # Debug: show what angle is being used
        print(f"[DEBUG] Beam angle for farfield: {beam_angle}°")
        if hasattr(self.ris_node, 'phase_metadata'):
            print(f"[DEBUG] Phase metadata: {self.ris_node.phase_metadata}")

        try:
            bits = self.ris_node.bits if hasattr(self.ris_node, 'bits') else 0
            print(f"Computing 3D far-field pattern (style={style}, resolution={resolution}°, {bits}-bit)...")
            result = bridge.plot_farfield_3d(
                element_positions=self.ris_node.element_positions,
                phases=phases,
                frequency=self.ris_node.freq,
                beam_angle_deg=beam_angle,
                N=self.ris_node.N,
                style=style,
                resolution=resolution,
                bits=bits
            )
            print(f"Far-field pattern displayed in MATLAB")
            print(f"  Beam steering angle:  {beam_angle:.1f}° (used for phase computation)")
            print(f"  Array size:           {result['array_size']}x{result['array_size']}")
            print(f"  Peak direction:       theta={result['peak_theta']:.1f}° (elevation), phi={result['peak_phi']:.1f}° (azimuth)")
            print(f"  HPBW:                 {result['hpbw']:.1f}°")
            print(f"  Quantization:         {bits}-bit" if bits > 0 else "  Quantization:         continuous")
            print(f"  Style:                {style}")
            print(f"\n  NOTE: Peak direction should match steering angle in azimuth (phi)")
            print(f"        Expected phi ≈ {beam_angle:.1f}° or equivalently ≈ {(beam_angle + 180) % 360 - 180:.1f}°")
        except Exception as e:
            print(f"Error: {e}")

    def do_matlab_sweep(self, arg):
        """matlab_sweep [step] [table] [apply] [AP_name] [UE_name] - Sweep beam angles

        Two modes:
        1. Discovery mode (default): Sweep angles to find peak directivity.
           Only needs AP and RIS positions. UE position is unknown.
        2. UE-aware mode: If UE is specified, compute SNR at UE direction.

        Options:
            matlab_sweep              - Discovery mode, 1 deg step
            matlab_sweep 0.5          - 0.5 degree step (finer resolution)
            matlab_sweep 2            - 2 degree step (faster)
            matlab_sweep table        - Show directivity/SNR table
            matlab_sweep apply        - Apply optimal angle to active links
            matlab_sweep AP1          - Specify AP (discovery mode)
            matlab_sweep AP1 UE1      - UE-aware mode with specific AP/UE

        Examples:
            matlab_sweep              - Discovery sweep using first AP
            matlab_sweep 0.5 table    - Fine sweep with table output
            matlab_sweep AP1 UE1      - UE-aware mode
            matlab_sweep 1 apply      - Sweep and apply optimal angle
        """
        bridge = self._get_matlab_bridge()
        if bridge is None:
            return

        # Parse arguments
        parts = arg.split() if arg else []
        angle_step = 1.0
        apply_result = False
        show_table = False
        ap_name = None
        ue_name = None

        for part in parts:
            if part.lower() == 'apply':
                apply_result = True
            elif part.lower() == 'table':
                show_table = True
            else:
                try:
                    angle_step = float(part)
                except ValueError:
                    # Could be node name
                    if self.network and part in self.network.nodes:
                        node = self.network.get(part)
                        if hasattr(node, 'power_dBm'):
                            ap_name = part
                        elif hasattr(node, 'noise_figure_dB'):
                            ue_name = part

        # Ensure geometry is available
        if self.ris_node.element_positions is None:
            self.ris_node.update_geometry()

        # Get AP from network
        if self.network is None:
            print("Error: No network available. Load a topology first.")
            return

        ap_node = None
        ue_node = None

        # If AP name specified, use it
        if ap_name:
            ap_node = self.network.get(ap_name)
        else:
            # Try to find from active links first
            for link_key, link_info in self.network.active_links.items():
                if link_info.get('ris') == self.ris_node.name:
                    ap_name = link_info.get('ap')
                    if ap_name:
                        ap_node = self.network.get(ap_name)
                    break

            # Fallback: find first AP in network
            if ap_node is None:
                for name, node in self.network.nodes.items():
                    if hasattr(node, 'power_dBm'):
                        ap_node = node
                        break

        if ap_node is None:
            print("Error: No AP found in network.")
            return

        # Get UE if specified (for UE-aware mode)
        if ue_name:
            ue_node = self.network.get(ue_name)

        tx_power = getattr(ap_node, 'power_dBm', 20.0)
        bits = self.ris_node.bits if hasattr(self.ris_node, 'bits') else 0

        # Get RIS normal and max steering angle
        ris_normal = getattr(self.ris_node, 'normal_angle_deg', 0.0)
        max_steering = getattr(self.ris_node, 'max_angle_deg', 60.0)

        # Determine mode
        discovery_mode = ue_node is None

        if discovery_mode:
            print(f"Beam Discovery Sweep (step={angle_step} deg, {bits}-bit)...")
            print(f"  AP:  {ap_node.name} at ({ap_node.pos[0]:.2f}, {ap_node.pos[1]:.2f}, {ap_node.pos[2]:.2f})")
            print(f"  RIS: {self.ris_node.name} at ({self.ris_node.pos[0]:.2f}, {self.ris_node.pos[1]:.2f}, {self.ris_node.pos[2]:.2f})")
            print(f"  RIS Normal: {ris_normal:.1f} deg, Max Steering: +/-{max_steering:.1f} deg")
            print(f"  UE:  (unknown - discovery mode)")
        else:
            print(f"UE-Aware Sweep (step={angle_step} deg, {bits}-bit)...")
            print(f"  AP:  {ap_node.name} at ({ap_node.pos[0]:.2f}, {ap_node.pos[1]:.2f}, {ap_node.pos[2]:.2f})")
            print(f"  RIS: {self.ris_node.name} at ({self.ris_node.pos[0]:.2f}, {self.ris_node.pos[1]:.2f}, {self.ris_node.pos[2]:.2f})")
            print(f"  RIS Normal: {ris_normal:.1f} deg, Max Steering: +/-{max_steering:.1f} deg")
            print(f"  UE:  {ue_node.name} at ({ue_node.pos[0]:.2f}, {ue_node.pos[1]:.2f}, {ue_node.pos[2]:.2f})")

        try:
            result = bridge.sweep_beam_snr(
                element_positions=self.ris_node.element_positions,
                frequency=self.ris_node.freq,
                N=self.ris_node.N,
                bits=bits,
                ap_pos=ap_node.pos,
                ris_pos=self.ris_node.pos,
                ue_pos=ue_node.pos if ue_node else None,
                tx_power_dBm=tx_power,
                angle_range=(-max_steering, max_steering),
                angle_step=angle_step,
                ris_normal_deg=ris_normal,
                max_steering_deg=max_steering
            )

            print(f"\nResults (angles in GLOBAL coordinates, matching 'connect' command):")
            print(f"  RIS Normal:                {result['ris_normal_deg']:.1f} deg (absolute)")

            # Convert incident angle to deflection (absolute frame)
            incident_abs = result['ris_normal_deg'] + result['incident_angle']
            # Normalize to [-180, 180]
            while incident_abs > 180:
                incident_abs -= 360
            while incident_abs < -180:
                incident_abs += 360

            if discovery_mode:
                optimal_abs = result['ris_normal_deg'] + result['optimal_angle']
                # Normalize
                while optimal_abs > 180:
                    optimal_abs -= 360
                while optimal_abs < -180:
                    optimal_abs += 360

                print(f"  Incident angle (AP->RIS):  {incident_abs:.1f} deg (absolute)")
                print(f"  Optimal steering angle:    {result['optimal_angle']:.1f} deg (rel to normal) = {optimal_abs:.1f} deg (absolute)")
                print(f"  Peak directivity:          {result['optimal_snr']:.1f} dB")
                print(f"  Beam direction (absolute): {result['target_angle']:.1f} deg")
                print(f"  Distance AP->RIS:          {result['d_ap_ris']:.2f} m")
            else:
                optimal_abs = result['ris_normal_deg'] + result['optimal_angle']
                # Normalize
                while optimal_abs > 180:
                    optimal_abs -= 360
                while optimal_abs < -180:
                    optimal_abs += 360

                target_abs = result['target_angle']
                deflection_from_incident = target_abs - incident_abs
                while deflection_from_incident > 180:
                    deflection_from_incident -= 360
                while deflection_from_incident < -180:
                    deflection_from_incident += 360

                print(f"  Incident angle (AP->RIS):  {incident_abs:.1f} deg (absolute)")
                print(f"  Target angle (RIS->UE):    {target_abs:.1f} deg (absolute)")
                print(f"  Required deflection:       {deflection_from_incident:.1f} deg")
                print(f"  SNR at target:             {result['snr_at_deflection']:.1f} dB")
                print(f"  Optimal angle:             {result['optimal_angle']:.1f} deg (rel to normal) = {optimal_abs:.1f} deg (absolute)")
                print(f"  SNR at optimal:            {result['optimal_snr']:.1f} dB")
                print(f"  Distance AP->RIS:          {result['d_ap_ris']:.2f} m")
                print(f"  Distance RIS->UE:          {result['d_ris_ue']:.2f} m")

                if abs(result['optimal_angle'] - result['deflection_angle']) < angle_step * 2:
                    print(f"\n  [OK] Optimal angle matches target direction!")
                else:
                    print(f"\n  [!] Optimal differs from target by {abs(result['optimal_angle'] - result['deflection_angle']):.1f} deg")

            # Show table if requested
            if show_table and 'angles' in result and 'snr_values' in result:
                angles = result['angles']
                snr_values = result['snr_values']
                metric_name = "Directivity (dB)" if discovery_mode else "SNR (dB)"

                print(f"\n{'='*85}")
                print(f"BEAM SWEEP TABLE ({len(angles)} angles)")
                print(f"{'='*85}")
                print(f"{'Rel Angle':>12} {'Abs Angle':>12} {metric_name:>16} {'Status':>20}")
                print(f"{'(deg)':>12} {'(deg)':>12} {'':<16} {'':<20}")
                print(f"{'-'*12} {'-'*12} {'-'*16} {'-'*20}")

                # Find top 10 values for highlighting
                sorted_indices = sorted(range(len(snr_values)), key=lambda i: snr_values[i], reverse=True)
                top_indices = set(sorted_indices[:10])

                for i, (angle_rel, snr) in enumerate(zip(angles, snr_values)):
                    # Convert to absolute angle
                    angle_abs = result['ris_normal_deg'] + angle_rel
                    # Normalize to [-180, 180]
                    while angle_abs > 180:
                        angle_abs -= 360
                    while angle_abs < -180:
                        angle_abs += 360

                    status = ""
                    if abs(angle_rel - result['optimal_angle']) < 0.1:
                        status = "<- OPTIMAL"
                    elif not discovery_mode and abs(angle_rel - result['deflection_angle']) < 0.1:
                        status = "<- DEFLECTION"
                    elif i in top_indices:
                        status = f"(top {sorted_indices.index(i)+1})"

                    print(f"{angle_rel:>12.1f} {angle_abs:>12.1f} {snr:>16.1f} {status:>20}")

                print(f"{'='*85}")

                # Show summary of top angles
                ris_normal = result['ris_normal_deg']
                print(f"\nTop 5 beam angles by {metric_name.split()[0]}:")
                for rank, idx in enumerate(sorted_indices[:5], 1):
                    angle_rel = angles[idx]
                    angle_abs = ris_normal + angle_rel
                    # Normalize
                    while angle_abs > 180:
                        angle_abs -= 360
                    while angle_abs < -180:
                        angle_abs += 360
                    print(f"  {rank}. {angle_rel:>6.1f} deg (rel) = {angle_abs:>7.1f} deg (abs) -> {snr_values[idx]:.1f} dB")

            # Apply optimal angle if requested
            if apply_result:
                print(f"\nApplying optimal angle to RIS phases...")
                try:
                    # Compute phases for optimal angle
                    import numpy as np
                    c = 3e8
                    wavelength = c / self.ris_node.freq
                    k = 2 * np.pi / wavelength

                    # Get element positions centered
                    elem_pos = self.ris_node.element_positions
                    x_pos = elem_pos[:, 0] - np.mean(elem_pos[:, 0])
                    y_pos = elem_pos[:, 1] - np.mean(elem_pos[:, 1])

                    optimal_angle = result['optimal_angle']
                    phases = -k * (x_pos * np.cos(np.radians(optimal_angle)) +
                                   y_pos * np.sin(np.radians(optimal_angle)))

                    # Apply quantization
                    if bits > 0:
                        num_levels = 2 ** bits
                        phase_step = 2 * np.pi / num_levels
                        phases = np.round(phases / phase_step) * phase_step

                    # Store phases
                    self.ris_node.current_phases = phases
                    self.ris_node.quantized_phases = phases

                    # Update phase metadata
                    if hasattr(self.ris_node, 'phase_metadata'):
                        self.ris_node.phase_metadata['deflection_angle_deg'] = optimal_angle
                        self.ris_node.phase_metadata['incident_azimuth_deg'] = result['incident_angle']
                        self.ris_node.phase_metadata['reflected_azimuth_deg'] = result['target_angle']

                    print(f"  [OK] Phases applied for {optimal_angle:.1f} deg steering")
                    print(f"       Beam direction: {result['target_angle']:.1f} deg (absolute)")

                    # If we have a UE, also create active link
                    if ue_node:
                        connect_result = self.network.connect(
                            ap_node.name,
                            self.ris_node.name,
                            ue_node.name,
                            compute_phases=True,
                            store_in_active_links=True
                        )
                        print(f"  [OK] Active link: {ap_node.name}->{self.ris_node.name}->{ue_node.name}")
                        print(f"       SNR: {connect_result['snr_dB']:.1f} dB, Gain: {connect_result['gain_dBi']:.1f} dBi")

                except Exception as e:
                    print(f"  [X] Failed to apply: {e}")

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
