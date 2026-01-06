#!/usr/bin/env python3
"""
IABuilder Universal Installer
Works on Linux, macOS, and Windows
Creates desktop shortcuts and interactive launcher
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

class IABuilderInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.script_dir = Path(__file__).parent.absolute()
        self.install_dir = self.get_install_dir()
        self.colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }

    def get_install_dir(self):
        """Get appropriate installation directory for each platform"""
        home = Path.home()

        if self.system == "linux":
            return home / ".local" / "share" / "iabuilder"
        elif self.system == "darwin":  # macOS
            return home / "Applications" / "IABuilder"
        elif self.system == "windows":
            return home / "AppData" / "Local" / "IABuilder"
        else:
            return home / ".iabuilder"

    def print_banner(self):
        """Print installation banner with platform icon"""
        banner = f"""
{self.colors['blue']}╔════════════════════════════════════════════════════════╗{self.colors['reset']}
{self.colors['blue']}║              {self.colors['green']}{self.colors['bold']}IABUILDER INSTALLER{self.colors['reset']}{self.colors['blue']}              ║{self.colors['reset']}
{self.colors['blue']}╚════════════════════════════════════════════════════════╝{self.colors['reset']}
"""
        print(banner)

    def check_python(self):
        """Check if Python 3.8+ is available"""
        print(f"{self.colors['blue']}🔍 Checking Python...{self.colors['reset']}")

        try:
            version = sys.version_info
            version_str = f"{version.major}.{version.minor}"

            if version >= (3, 8):
                print(f"{self.colors['green']}✅ Python {version_str} found{self.colors['reset']}")
                return True
            else:
                print(f"{self.colors['red']}❌ Python {version_str} is too old. Need Python 3.8+{self.colors['reset']}")
                return False

        except Exception as e:
            print(f"{self.colors['red']}❌ Python check failed: {e}{self.colors['reset']}")
            return False

    def check_disk_space(self):
        """Check if there's enough disk space (need ~200MB)"""
        try:
            # Get free space in MB
            stat = os.statvfs(str(self.script_dir))
            free_space_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

            if free_space_mb < 200:
                print(f"{self.colors['red']}❌ Not enough disk space. Need at least 200MB free.{self.colors['reset']}")
                return False

            return True
        except:
            # If we can't check disk space, assume it's OK
            return True

    def install_iabuilder(self):
        """Install IABuilder to the installation directory"""
        print(f"{self.colors['blue']}📦 Installing IABuilder...{self.colors['reset']}")

        try:
            # Create installation directory
            self.install_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files except installer itself
            for item in self.script_dir.iterdir():
                if item.name != "installer.py" and not item.name.startswith("install_iabuilder"):
                    if item.is_file():
                        shutil.copy2(item, self.install_dir)
                    else:
                        shutil.copytree(item, self.install_dir / item.name, dirs_exist_ok=True)

            # Create the interactive launcher
            self.create_interactive_launcher()

            print(f"{self.colors['green']}✅ IABuilder installed successfully!{self.colors['reset']}")
            return True

        except Exception as e:
            print(f"{self.colors['red']}❌ Installation failed: {e}{self.colors['reset']}")
            return False

    def create_interactive_launcher(self):
        """Create the interactive launcher that asks for directory"""
        launcher_content = '''#!/bin/bash
# IABuilder Interactive Desktop Launcher

echo "=================================================="
echo "🤖 IABUILDER DESKTOP LAUNCHER"
echo "=================================================="
echo
echo "Enter the directory where you want to start IABuilder:"
echo "(Press Enter to use current directory)"
echo

read -p "Directory: " user_dir

if [ -z "$user_dir" ]; then
    user_dir="$PWD"
fi

if [ ! -d "$user_dir" ]; then
    echo "Directory does not exist: $user_dir"
    echo "Press Enter to exit..."
    read
    exit 1
fi

echo "Starting IABuilder in: $user_dir"
cd "$(dirname "$0")"
export IABUILDER_WORKING_DIR="$user_dir"
python3 launch_iabuilder.py
'''

        launcher_path = self.install_dir / "iabuilder-launcher.sh"
        launcher_path.write_text(launcher_content)
        launcher_path.chmod(0o755)

    def create_desktop_shortcut(self):
        """Create desktop shortcut for the current platform"""
        print(f"{self.colors['blue']}🔗 Creating desktop shortcut...{self.colors['reset']}")

        try:
            if self.system == "linux":
                self.create_linux_shortcut()
            elif self.system == "darwin":
                self.create_macos_shortcut()
            elif self.system == "windows":
                self.create_windows_shortcut()
            else:
                print(f"{self.colors['yellow']}⚠️  Desktop shortcut not supported on this platform{self.colors['reset']}")

            print(f"{self.colors['green']}✅ Desktop shortcut created!{self.colors['reset']}")

        except Exception as e:
            print(f"{self.colors['yellow']}⚠️  Could not create desktop shortcut: {e}{self.colors['reset']}")

    def create_linux_shortcut(self):
        """Create .desktop file for Linux"""
        desktop_dir = Path.home() / "Desktop"
        desktop_dir.mkdir(exist_ok=True)

        desktop_file = desktop_dir / "iabuilder.desktop"
        desktop_content = f"""[Desktop Entry]
Name=IABuilder
Comment=Intelligent Architecture Builder
Exec=gnome-terminal -- bash "{self.install_dir}/iabuilder-launcher.sh"
Icon=terminal
Terminal=false
Type=Application
Categories=Development;
"""

        desktop_file.write_text(desktop_content)
        desktop_file.chmod(0o755)

    def create_macos_shortcut(self):
        """Create .app bundle for macOS"""
        desktop_dir = Path.home() / "Desktop"
        app_dir = desktop_dir / "IABuilder.app" / "Contents" / "MacOS"
        app_dir.mkdir(parents=True, exist_ok=True)

        # Copy launcher
        shutil.copy2(self.install_dir / "iabuilder-launcher.sh", app_dir / "iabuilder-launcher")
        (app_dir / "iabuilder-launcher").chmod(0o755)

        # Create Info.plist
        plist_dir = desktop_dir / "IABuilder.app" / "Contents"
        plist_content = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>iabuilder-launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.iabuilder.desktop</string>
    <key>CFBundleName</key>
    <string>IABuilder</string>
