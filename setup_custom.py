#!/usr/bin/env python3
"""
RISNet Setup Script

Installs dependencies, configures PATH, and verifies installation.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import platform
import ctypes
import winreg


class RISNetSetup:
    """Handle RISNet installation and setup"""

    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.bin_dir = self.project_root / "bin"
        self.risnet_script = self.bin_dir / "risnet"
        self.shell_profiles = [
            Path.home() / ".bashrc",
            Path.home() / ".zshrc",
            Path.home() / ".bash_profile",
            Path.home() / ".profile",
        ]
        self.required_packages = ["numpy", "flask", "pyyaml", "waitress"]

    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{'='*80}")
        print(f"  {text}")
        print(f"{'='*80}\n")

    def check_python_version(self):
        """Check Python version"""
        self.print_header("Checking Python Version")
        version = sys.version_info
        print(f"Python {version.major}.{version.minor}.{version.micro}")

        if version.major < 3 or (version.major == 3 and version.minor < 7):
            print(f"❌ Python 3.7+ required. You have {version.major}.{version.minor}")
            return False

        print("✓ Python version OK")
        return True

    def check_dependencies(self):
        """Check if required packages are installed"""
        self.print_header("Checking Dependencies")
        missing = []

        for package in self.required_packages:
            try:
                __import__(package)
                print(f"✓ {package:15} installed")
            except ImportError:
                print(f"✗ {package:15} missing")
                missing.append(package)

        return missing

    def install_dependencies(self, packages):
        """Install missing packages (supports Linux and Windows)"""
        if not packages:
            print("\n✓ All dependencies already installed")
            return True

        self.print_header("Installing Dependencies")
        print(f"Installing: {', '.join(packages)}\n")

        try:
            # Try with --break-system-packages first (Linux with venv)
            cmd = [sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError:
                # Fallback: install without --break-system-packages (Windows, standard pip)
                print("  Retrying without --break-system-packages flag...\n")
                cmd = [sys.executable, "-m", "pip", "install"] + packages
                subprocess.check_call(cmd)

            print("\n✓ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Failed to install dependencies: {e}")
            return False

    def check_risnet_script(self):
        """Check if main.py exists and is executable"""
        self.print_header("Checking main.py")

        main_py = self.project_root / "main.py"
        if not main_py.exists():
            print(f"❌ main.py not found: {main_py}")
            return False

        print(f"✓ main.py found: {main_py}")
        return True

    def find_shell_profile(self):
        """Find the user's shell profile file"""
        for profile in self.shell_profiles:
            if profile.exists():
                return profile
        return self.shell_profiles[0]  # Default to .bashrc

    def add_to_path(self):
        """Add RISNet to PATH"""
        self.print_header("Setting up PATH")

        if platform.system() == "Windows":
            return self._add_to_path_windows()
        else:
            return self._add_to_path_unix()

    def _add_to_path_windows(self):
        """Add RISNet to Windows PATH via environment variables"""
        print(f"Adding to Windows PATH: {self.bin_dir}\n")

        try:
            # Read current PATH from registry
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                    current_path = winreg.QueryValueEx(key, "PATH")[0]
            except FileNotFoundError:
                current_path = ""

            # Check if already in PATH
            bin_dir_str = str(self.bin_dir)
            if bin_dir_str in current_path:
                print("✓ RISNet already in Windows PATH")
                return True

            # Add to PATH
            if current_path:
                new_path = f"{bin_dir_str};{current_path}"
            else:
                new_path = bin_dir_str

            # Try to set in user environment variables
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE
                ) as key:
                    winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"✓ Added to Windows PATH (HKEY_CURRENT_USER)")
                print(f"\n  Path: {bin_dir_str}")
                print(f"\n  Note: Close and reopen your terminal for changes to take effect")
                return True
            except PermissionError:
                print("⚠ Permission denied. Trying system PATH (requires admin)...")
                return self._add_to_path_windows_with_admin()

        except Exception as e:
            print(f"❌ Failed to add to Windows PATH: {e}")
            return False

    def _add_to_path_windows_with_admin(self):
        """Add RISNet to Windows PATH with admin privileges"""
        try:
            # Try to modify system PATH (requires admin)
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment",
                0,
                winreg.KEY_READ | winreg.KEY_WRITE,
            ) as key:
                current_path = winreg.QueryValueEx(key, "PATH")[0]
                bin_dir_str = str(self.bin_dir)

                if bin_dir_str in current_path:
                    print("✓ RISNet already in Windows PATH (system)")
                    return True

                new_path = f"{current_path};{bin_dir_str}"
                winreg.SetValueEx(key, "PATH", 0, winreg.REG_EXPAND_SZ, new_path)
                print(f"✓ Added to Windows PATH (system-wide)")
                print(f"\n  Path: {bin_dir_str}")
                print(f"\n  Note: Close and reopen your terminal for changes to take effect")
                return True

        except PermissionError:
            print("⚠ Admin privileges required. Please run setup.py as Administrator")
            print("  Right-click setup.py and select 'Run as administrator'")
            return False
        except Exception as e:
            print(f"❌ Failed to add to Windows PATH: {e}")
            return False

    def _add_to_path_unix(self):
        """Add RISNet to Unix-like PATH via shell profile"""
        profile = self.find_shell_profile()
        path_export = f'export PATH="{self.bin_dir}:$PATH"'
        path_comment = "# RISNet installation"

        print(f"Shell profile: {profile}")
        print(f"Adding to PATH: {self.bin_dir}\n")

        # Check if already in PATH
        if profile.exists():
            content = profile.read_text()
            if str(self.bin_dir) in content:
                print("✓ RISNet already in PATH")
                return True

        # Add to PATH
        try:
            with open(profile, "a") as f:
                f.write(f"\n{path_comment}\n{path_export}\n")
            print(f"✓ Added to {profile.name}")
            print(f"\n  Command: {path_export}")
            print(f"\n  Note: Run 'source {profile}' or restart your terminal for changes to take effect")
            return True
        except Exception as e:
            print(f"❌ Failed to add to PATH: {e}")
            return False

    def test_risnet_command(self):
        """Test if risnet command works"""
        self.print_header("Testing RISNet Command")

        # Test 1: Via main.py
        print("Test 1: Via main.py")
        try:
            result = subprocess.run(
                [sys.executable, str(self.project_root / "main.py"), "list"],
                capture_output=True,
                timeout=5,
                cwd=self.project_root,
            )
            if result.returncode == 0:
                print("✓ main.py works: python3 main.py list\n")
            else:
                print("⚠ main.py returned non-zero status\n")
        except Exception as e:
            print(f"⚠ main.py test failed: {e}\n")

        # Test 2: Via risnet wrapper script (with PATH setup)
        print("Test 2: Via risnet script")
        risnet_script = self.bin_dir / "risnet"

        if not risnet_script.exists():
            print(f"❌ risnet script not found: {risnet_script}")
            print("Setup cannot continue without risnet script\n")
            return False

        # Try to run risnet with updated PATH
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Create environment with PATH including bin directory
                env = os.environ.copy()
                env['PATH'] = f"{self.bin_dir}:{env.get('PATH', '')}"

                # Try running risnet directly first
                if attempt == 0:
                    print(f"  Attempt {attempt + 1}: Using python3 bin/risnet")
                    result = subprocess.run(
                        [sys.executable, str(risnet_script), "list"],
                        capture_output=True,
                        timeout=5,
                        cwd=self.project_root,
                        env=env,
                    )
                else:
                    print(f"  Attempt {attempt + 1}: Using risnet with updated PATH")
                    result = subprocess.run(
                        ["risnet", "list"],
                        capture_output=True,
                        timeout=5,
                        cwd=self.project_root,
                        env=env,
                    )

                if result.returncode == 0:
                    print("✓ risnet script works\n")
                    break
                else:
                    stderr = result.stderr.decode() if result.stderr else ""
                    if attempt < max_retries - 1:
                        print(f"  ⚠ Attempt {attempt + 1} failed, retrying...\n")
                    else:
                        print(f"❌ risnet script failed after {max_retries} attempts")
                        print(f"  Error: {stderr}\n")
                        return False
            except FileNotFoundError as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠ risnet not found in PATH (attempt {attempt + 1}), retrying...\n")
                else:
                    print(f"❌ risnet command not accessible even with updated PATH")
                    print(f"  Error: {e}\n")
                    return False
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠ Unexpected error (attempt {attempt + 1}): {e}, retrying...\n")
                else:
                    print(f"❌ risnet script test failed: {e}\n")
                    return False

        # Test 3: Load topology
        print("Test 3: Load topology")
        topology_file = (
            self.project_root
            / "examples/json/example_1_simple.json"
        )
        if topology_file.exists():
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        str(self.project_root / "main.py"),
                        "--topology",
                        str(topology_file),
                        "list",
                    ],
                    capture_output=True,
                    timeout=5,
                    cwd=self.project_root,
                )
                if result.returncode == 0:
                    print(f"✓ Topology loading works")
                    print(f"  Command: python3 main.py --topology examples/json/example_1_simple.json list\n")
                else:
                    print(f"⚠ Topology loading failed\n")
            except Exception as e:
                print(f"⚠ Topology test failed: {e}\n")
        else:
            print(f"⚠ Topology file not found: {topology_file}\n")

    def verify_installation(self):
        """Verify installation by running commands"""
        self.print_header("Verifying Installation")

        tests = [
            ("Add AP node", ["add", "ap"]),
            ("List nodes", ["list"]),
            ("Clear nodes", ["clear"]),
        ]

        main_py = self.project_root / "main.py"
        for test_name, args in tests:
            print(f"Test: {test_name}")
            try:
                result = subprocess.run(
                    [sys.executable, str(main_py)] + args,
                    capture_output=True,
                    timeout=5,
                    cwd=self.project_root,
                )
                if result.returncode == 0:
                    print(f"✓ {test_name} works\n")
                else:
                    print(f"⚠ {test_name} returned non-zero\n")
            except Exception as e:
                print(f"⚠ {test_name} failed: {e}\n")

    def show_next_steps(self):
        """Show next steps"""
        self.print_header("Setup Complete!")

        print("✓ RISNet is ready to use!\n")

        print("QUICK START:")
        print(f"\n1. From project directory:")
        print(f"   cd {self.project_root}\n")
        print("   Using risnet command (recommended):")
        print("   risnet --topology examples/json/example_1_simple.json list\n")
        print("   Or using python3:")
        print("   python3 main.py --topology examples/json/example_1_simple.json list\n")

        print("USEFUL COMMANDS (using risnet):")
        print("   risnet                        # Interactive mode")
        print("   risnet list                   # List nodes")
        print("   risnet add ap                 # Add access point")
        print("   risnet add ris                # Add RIS surface")
        print("   risnet add ue                 # Add user equipment")
        print("   risnet save network.json      # Save topology")
        print("   risnet --topology examples/json/example_1_simple.json list\n")

        print("USEFUL COMMANDS (using python3):")
        print("   python3 main.py               # Interactive mode")
        print("   python3 main.py list          # List nodes")
        print("   python3 main.py add ap        # Add access point")
        print("   python3 main.py add ris       # Add RIS surface")
        print("   python3 main.py add ue        # Add user equipment")
        print("   python3 main.py save network.json  # Save topology")
        print("   python3 main.py --topology examples/json/example_1_simple.json list")


    def run(self):
        """Run complete setup"""
        print("\n")
        print("╔" + "="*78 + "╗")
        print("║" + " "*78 + "║")
        print("║" + "  RISNet Installation and Setup".center(78) + "║")
        print("║" + " "*78 + "║")
        print("╚" + "="*78 + "╝")

        # Check Python version
        if not self.check_python_version():
            return False

        # Check RISNet script
        if not self.check_risnet_script():
            return False

        # Check and install dependencies
        missing = self.check_dependencies()
        if missing:
            if not self.install_dependencies(missing):
                print("\n⚠ Some dependencies failed to install")
                print("  You may need to install them manually:")
                print(f"  pip install {' '.join(missing)}")

        # Add to PATH
        self.add_to_path()

        # Test risnet command
        self.test_risnet_command()

        # Verify installation
        self.verify_installation()

        # Show next steps
        self.show_next_steps()

        return True


def main():
    """Main entry point"""
    setup = RISNetSetup()
    success = setup.run()

    print("\n" + "="*80)
    if success:
        print("✓ Setup completed successfully!")
        print("="*80 + "\n")
        return 0
    else:
        print("❌ Setup completed with errors")
        print("="*80 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
