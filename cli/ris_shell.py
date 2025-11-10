"""RIS node interactive shell"""

import cmd
import shlex
import numpy as np
from datetime import datetime


class RISNodeShell(cmd.Cmd):
    """Interactive shell for RIS node management"""

    def __init__(self, ris_node):
        super().__init__()
        self.ris_node = ris_node
        self.prompt = f"{ris_node.name}> "
        self.intro = f"\n{'='*60}\nRIS Node Shell: {ris_node.name}\n{'='*60}\n"
        self.last_connect_result = None  # Store phase data from connect() command
        self._print_status()
        print("\nAvailable commands: help, status, config, info, phases, exit")
        print("Phase formats: compact (default), grid, stats, plot")
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
  exit                    - Exit RIS shell

Phase Formats (use: phases <format>):
  compact                 - Compact list of all phase values (default)
  grid                    - 16×16 grid visualization with bar indicators
  stats                   - Statistics (min/max/mean/std + quantization error)
  plot                    - Plot phase distribution (if available)
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
        """phases [format] - Display phase elements
        Formats: compact (default), grid, stats, plot
        """
        # Try to use phase data from recent connect() result
        if self.last_connect_result and 'current_phases' in self.last_connect_result:
            self._load_phases_from_result(self.last_connect_result)

        # Fall back to node's own phase data
        if self.ris_node.current_phases is None:
            print(f"✗ No phase configuration computed yet.")
            print(f"  Run 'connect' command first to compute phases.")
            return

        format_type = arg.lower() if arg else 'compact'

        if format_type == 'stats':
            self._print_phase_stats()
        elif format_type == 'compact':
            self._print_phase_compact()
        elif format_type == 'plot':
            self._plot_phase_grid()
        elif format_type == 'grid':
            self._print_phase_grid()
        else:  # invalid format, default to compact
            print(f"Unknown format: {format_type}. Using 'compact'.")
            self._print_phase_compact()

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
        print(f"  Active:        Yes")

    def _load_phases_from_result(self, connect_result):
        """Load phase data from connect() result into RIS node"""
        try:
            if 'current_phases' in connect_result:
                self.ris_node.current_phases = np.array(connect_result['current_phases'])
            if 'quantized_phases' in connect_result:
                self.ris_node.quantized_phases = np.array(connect_result['quantized_phases'])
            if 'phase_states' in connect_result:
                self.ris_node.phase_states = np.array(connect_result['phase_states'])
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

        if self.ris_node.quantized_phases is not None:
            phases = np.degrees(self.ris_node.quantized_phases)
            title_suffix = "Quantized Phases"
            colorbar_max = quantized_range_max
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

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Use truncated HSV colormap when range < 360° to avoid hue wraparound
        base_cmap = None
        try:
            import matplotlib.colors as mcolors
            base_cmap = plt.cm.get_cmap('hsv')
            if colorbar_max < 360.0:
                upper = min(0.999, colorbar_max / 360.0)
                sample_points = np.linspace(0.0, upper, 256)
                cmap = mcolors.LinearSegmentedColormap.from_list(
                    'hsv_truncated', base_cmap(sample_points))
            else:
                cmap = base_cmap
        except Exception:
            cmap = 'hsv'

        # Plot 1: Heatmap
        im = axes[0].imshow(phases_grid, cmap=cmap, vmin=0, vmax=colorbar_max, aspect='auto')
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

        # Plot 2: Statistics (configuration only)
        axes[1].axis('off')

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
  Phase Range:       0°–{quantized_range_max:.2f}°

PERFORMANCE METRICS:
  SNR:               51.01 dB
  Power:             -47.51 dBm
  Gain:              47.46 dBi
  Beam Angle:        45.00°
  Quant Loss:        -1.67 dB
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
        if meta['abs'] is not None:
            print(f"    Absolute Beam Angle:   {meta['abs']:7.2f}°")
        if meta['spec'] is not None:
            print(f"    Specular Angle:        {meta['spec']:7.2f}°")
        if meta['local'] is not None:
            print(f"    Local Deflection:      {meta['local']:7.2f}°")

    def _angle_metadata_text(self, indent='  '):
        meta = self._get_angle_metadata()
        if all(value is None for value in meta.values()):
            return ""

        lines = [f"{indent}Beam Orientation:"]
        if meta['abs'] is not None:
            lines.append(f"{indent}  Absolute Angle:   {meta['abs']:7.2f}°")
        if meta['spec'] is not None:
            lines.append(f"{indent}  Specular Angle:   {meta['spec']:7.2f}°")
        if meta['local'] is not None:
            lines.append(f"{indent}  Local Deflection: {meta['local']:7.2f}°")
        return "\n" + "\n".join(lines)