</dict>
</plist>
"""
        (plist_dir / "Info.plist").write_text(plist_content)

    def create_windows_shortcut(self):
        """Create .lnk shortcut for Windows"""
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "IABuilder.lnk")

            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = 'powershell.exe'
            shortcut.Arguments = f'-ExecutionPolicy Bypass -File "{self.install_dir}\\iabuilder-launcher.sh"'
            shortcut.WorkingDirectory = str(self.install_dir)
            shortcut.Description = "Launch IABuilder"
            shortcut.save()

        except ImportError:
            # Fallback without winshell
            print(f"{self.colors['yellow']}⚠️  Desktop shortcut creation limited. Install pywin32 for better shortcuts.{self.colors['reset']}")

    def test_installation(self):
        """Test that the installation works"""
        print(f"{self.colors['blue']}🧪 Testing installation...{self.colors['reset']}")

        try:
            # Try to run a basic Python check
            result = subprocess.run([
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, '{self.install_dir}'); import launch_iabuilder; print('OK')"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print(f"{self.colors['green']}✅ Installation test passed!{self.colors['reset']}")
                return True
            else:
                print(f"{self.colors['yellow']}⚠️  Installation test warning: {result.stderr.strip()}{self.colors['reset']}")
                return True

        except Exception as e:
            print(f"{self.colors['yellow']}⚠️  Installation test failed: {e}{self.colors['reset']}")
            return False

    def run(self):
        """Main installation flow"""
        self.print_banner()

        print(f"{self.colors['green']}Detected platform: {self.system.upper()}{self.colors['reset']}")
        print()

        # Run installation steps
        if not self.check_python():
            print(f"{self.colors['red']}❌ Python 3.8+ is required. Please install it first.{self.colors['reset']}")
            sys.exit(1)

        if not self.check_disk_space():
            sys.exit(1)

        if not self.install_iabuilder():
            sys.exit(1)

        self.create_desktop_shortcut()

        if self.test_installation():
            print()
            print(f"{self.colors['green']}{self.colors['bold']}🎉 IABuilder installed successfully!{self.colors['reset']}")
            print()
            print(f"{self.colors['yellow']}🚀 To start IABuilder:{self.colors['reset']}")
            print(f"   • Double-click the desktop shortcut")
            print(f"   • Or run: {self.colors['cyan']}python3 {self.install_dir}/launch_iabuilder.py{self.colors['reset']}")
            print()
            print(f"{self.colors['blue']}📁 Installation directory: {self.install_dir}{self.colors['reset']}")

def main():
    installer = IABuilderInstaller()
    installer.run()

if __name__ == "__main__":
    main()