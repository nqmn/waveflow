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
        self._print_status()
        print("\nAvailable commands: help, status, config, info, phases, exit")
        print("Type 'help' for more information\n")

    def do_help(self, arg):
        """help [command] - Show help"""
        if arg:
            return super().do_help(arg)

        help_text = """
RIS Node Commands:
  help              - Show this help message
  status            - Show current RIS status
  info              - Show detailed RIS information
  config [set]      - Show or modify RIS configuration
  phases [format]   - Display phase element values
  exit              - Exit RIS shell
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
        Formats: grid, compact, stats, plot
        """
        if self.ris_node.current_phases is None:
            print(f"✗ No phase configuration computed yet.")
            print(f"  Run 'connect' command first to compute phases.")
            return

        format_type = arg.lower() if arg else 'grid'

        if format_type == 'stats':
            self._print_phase_stats()
        elif format_type == 'compact':
            self._print_phase_compact()
        elif format_type == 'plot':
            self._plot_phase_grid()
        else:  # 'grid' or default
            self._print_phase_grid()

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
            quant_error = ideal_deg - quantized_deg

            print(f"\n  Quantized Phases (degrees):")
            print(f"    Min:  {np.min(quantized_deg):7.2f}°")
            print(f"    Max:  {np.max(quantized_deg):7.2f}°")
            print(f"    Mean: {np.mean(quantized_deg):7.2f}°")
            print(f"    Std:  {np.std(quantized_deg):7.2f}°")

            print(f"\n  Quantization Error (ideal - quantized):")
            print(f"    Max Error:  {np.max(np.abs(quant_error)):7.2f}°")
            print(f"    Mean Error: {np.mean(np.abs(quant_error)):7.2f}°")
            print(f"    RMS Error:  {np.sqrt(np.mean(quant_error**2)):7.2f}°")

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

        if self.ris_node.quantized_phases is not None:
            phases = np.degrees(self.ris_node.quantized_phases)
            title_suffix = "Quantized Phases"
        else:
            phases = np.degrees(self.ris_node.current_phases)
            title_suffix = "Ideal Phases"

        phases_grid = phases.reshape(self.ris_node.N, self.ris_node.N)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Plot 1: Heatmap
        im = axes[0].imshow(phases_grid, cmap='hsv', vmin=0, vmax=360, aspect='auto')
        axes[0].set_title(f'{self.ris_node.name} - {title_suffix} Heatmap\n({self.ris_node.N}×{self.ris_node.N}, {self.ris_node.bits}-bit)',
                         fontsize=12, fontweight='bold')
        axes[0].set_xlabel('Column')
        axes[0].set_ylabel('Row')

        cbar = plt.colorbar(im, ax=axes[0])
        cbar.set_label('Phase (degrees)', rotation=270, labelpad=20)

        # Plot 2: Statistics
        axes[1].axis('off')

        if self.ris_node.quantized_phases is not None:
            ideal_deg = np.degrees(self.ris_node.current_phases)
            quantized_deg = np.degrees(self.ris_node.quantized_phases)
            quant_error = ideal_deg - quantized_deg

            stats_text = f"""
RIS NODE: {self.ris_node.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION:
  Grid Size (N):     {self.ris_node.N}×{self.ris_node.N}
  Total Elements:    {self.ris_node.N * self.ris_node.N}
  Phase Bits:        {self.ris_node.bits}
  Quantization States: {2**self.ris_node.bits}
  Phase Step:        {360 / (2**self.ris_node.bits):.2f}°

IDEAL PHASES:
  Min:    {np.min(ideal_deg):7.2f}°
  Max:    {np.max(ideal_deg):7.2f}°
  Mean:   {np.mean(ideal_deg):7.2f}°
  Std:    {np.std(ideal_deg):7.2f}°

QUANTIZED PHASES:
  Min:    {np.min(quantized_deg):7.2f}°
  Max:    {np.max(quantized_deg):7.2f}°
  Mean:   {np.mean(quantized_deg):7.2f}°
  Std:    {np.std(quantized_deg):7.2f}°

QUANTIZATION ERROR:
  Max Error:  {np.max(np.abs(quant_error)):7.2f}°
  Mean Error: {np.mean(np.abs(quant_error)):7.2f}°
  RMS Error:  {np.sqrt(np.mean(quant_error**2)):7.2f}°
            """
        else:
            ideal_deg = np.degrees(self.ris_node.current_phases)
            stats_text = f"""
RIS NODE: {self.ris_node.name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONFIGURATION:
  Grid Size (N):     {self.ris_node.N}×{self.ris_node.N}
  Total Elements:    {self.ris_node.N * self.ris_node.N}
  Phase Bits:        {self.ris_node.bits}
  Quantization States: {2**self.ris_node.bits}
  Phase Step:        {360 / (2**self.ris_node.bits):.2f}°

IDEAL PHASES:
  Min:    {np.min(ideal_deg):7.2f}°
  Max:    {np.max(ideal_deg):7.2f}°
  Mean:   {np.mean(ideal_deg):7.2f}°
  Std:    {np.std(ideal_deg):7.2f}°

(No quantization applied)
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
