"""RIS node interactive shell"""

import cmd
import shlex
import numpy as np
from datetime import datetime


class RISNodeShell(cmd.Cmd):
    """Interactive shell for RIS node management"""

    def __init__(self, ris_node, network=None):
        super().__init__()
        self.ris_node = ris_node
        self.network = network  # Reference to network for accessing active_links
        self.prompt = f"{ris_node.name}> "
        self.intro = f"\n{'='*60}\nRIS Node Shell: {ris_node.name}\n{'='*60}\n"
        self.last_connect_result = None  # Store phase data from connect() command
        self._print_status()
        print("\nAvailable commands: help, status, config, info, phases, wave_mode, exit")
        print("Phase formats: compact, grid, stats, plot, codebook, transmit, export")
        print("Wave modes: set_tx_mode, set_rx_mode, wave_mode")
        print("Type 'help' for more information\n")

    def do_help(self, arg):
        """help [command] - Show help"""
        if arg:
            return super().do_help(arg)

        help_text = """
RIS Node Commands:
  help                    - Show this help message
  status                  - Show current RIS status
  info                    - Show detailed RIS information
  config [set]            - Show or modify RIS configuration
  phases [format]         - Display phase element values
  wave_mode [info]        - Show wave mode configuration
  set_tx_mode <mode>      - Set TX wave type (auto/plane/spherical)
  set_rx_mode <mode>      - Set RX wave type (auto/plane/focus)
  exit                    - Exit RIS shell

Phase Formats (use: phases <format>):
  compact                 - Compact list of all phase values (default)
  grid                    - 16×16 grid visualization with bar indicators
  stats                   - Statistics (min/max/mean/std + quantization error)
  plot                    - Plot phase distribution (if available)
  codebook                - Phase state codebook (0, 1, 2, ... for each element)
  transmit                - RIS transmission-ready format (hex, UART, checksum)
  export <file> <fmt>     - Export codebook (hex, binary, csv, json)

Wave Mode Control:
  set_tx_mode auto        - Auto-select TX wave type (Fraunhofer boundary)
  set_tx_mode plane       - Use plane wave TX (far-field)
  set_tx_mode spherical   - Use spherical wave TX (near-field)
  set_rx_mode auto        - Auto-select RX wave type (Fraunhofer boundary)
  set_rx_mode plane       - Use plane wave RX (beam steering)
  set_rx_mode focus       - Use spherical wave RX (point focusing)
  wave_mode               - Show current TX/RX mode configuration
        """
        print(help_text)

    def do_status(self, arg):
        """status - Show RIS status"""
        self._print_status()

    def do_info(self, arg):
        """info - Show RIS information"""
        print(f"\n{self.ris_node.name} Information:")
        print(f"  Name:          {self.ris_node.name}")
        print(f"  Type:          RIS Surface")
        print(f"  Position:      ({self.ris_node.pos[0]:.2f}, {self.ris_node.pos[1]:.2f}, {self.ris_node.pos[2]:.2f}) meters")
        print(f"  Grid Size:     {self.ris_node.N}x{self.ris_node.N} elements")
        print(f"  Total Elements:{self.ris_node.N * self.ris_node.N}")
        print(f"  Phase Bits:    {self.ris_node.bits} bits per element")
        print(f"  Phase Range:   0 to {360 * (1 - 1/(2**self.ris_node.bits)):.1f}°")
        print(f"  States/Element:{2**self.ris_node.bits}")
        print(f"  Field of View: ±{self.ris_node.max_angle_deg}°")

        try:
            total_elements = self.ris_node.N * self.ris_node.N
            states_per_element = 2 ** self.ris_node.bits
            import math
            log_total_states = total_elements * math.log10(states_per_element)
            print(f"  Total States:  10^{log_total_states:.2f} (too large to display)")
        except:
            print(f"  Total States:  (too large to calculate)")

    def do_config(self, arg):
        """config [grid N | bits B] - Show or modify RIS configuration"""
        if not arg:
            print(f"\n{self.ris_node.name} Configuration:")
            print(f"  Grid Size (N): {self.ris_node.N}")
            print(f"  Phase Bits:    {self.ris_node.bits}")
            print(f"  Current Mode:  Passive Beamforming")
        else:
            parts = shlex.split(arg)
            key = parts[0].lower()
            if key == 'grid' and len(parts) > 1:
                try:
                    new_n = int(parts[1])
                    self.ris_node.N = new_n
                    print(f"✓ Grid size updated to {new_n}x{new_n}")
                except ValueError:
                    print("Invalid value. Usage: config grid <N>")
            elif key == 'bits' and len(parts) > 1:
                try:
                    new_bits = int(parts[1])
                    self.ris_node.bits = new_bits
                    print(f"✓ Phase bits updated to {new_bits}")
                except ValueError:
                    print("Invalid value. Usage: config bits <bits>")
            else:
                print("Usage: config <grid|bits> <value>")

    def do_phases(self, arg):
        """phases [link_index] [format] - Display phase elements from an active link

        With no arguments, shows phases from most recent connect/sweep.

        Link Index: Use status command to see numbered active links [1], [2], etc.

        Formats: compact (default), grid, stats, plot, codebook, transmit
        Export:  export <filename> <format>  (hex, binary, csv, json)

        Examples:
            phases                          # Most recent phases
            phases 2                        # Phases from link [2]
            phases 2 grid                   # Link [2] phases in grid format
            phases codebook                 # Show phase state codebook
            phases transmit                 # Show transmission format
            phases export codebook.hex hex  # Export as hex file
        """
        parts = arg.split() if arg else []
        link_index = None
        format_type = 'compact'
        export_filename = None
        export_format = None

        # Parse arguments
        i = 0
        while i < len(parts):
            part = parts[i]
            if part == 'export' and i + 2 < len(parts):
                export_filename = parts[i + 1]
                export_format = parts[i + 2].lower()
                i += 3
            elif part.isdigit():
                link_index = int(part)
                i += 1
            else:
                format_type = part.lower()
                i += 1

        # If link_index specified, load phases from that active link
        if link_index is not None:
            if self.network is None:
                print("✗ Network not available (cannot access active links)")
                return

            active_links = self.network.get_active_links()
            if not active_links:
                print("✗ No active links found")
                return

            if link_index < 1 or link_index > len(active_links):
                print(f"✗ Invalid link index. Available links: [1] to [{len(active_links)}]")
                print(f"  Use 'status' command to see active links")
                return

            # Get the link by index
            link_name = list(active_links.keys())[link_index - 1]
            link_info = active_links[link_name]

            # Restore phases from the link info
            if 'current_phases' in link_info:
                self.ris_node.current_phases = np.array(link_info['current_phases'])
            if 'quantized_phases' in link_info:
                self.ris_node.quantized_phases = np.array(link_info['quantized_phases'])
            if 'phase_states' in link_info:
                self.ris_node.phase_states = np.array(link_info['phase_states'])

            # Restore beam angle attributes from the link info
            if 'beam_angle_local' in link_info:
                self.ris_node.local_beam_deflection_deg = float(link_info['beam_angle_local'])
            if 'beam_angle_absolute' in link_info:
                self.ris_node.abs_beam_angle_deg = float(link_info['beam_angle_absolute'])
            if 'ris_normal_angle' in link_info:
                self.ris_node.specular_angle_deg = float(link_info['ris_normal_angle'])

            print(f"Displaying phases from: [{link_index}] {link_name}")
            # Display angles with new format (Steering Angle with azimuths if available)
            if link_info.get('deflection_angle_deg') is not None:
                print(f"Steering Angle (Deflection): {link_info['deflection_angle_deg']:.2f}° (azimuth deflection magnitude)")
                if link_info.get('incident_azimuth_deg') is not None:
                    print(f"  Incident Azimuth (AP→RIS): {link_info['incident_azimuth_deg']:.2f}°")
                if link_info.get('reflected_azimuth_deg') is not None:
                    print(f"  Reflected Azimuth (RIS→UE): {link_info['reflected_azimuth_deg']:.2f}°")
            elif 'beam_angle_local' in link_info:
                # Fallback: use beam_angle_local as steering angle when metadata unavailable
                print(f"Steering Angle (Deflection): {link_info['beam_angle_local']:.2f}° (azimuth deflection magnitude)")
            print()
        else:
            # Try to use phase data from recent connect() result
            if self.last_connect_result and 'current_phases' in self.last_connect_result:
                self._load_phases_from_result(self.last_connect_result)

        # Fall back to node's own phase data
        if self.ris_node.current_phases is None:
            print(f"✗ No phase configuration computed yet.")
            print(f"  Run 'connect' command first to compute phases.")
            print(f"  Or use: phases <link_index>  (e.g., phases 2)")
            return

        # Handle export first (special case)
        if export_filename and export_format:
            self._export_phases(export_filename, export_format)
            return

        # Handle display formats
        if format_type == 'stats':
            self._print_phase_stats()
        elif format_type == 'compact':
            self._print_phase_compact()
        elif format_type == 'plot':
            self._plot_phase_grid()
        elif format_type == 'grid':
            self._print_phase_grid()
        elif format_type == 'codebook':
            self._print_phase_codebook()
        elif format_type == 'transmit':
            self._print_phase_transmit()
        else:  # invalid format, default to compact
            print(f"Unknown format: {format_type}. Using 'compact'.")
            self._print_phase_compact()

    def do_set_tx_mode(self, arg):
        """set_tx_mode <mode> - Set TX wave type (auto|plane|spherical)

        Modes:
          auto       - Automatic selection based on Fraunhofer boundary
          plane      - Plane wave (far-field TX)
          spherical  - Spherical wave (near-field TX)

        Examples:
          set_tx_mode auto
          set_tx_mode plane
          set_tx_mode spherical
        """
        if not arg:
            print("Usage: set_tx_mode <auto|plane|spherical>")
            return

        mode = arg.strip().lower()
        result = self.ris_node.set_tx_mode(mode)

        if result['status'] == 'success':
            print(f"✓ TX mode set to: {mode}")
            print(f"  plane_tx = {result['plane_tx']}")
        else:
            print(f"✗ Error: {result.get('message', 'Unknown error')}")

    def do_set_rx_mode(self, arg):
        """set_rx_mode <mode> - Set RX wave type (auto|plane|steer|spherical|focus)

        Modes:
          auto       - Automatic selection based on Fraunhofer boundary
          plane      - Plane wave, beam steering (far-field RX)
          steer      - Alias for 'plane'
          spherical  - Spherical wave, point focusing (near-field RX)
          focus      - Alias for 'spherical'

        Examples:
          set_rx_mode auto
          set_rx_mode plane
          set_rx_mode focus
        """
        if not arg:
            print("Usage: set_rx_mode <auto|plane|steer|spherical|focus>")
            return

        mode = arg.strip().lower()
        result = self.ris_node.set_rx_mode(mode)

        if result['status'] == 'success':
            print(f"✓ RX mode set to: {mode}")
            print(f"  plane_rx = {result['plane_rx']}")
        else:
            print(f"✗ Error: {result.get('message', 'Unknown error')}")

    def do_wave_mode(self, arg):
        """wave_mode [info] - Show current wave mode configuration

        Display TX/RX wave types and Fraunhofer boundary information.
        Shows auto-selection results from last phase computation.

        Example:
          wave_mode
          wave_mode info
        """
        info = self.ris_node.get_hybrid_mode_info()

        print(f"\n{self.ris_node.name} Wave Mode Configuration:")
        print(f"  Hybrid Engine:  {'Enabled' if info['use_hybrid_engine'] else 'Disabled (Legacy)'}")
        print(f"  TX Mode:        {info['tx_mode']}")
        print(f"  RX Mode:        {info['rx_mode']}")

        if 'fraunhofer_boundary_m' in info:
            print(f"\nFraunhofer Boundary: {info['fraunhofer_boundary_m']:.3f} m")

        if 'dist_ap_to_ris_m' in info:
            print(f"  AP to RIS:      {info['dist_ap_to_ris_m']:.3f} m")

        if 'dist_ris_to_ue_m' in info:
            print(f"  RIS to UE:      {info['dist_ris_to_ue_m']:.3f} m")

        if 'last_tx_mode_used' in info:
            print(f"\nLast Phase Computation:")
            print(f"  TX Used:        {info['last_tx_mode_used']}")
            print(f"  RX Used:        {info['last_rx_mode_used']}")

            # Show mode description
            from controller.ris_phase.phase_hybrid import HybridPhaseEngine
            plane_tx_used = (info['last_tx_mode_used'] == 'plane')
            plane_rx_used = (info['last_rx_mode_used'] == 'plane')
            desc = HybridPhaseEngine.get_mode_description(plane_tx_used, plane_rx_used)
            print(f"  Description:    {desc}")

        print()

    def do_exit(self, arg):
        """exit - Exit RIS shell"""
        print(f"Exiting {self.ris_node.name} shell\n")
        return True

    def _print_status(self):
        """Print RIS node status"""
        print(f"\n{self.ris_node.name} Status:")
        print(f"  Position:     ({self.ris_node.pos[0]:.2f}, {self.ris_node.pos[1]:.2f}, {self.ris_node.pos[2]:.2f})")
        print(f"  Grid Size (N): {self.ris_node.N}")
        print(f"  Phase Bits:    {self.ris_node.bits}")
        print(f"  Phase States:  {2**self.ris_node.bits}")
        print(f"  Field of View: ±{self.ris_node.max_angle_deg}°")
        print(f"  Active:        Yes")

    def _load_phases_from_result(self, connect_result):
        """Load phase data and beam angles from connect() result into RIS node"""
        try:
            if 'current_phases' in connect_result:
                self.ris_node.current_phases = np.array(connect_result['current_phases'])
            if 'quantized_phases' in connect_result:
                self.ris_node.quantized_phases = np.array(connect_result['quantized_phases'])
            if 'phase_states' in connect_result:
                self.ris_node.phase_states = np.array(connect_result['phase_states'])

            # Load beam angle attributes from metrics or summary
            metrics = connect_result.get('metrics', {})
            summary = connect_result.get('summary', {})

            # Try to get local deflection from metrics (set by network.connect)
            if 'local_deflection_deg' in metrics:
                self.ris_node.local_beam_deflection_deg = float(metrics['local_deflection_deg'])
            # Try to get absolute angle from metrics
            if 'beam_angle' in metrics:
                self.ris_node.abs_beam_angle_deg = float(metrics['beam_angle'])
            elif 'beam_angle_deg' in summary:
                self.ris_node.abs_beam_angle_deg = float(summary['beam_angle_deg'])
            # Try to get specular angle from metrics
            if 'ris_normal_angle_deg' in metrics:
                self.ris_node.specular_angle_deg = float(metrics['ris_normal_angle_deg'])
        except Exception as e:
            print(f"Warning: Could not load phase data: {e}")

    def _print_phase_stats(self):
        """Print phase statistics"""
        ideal_deg = np.degrees(self.ris_node.current_phases)

        print(f"\n{self.ris_node.name} Phase Statistics:")
        print(f"  Ideal Phases (degrees):")
        print(f"    Min:  {np.min(ideal_deg):7.2f}°")
        print(f"    Max:  {np.max(ideal_deg):7.2f}°")
        print(f"    Mean: {np.mean(ideal_deg):7.2f}°")
        print(f"    Std:  {np.std(ideal_deg):7.2f}°")

        if self.ris_node.quantized_phases is not None:
            quantized_deg = np.degrees(self.ris_node.quantized_phases)
            quant_error = self._wrapped_phase_error(ideal_deg, quantized_deg)

            print(f"\n  Quantized Phases (degrees):")
            print(f"    Min:  {np.min(quantized_deg):7.2f}°")
            print(f"    Max:  {np.max(quantized_deg):7.2f}°")
            print(f"    Mean: {np.mean(quantized_deg):7.2f}°")
            print(f"    Std:  {np.std(quantized_deg):7.2f}°")

            print(f"\n  Quantization Error (ideal - quantized):")
            print(f"    Max Error:  {np.max(np.abs(quant_error)):7.2f}°")
            print(f"    Mean Error: {np.mean(np.abs(quant_error)):7.2f}°")
            print(f"    RMS Error:  {np.sqrt(np.mean(quant_error**2)):7.2f}°")

        self._print_angle_metadata()

    def _print_phase_compact(self):
        """Print phases in compact format"""
        if self.ris_node.quantized_phases is not None:
            phases = np.degrees(self.ris_node.quantized_phases)
            title = "Quantized Phases"
        else:
            phases = np.degrees(self.ris_node.current_phases)
            title = "Ideal Phases"

        print(f"\n{self.ris_node.name} {title} (compact, degrees):")
        print("  [", end="")
        for i, p in enumerate(phases):
            if i > 0 and i % 8 == 0:
                print("\n   ", end="")
            print(f"{p:6.1f}°", end=" ")
        print("]")

    def _print_phase_grid(self):
        """Print phases as N×N grid"""
        if self.ris_node.quantized_phases is not None:
            phases = np.degrees(self.ris_node.quantized_phases)
            title = "Quantized Phases"
        else:
            phases = np.degrees(self.ris_node.current_phases)
            title = "Ideal Phases"

        phases_grid = phases.reshape(self.ris_node.N, self.ris_node.N)

        print(f"\n{self.ris_node.name} {title} Grid ({self.ris_node.N}×{self.ris_node.N}):")
        print(f"  Bits: {self.ris_node.bits}, States: {2**self.ris_node.bits}\n")

        # Print column headers
        print("     ", end="")
        for j in range(self.ris_node.N):
            print(f"  [Col{j:2d}] ", end="")
        print()

        # Print grid with row headers
        for i in range(self.ris_node.N):
            print(f"[R{i:2d}]", end="")
            for j in range(self.ris_node.N):
                phase = phases_grid[i][j]
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

    def _plot_phase_grid(self, filename=None):
        """Plot RIS phase grid as heatmap"""
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            print("✗ matplotlib not installed. Install with: pip install matplotlib")
            return

        bits_value = getattr(self.ris_node, 'bits', 1) or 1
        try:
            bits_int = int(bits_value)
        except (TypeError, ValueError):
            bits_int = 1
        states = max(1, 2 ** bits_int)
        phase_step_deg = 360.0 / states
        quantized_range_max = 0.0 if states == 1 else (states - 1) * phase_step_deg

        quantized_mode = self.ris_node.quantized_phases is not None
        if quantized_mode:
            phases = np.degrees(self.ris_node.quantized_phases)
            title_suffix = "Quantized Phases"
            colorbar_max = quantized_range_max if quantized_range_max > 0 else phase_step_deg
        else:
            phases = np.degrees(self.ris_node.current_phases)
            title_suffix = "Ideal Phases"
            colorbar_max = 360.0

        # Ensure meaningful color span even for degenerate ranges
        if colorbar_max <= 0:
            data_max = float(np.max(phases)) if phases.size else 360.0
            colorbar_max = data_max if data_max > 0 else 360.0

        grid_size = self.ris_node.N
        total_elements = grid_size * grid_size
        phases_grid = phases.reshape(grid_size, grid_size)

        # Detect wave mode
        wave_mode = self._detect_wave_mode()
        phase_pattern_desc = self._describe_phase_pattern(phases_grid, states, wave_mode)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Use truncated/discrete HSV colormap to emphasize quantization levels
        base_cmap = None
        norm = None
        try:
            import matplotlib.colors as mcolors
            base_cmap = plt.cm.get_cmap('hsv')
            if quantized_mode:
                # Create discrete colors per quantization state
                sample_points = np.linspace(0.0, 1.0, states, endpoint=False) if states > 0 else [0.0]
                cmap = mcolors.ListedColormap(base_cmap(sample_points if len(sample_points) > 0 else [0.0]))
                upper_bound = colorbar_max if colorbar_max > 0 else phase_step_deg
                boundaries = np.linspace(-phase_step_deg / 2.0,
                                         upper_bound + phase_step_deg / 2.0,
                                         len(sample_points) + 1)
                # Avoid duplicate boundaries when only one sample exists
                if len(boundaries) < 2:
                    boundaries = np.array([-phase_step_deg / 2.0, phase_step_deg / 2.0])
                norm = mcolors.BoundaryNorm(boundaries, cmap.N)
            elif colorbar_max < 360.0:
                upper = min(0.999, colorbar_max / 360.0)
                sample_points = np.linspace(0.0, upper, 256)
                cmap = mcolors.LinearSegmentedColormap.from_list(
                    'hsv_truncated', base_cmap(sample_points))
            else:
                cmap = base_cmap
        except Exception:
            cmap = 'hsv'

        # Plot 1: Heatmap
        im_kwargs = {'cmap': cmap, 'aspect': 'auto'}
        if norm is not None:
            im_kwargs['norm'] = norm
        else:
            im_kwargs['vmin'] = 0
            im_kwargs['vmax'] = colorbar_max
        im = axes[0].imshow(phases_grid, **im_kwargs)
        axes[0].set_title(f'{self.ris_node.name} - {title_suffix} Heatmap\n({grid_size}×{grid_size}, {self.ris_node.bits}-bit)',
                         fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Column')
        axes[0].set_ylabel('Row')
        # Overlay grid lines to emphasize element boundaries
        axes[0].set_xticks(np.arange(-0.5, grid_size, 1), minor=True)
        axes[0].set_yticks(np.arange(-0.5, grid_size, 1), minor=True)
        axes[0].grid(which='minor', color='black', linewidth=0.25, alpha=0.6)
        axes[0].tick_params(which='minor', length=0)
        axes[0].set_xticks(np.arange(0, grid_size, max(1, grid_size // 8)))
        axes[0].set_yticks(np.arange(0, grid_size, max(1, grid_size // 8)))
        cbar = plt.colorbar(im, ax=axes[0])
        cbar.set_label('Phase (degrees)', rotation=270, labelpad=20)
        if quantized_mode:
            unique_levels = np.unique(np.round(phases, 6))
            if unique_levels.size > 0:
                cbar_ticks = unique_levels
            else:
                cbar_ticks = np.linspace(0.0, colorbar_max, max(states, 2))
            cbar.set_ticks(cbar_ticks)
            cbar.set_ticklabels([f"{val:.0f}°" for val in cbar_ticks])

        # Plot 2: Statistics (configuration only)
        axes[1].axis('off')

        metrics_block = self.last_connect_result if isinstance(self.last_connect_result, dict) else {}
        metrics_data = metrics_block.get('metrics') if isinstance(metrics_block.get('metrics'), dict) else {}
        summary_data = metrics_block.get('summary') if isinstance(metrics_block.get('summary'), dict) else {}

        def _get_metric_value(*keys):
            for key in keys:
                if key in metrics_data and metrics_data[key] is not None:
                    return metrics_data[key]
                if key in summary_data and summary_data.get(key) is not None:
                    return summary_data[key]
            return None

        def _fmt_metric(value, unit=""):
            if value is None:
                return "N/A"
            return f"{float(value):7.2f}{unit}"

        snr_str = _fmt_metric(_get_metric_value('snr_dB'), ' dB')
        power_str = _fmt_metric(_get_metric_value('pwr_dBm', 'rssi_dBm'), ' dBm')
        gain_str = _fmt_metric(_get_metric_value('gain_dBi'), ' dBi')
        quant_loss_val = _get_metric_value('quant_loss_dB')
        if quant_loss_val is None:
            quant_loss_str = "N/A"
        else:
            quant_penalty = abs(float(quant_loss_val))
            quant_loss_str = f"+{quant_penalty:.2f} dB (ΔSNR = {float(quant_loss_val):+.2f} dB)"

        phase_range_text = "Full 0°–360° sweep"
        if quantized_mode:
            if colorbar_max > 0:
                phase_range_text = f"0°–{colorbar_max:.2f}°"
            else:
                phase_range_text = "Single-level (0°)"

        stats_text = f"""
RIS NODE: {self.ris_node.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION:
  Grid Size (N):     {grid_size}×{grid_size}
  Total Elements:    {total_elements}
  Element Formula:   N_elements = N² = {grid_size}² = {total_elements}
  Phase Bits:        {self.ris_node.bits}
  Quantization States: {2**self.ris_node.bits}
  Phase Step:        {phase_step_deg:.2f}°
  Phase Range:       {phase_range_text}
  Wave Mode:         {wave_mode}
  Phase Pattern:     {phase_pattern_desc}
  Colorbar Levels:   {f'{states} discrete state(s)' if quantized_mode else 'Continuous gradient'}

PERFORMANCE METRICS:
  SNR:               {snr_str}
  Power:             {power_str}
  Gain:              {gain_str}
  Quantization Pen.: {quant_loss_str}
{self._angle_metadata_text()}
"""

        axes[1].text(0.05, 0.95, stats_text, transform=axes[1].transAxes,
                     fontsize=10, verticalalignment='top', fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()

        if filename:
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            print(f"✓ Phase grid exported to: {filename}")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"{self.ris_node.name}_phases_{timestamp}.png"
            plt.savefig(default_filename, dpi=150, bbox_inches='tight')
            print(f"✓ Phase grid exported to: {default_filename}")

        try:
            plt.show()
        except:
            pass

    @staticmethod
    def _wrapped_phase_error(ideal_deg, quantized_deg):
        """Compute wrapped phase error (degrees) in range [-180, 180]."""
        diff = ideal_deg - quantized_deg
        return ((diff + 180.0) % 360.0) - 180.0

    def _get_angle_metadata(self):
        return {
            'abs': getattr(self.ris_node, 'abs_beam_angle_deg', None),
            'spec': getattr(self.ris_node, 'specular_angle_deg', None),
            'local': getattr(self.ris_node, 'local_beam_deflection_deg', None)
        }

    def _print_angle_metadata(self):
        meta = self._get_angle_metadata()
        if all(value is None for value in meta.values()):
            return

        print(f"\n  Beam Orientation:")
        if meta['local'] is not None:
            direction_desc = "right" if meta['local'] > 0 else "left" if meta['local'] < 0 else "center"
            print(f"    Steering Angle (Deflection): {meta['local']:7.2f}°  ({direction_desc})")
        if meta['abs'] is not None:
            print(f"    (Global frame):             {meta['abs']:7.2f}°")
        if meta['spec'] is not None:
            print(f"    RIS Target (Specular):      {meta['spec']:7.2f}°")

    def _angle_metadata_text(self, indent='  '):
        meta = self._get_angle_metadata()
        if all(value is None for value in meta.values()):
            return ""

        lines = [f"{indent}Beam Orientation:"]
        if meta['local'] is not None:
            direction_desc = "right" if meta['local'] > 0 else "left" if meta['local'] < 0 else "center"
            lines.append(f"{indent}  Steering Angle (Deflection): {meta['local']:7.2f}°  ({direction_desc})")
        if meta['abs'] is not None:
            lines.append(f"{indent}  (Global frame):             {meta['abs']:7.2f}°")
        if meta['spec'] is not None:
            lines.append(f"{indent}  RIS Target (Specular):      {meta['spec']:7.2f}°")
        return "\n" + "\n".join(lines)

    def _describe_phase_pattern(self, phases_grid, states, wave_mode):
        """Provide quick description of quantized phase map characteristics."""
        if phases_grid is None:
            return "Not available"

        unique_levels = np.unique(np.round(phases_grid, 2))
        unique_count = unique_levels.size
        wave_desc = wave_mode if isinstance(wave_mode, str) else "Unknown"
        wave_phrase = wave_desc.lower()

        if self.ris_node.quantized_phases is not None:
            if states == 2 and unique_count <= 2:
                if wave_mode == "Plane Wave":
                    return "1-bit 0°/180° stripes approximating a linear ramp"
                return "1-bit 0°/180° pattern with spatial variation (spherical-phase steering)"
            return f"{unique_count} unique level(s) across {states}-state quantizer"

        return f"Continuous {wave_phrase} ramp with ~{unique_count} sampled bins"

    def _detect_wave_mode(self):
        """Detect if phase pattern is plane wave or spherical wave

        Returns:
            str: 'Plane Wave' or 'Spherical Wave' based on phase gradient analysis
        """
        if self.ris_node.current_phases is None:
            return "Unknown"

        phases = self.ris_node.current_phases
        N = self.ris_node.N
        phases_2d = phases.reshape((N, N))

        # For plane waves: all rows should have the same phase pattern (tiled 1D array)
        # For spherical waves: phase pattern varies across 2D grid

        # Check if rows are repetitive (plane wave characteristic)
        row_0 = phases_2d[0, :]
        row_1 = phases_2d[1, :] if N > 1 else row_0
        row_diff = np.abs(row_0 - row_1)

        # Unwrap phase differences to handle wrapping
        row_diff = np.where(row_diff > np.pi, 2*np.pi - row_diff, row_diff)

        # For plane waves, rows should be nearly identical (low difference)
        row_similarity = np.mean(row_diff)

        # Also check column differences
        col_0 = phases_2d[:, 0]
        col_1 = phases_2d[:, 1] if N > 1 else col_0

        # Check if column 0 and 1 have consistent linear progression
        col_0_grad = np.diff(col_0)
        col_1_grad = np.diff(col_1)

        # Unwrap gradient differences
        grad_diff = np.abs(col_0_grad - col_1_grad)
        grad_diff = np.where(grad_diff > np.pi, 2*np.pi - grad_diff, grad_diff)

        grad_consistency = np.mean(grad_diff)

        # Plane wave: low row difference + consistent column gradient
        # Threshold empirically determined
        if row_similarity < 0.3 and grad_consistency < 0.3:
            return "Plane Wave"
        else:
            return "Spherical Wave"

    def _print_phase_codebook(self):
        """Print phase state codebook (0, 1, 2, ... for each element)"""
        if not hasattr(self.ris_node, 'phase_states') or self.ris_node.phase_states is None:
            print("✗ No phase states available. Quantized phases required.")
            return

        phase_states = self.ris_node.phase_states
        N = self.ris_node.N
        bits = getattr(self.ris_node, 'bits', 1) or 1
        num_levels = 2 ** bits

        print(f"\n{self.ris_node.name} Phase Codebook ({bits}-bit, {num_levels} levels):")
        print(f"  Array size: {N}×{N} = {N*N} elements")
        print()

        # Show codebook as grid
        phase_states_grid = phase_states.reshape((N, N))
        print("Codebook Grid (state values):")
        for i in range(N):
            print("  ", end="")
            for j in range(N):
                state = int(phase_states_grid[i, j])
                print(f"[{state}]", end=" ")
            print()

        print()

        # Show distribution
        print("Distribution:")
        for level in range(num_levels):
            count = np.sum(phase_states == level)
            percent = 100 * count / len(phase_states)
            phase_deg = (level * 360) // num_levels  # Convert state to degrees
            bar = "█" * int(percent // 5)
            print(f"  State {level} ({phase_deg:>3}°): {count:3d} elements ({percent:5.1f}%) {bar}")

        print()

        # Show linear codebook vector
        print("Linear Codebook Vector:")
        print(f"  {list(phase_states)}")

        print()

        # Show as hex
        codebook_binary = ''.join([str(int(x)) for x in phase_states])
        codebook_hex = hex(int(codebook_binary, 2))[2:].upper()
        # Pad to match expected length
        expected_hex_len = (N * N * bits + 3) // 4  # Round up to nearest nibble
        codebook_hex = codebook_hex.zfill(expected_hex_len)

        print("Hex Representation:")
        print(f"  0x{codebook_hex}")

        print()

        # Show byte-by-byte for transmission
        print("Transmission Format (hex bytes):")
        hex_bytes = ' '.join([codebook_hex[i:i+2] for i in range(0, len(codebook_hex), 2)])
        print(f"  {hex_bytes}")

    def _print_phase_transmit(self):
        """Print RIS transmission-ready format with checksum"""
        import binascii

        if not hasattr(self.ris_node, 'phase_states') or self.ris_node.phase_states is None:
            print("✗ No phase states available. Quantized phases required.")
            return

        phase_states = self.ris_node.phase_states
        N = self.ris_node.N
        bits = getattr(self.ris_node, 'bits', 1) or 1

        # Generate codebook hex
        codebook_binary = ''.join([str(int(x)) for x in phase_states])
        codebook_hex = hex(int(codebook_binary, 2))[2:].upper()
        expected_hex_len = (N * N * bits + 3) // 4
        codebook_hex = codebook_hex.zfill(expected_hex_len)

        # Calculate CRC32 checksum
        data_bytes = bytes.fromhex(codebook_hex)
        crc32_value = binascii.crc32(data_bytes) & 0xffffffff

        print(f"\n{self.ris_node.name} Transmission Format:")
        print("=" * 70)

        print()
        print("RAW CODEBOOK:")
        print(f"  Hex String: 0x{codebook_hex}")
        print(f"  Length: {len(codebook_hex) // 2} bytes ({N*N*bits} bits)")

        print()
        print("WITH CHECKSUM (CRC32):")
        print(f"  Checksum: 0x{crc32_value:08X}")
        print(f"  Data + CRC: {codebook_hex} {crc32_value:08X}")

        print()
        print("TRANSMISSION FRAME (UART/SPI):")
        stx = "0xAA"  # Start of transmission
        etx = "0x55"  # End of transmission
        length = len(codebook_hex) // 2
        print(f"  [STX] [LEN] [DATA...] [CRC] [ETX]")
        print(f"  {stx}   {length:02X}   {codebook_hex}   {crc32_value:08X}   {etx}")

        print()
        print("BYTE-BY-BYTE (for transmission):")
        hex_bytes = ' '.join([codebook_hex[i:i+2] for i in range(0, len(codebook_hex), 2)])
        print(f"  {hex_bytes}")

        print()
        print("BASE64 ENCODING (for wireless):")
        b64_data = __import__('base64').b64encode(data_bytes).decode('ascii')
        print(f"  {b64_data}")

        print()
        print("JSON FORMAT (with metadata):")
        import json
        json_data = {
            "ris_name": self.ris_node.name,
            "array_size": N,
            "bits": bits,
            "codebook_hex": codebook_hex,
            "length_bytes": length,
            "checksum_crc32": f"0x{crc32_value:08X}",
            "timestamp": str(datetime.now())
        }
        print(f"  {json.dumps(json_data, indent=2)}")

    def _export_phases(self, filename, format_type):
        """Export phase codebook to file"""
        import json
        import binascii

        if not hasattr(self.ris_node, 'phase_states') or self.ris_node.phase_states is None:
            print("✗ No phase states available. Quantized phases required.")
            return

        phase_states = self.ris_node.phase_states
        N = self.ris_node.N
        bits = getattr(self.ris_node, 'bits', 1) or 1

        try:
            if format_type == 'hex':
                # Export as hex string
                codebook_binary = ''.join([str(int(x)) for x in phase_states])
                codebook_hex = hex(int(codebook_binary, 2))[2:].upper()
                expected_hex_len = (N * N * bits + 3) // 4
                codebook_hex = codebook_hex.zfill(expected_hex_len)

                with open(filename, 'w') as f:
                    f.write(codebook_hex)

                print(f"✓ Exported codebook to {filename} (hex format)")
                print(f"  Length: {len(codebook_hex) // 2} bytes")

            elif format_type == 'binary':
                # Export as binary string
                codebook_binary = ''.join([str(int(x)) for x in phase_states])
                with open(filename, 'w') as f:
                    f.write(codebook_binary)

                print(f"✓ Exported codebook to {filename} (binary format)")
                print(f"  Length: {len(codebook_binary)} bits")

            elif format_type == 'csv':
                # Export as CSV table
                phase_states_grid = phase_states.reshape((N, N))
                with open(filename, 'w') as f:
                    for i in range(N):
                        f.write(','.join([str(int(x)) for x in phase_states_grid[i, :]]) + '\n')

                print(f"✓ Exported codebook to {filename} (CSV format)")
                print(f"  Grid: {N}×{N}")

            elif format_type == 'json':
                # Export as JSON with metadata
                codebook_binary = ''.join([str(int(x)) for x in phase_states])
                codebook_hex = hex(int(codebook_binary, 2))[2:].upper()
                expected_hex_len = (N * N * bits + 3) // 4
                codebook_hex = codebook_hex.zfill(expected_hex_len)

                data_bytes = bytes.fromhex(codebook_hex)
                crc32_value = binascii.crc32(data_bytes) & 0xffffffff

                json_data = {
                    "ris_name": self.ris_node.name,
                    "array_size": int(N),
                    "bits": int(bits),
                    "num_states": int(2 ** bits),
                    "codebook_hex": codebook_hex,
                    "codebook_binary": codebook_binary,
                    "codebook_array": [int(x) for x in phase_states],
                    "length_bytes": len(codebook_hex) // 2,
                    "checksum_crc32": f"0x{crc32_value:08X}",
                    "timestamp": str(datetime.now())
                }

                with open(filename, 'w') as f:
                    json.dump(json_data, f, indent=2)

                print(f"✓ Exported codebook to {filename} (JSON format)")
                print(f"  Contains: hex, binary, array, metadata, checksum")

            else:
                print(f"✗ Unknown export format: {format_type}")
                print(f"  Supported formats: hex, binary, csv, json")

        except IOError as e:
            print(f"✗ Error writing to file: {e}")
