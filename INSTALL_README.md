# 🚀 IABuilder Installation Guide

## 📦 Download & Install

### Choose your platform:

| Platform | File | Size | How to run |
|----------|------|------|------------|
| **🐧 Linux** | `install.sh` | ~149MB | `chmod +x install.sh && ./install.sh` |
| **🍎 macOS** | `install.command` | ~149MB | Double-click `install.command` |
| **🪟 Windows** | `install.ps1` | ~149MB | Right-click → `Run with PowerShell` |

## ⚡ Quick Install

1. **Download** the appropriate installer for your platform
2. **Make executable** (Linux/macOS): `chmod +x install.sh`
3. **Run the installer**:
   - Linux: `./install.sh`
   - macOS: Double-click `install.command`
   - Windows: Right-click `install.ps1` → Run with PowerShell

## 🛠️ What the installer does:

### ✅ Automatic Setup:
- ✅ Detects your operating system automatically
- ✅ Checks Python 3.8+ availability
- ✅ Copies IABuilder with all dependencies (149MB)
- ✅ Creates desktop shortcut
- ✅ Tests the installation

### 🎯 Desktop Shortcut:
After installation, you'll have a **desktop shortcut** that:
1. **Automatically detects and opens your best available terminal** (alacritty, gnome-terminal, konsole, lxterminal, etc.)
2. Asks: `"Enter the directory where you want to start IABuilder:"`
3. You type/paste your project path (easy copy/paste in modern terminals!)
4. IABuilder starts in that directory

## 🖥️ Terminal Selection

The installer automatically detects and uses the best available terminal:

**Preferred (Modern terminals with great copy/paste):**
- 🥇 **Alacritty** - Fast, modern, excellent copy/paste
- 🥈 **Terminator** - Feature-rich with tabs and splits
- 🥉 **Tilix** - Modern tiling terminal
- 🏆 **GNOME Terminal** - Default GNOME terminal
- 🏆 **Konsole** - Default KDE terminal
- 🏆 **LX Terminal** - Lightweight and fast

**Other supported terminals:**
- XFCE Terminal, MATE Terminal, Sakura, etc.
- **xterm** (fallback only if no other terminal is found)

## 📋 System Requirements:

### Minimum Requirements:
- **Python 3.8 or higher**
- **200MB free disk space**
- **Desktop environment** (for shortcuts)

### Supported Platforms:
- ✅ **Linux**: Ubuntu, Debian, Fedora, CentOS, Arch, etc.
- ✅ **macOS**: 10.15+ (Catalina or newer)
- ✅ **Windows**: 10/11 with PowerShell

## 🔧 Manual Installation (if needed):

If the installer fails, you can install manually:

```bash
# 1. Extract the downloaded archive
tar -xzf iabuilder-installer-linux.tar.gz
cd iabuilder/

# 2. Run manual installation
python3 installer.py
```

## 🚨 Troubleshooting:

### "Python not found":
```bash
# Linux
sudo apt-get install python3 python3-pip

# macOS
# Download from: https://python.org/downloads/

# Windows
# Download from: https://python.org/downloads/
```

### "Permission denied":
```bash
# Linux/macOS
chmod +x install.sh
./install.sh

# Or run as admin
sudo ./install.sh
```

### "No desktop shortcut created":
- The installer will still work
- You can run: `python3 /path/to/iabuilder/launch_iabuilder.py`

## 🎉 After Installation:

**Double-click the desktop shortcut** or run:
```bash
python3 ~/.local/share/iabuilder/launch_iabuilder.py
```

The interactive launcher will ask for your project directory!

## 📞 Support:

If you encounter issues:
1. Check this README
2. Try manual installation
3. Ensure Python 3.8+ is installed
4. Check disk space (need 200MB+)

---

**Made with ❤️ for developers who want universal AI assistance**