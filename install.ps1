# IABuilder Universal Installer Launcher for Windows

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Change to script directory
Set-Location $ScriptDir

# Run the Python installer
python installer.py