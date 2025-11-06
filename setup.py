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


class RISNetSetup:
    """Handle RISNet installation and setup"""

    def __init__(self):
        self.project_root = Path(__file__).parent.absolute()
        self.risnet_script = self.project_root / "risnet"
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
        """Install missing packages"""
        if not packages:
            print("\n✓ All dependencies already installed")
            return True

        self.print_header("Installing Dependencies")
        print(f"Installing: {', '.join(packages)}\n")

        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + packages
            )
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

        profile = self.find_shell_profile()
        path_export = f'export PATH="{self.project_root}:$PATH"'
        path_comment = "# RISNet installation"

        print(f"Shell profile: {profile}")
        print(f"Adding to PATH: {self.project_root}\n")

        # Check if already in PATH
        if profile.exists():
            content = profile.read_text()
            if str(self.project_root) in content:
                print("✓ RISNet already in PATH")
                return True

        # Add to PATH
        try:
            with open(profile, "a") as f:
                f.write(f"\n{path_comment}\n{path_export}\n")
            print(f"✓ Added to {profile.name}")
            print(f"\n  Command: {path_export}")
            return True
        except Exception as e:
            print(f"❌ Failed to add to PATH: {e}")
            return False

    def test_risnet_command(self):
        """Test if risnet command works"""
        self.print_header("Testing RISNet Command")

        # Test 1: Via python
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

        # Test 2: Load topology
        print("Test 2: Load topology")
        topology_file = (
            self.project_root
            / "examples/json_topologies/example_1_simple.json"
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
                    print(f"  Command: python3 main.py --topology examples/json_topologies/example_1_simple.json list\n")
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
        print(f"   cd {self.project_root}")
        print(f"   python3 main.py --topology examples/json_topologies/example_1_simple.json list\n")

        print("USEFUL COMMANDS:")
        print("   python3 main.py               # Interactive mode")
        print("   python3 main.py list          # List nodes")
        print("   python3 main.py add ap        # Add access point")
        print("   python3 main.py add ris       # Add RIS surface")
        print("   python3 main.py add ue        # Add user equipment")
        print("   python3 main.py save network.json  # Save topology")
        print("   python3 main.py --topology examples/json_topologies/example_1_simple.json list")

        print("\nDOCUMENTATION:")
        print("   - docs_archive/SETUP.md       # Setup guide")
        print("   - examples/json_topologies/README.md")
        print("   - examples/json_topologies/LOADING_GUIDE.md")

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
