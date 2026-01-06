#Requires -Version 5.1
<#
.SYNOPSIS
    Installation script for IABuilder on Windows

.DESCRIPTION
    This script installs IABuilder to make it available system-wide
    and sets up the virtual environment

.PARAMETER InstallDir
    Directory where to install iabuilder (default: $HOME\bin)

.PARAMETER Force
    Force installation even if already installed

.PARAMETER Run
    Run iabuilder after installation

.EXAMPLE
    .\install_iabuilder_windows.ps1

.EXAMPLE
    .\install_iabuilder_windows.ps1 -InstallDir "C:\Tools" -Run

.EXAMPLE
    .\install_iabuilder_windows.ps1 -Force
#>

param(
    [string]$InstallDir = "$env:USERPROFILE\bin",
    [switch]$Force,
    [switch]$Run
)

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"
$Red = "Red"
$Cyan = "Cyan"
$White = "White"

function Write-ColorOutput {
    param(
        [string]$Text,
        [string]$Color = "White"
    )
    Write-Host $Text -ForegroundColor $Color
}

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition

# Show banner
Write-ColorOutput "╔════════════════════════════════════════════════════════╗" $Blue
Write-ColorOutput "║             IABUILDER WINDOWS INSTALLER              ║" $Blue
Write-ColorOutput "╚════════════════════════════════════════════════════════╝" $Blue
Write-ColorOutput "This script will install IABuilder on Windows`n" $Yellow

# Check if running on Windows
if ($env:OS -notlike "*Windows*") {
    Write-ColorOutput "Error: This script is for Windows only." $Red
    Write-ColorOutput "For Linux, use: ./install_iabuilder.sh" $Yellow
    Write-ColorOutput "For macOS, use: ./install_iabuilder_macos.sh" $Yellow
    exit 1
}

# Create installation directory if it doesn't exist
Write-ColorOutput "Installation directory: $InstallDir" $Yellow
if (!(Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

if (!(Test-Path $InstallDir)) {
    Write-ColorOutput "Error: Could not create installation directory $InstallDir" $Red
    exit 1
}

# Check if iabuilder is already installed
$IabuilderPath = Join-Path $InstallDir "iabuilder.cmd"
if ((Test-Path $IabuilderPath) -and !$Force) {
    Write-ColorOutput "iabuilder is already installed at $IabuilderPath" $Yellow
    Write-ColorOutput "Use -Force to reinstall or update." $Yellow

    $response = Read-Host "Do you want to continue with installation? (y/n)"
    if ($response -notlike "y*") {
        Write-ColorOutput "Installation canceled." $Red
        exit 1
    }
}

# Create the iabuilder.cmd script
Write-ColorOutput "Creating iabuilder.cmd script..." $Cyan

$IabuilderContent = @"
@echo off
REM iabuilder - IABuilder CLI that works from any project directory

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "IABUILDER_DIR=%SCRIPT_DIR%"
set "VENV_PATH=%IABUILDER_DIR%venv\Scripts"

REM Verify iabuilder directory exists
if not exist "%IABUILDER_DIR%" (
    echo Error: IABuilder directory not found at %IABUILDER_DIR%
    echo Please verify the installation or reinstall the software
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%VENV_PATH%" (
    echo Virtual environment not found. Creating new one...
    cd /d "%IABUILDER_DIR%"
    python -m venv venv
    call "%VENV_PATH%\activate.bat"
    pip install -r requirements.txt
    echo Virtual environment created and configured successfully
) else (
    REM Virtual environment exists, activate silently
    call "%VENV_PATH%\activate.bat" 2>nul
)

REM Startup banner
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║                    IABUILDER CLI                      ║
echo ║   Intelligent Architecture Builder with AI Support   ║
echo ╚════════════════════════════════════════════════════════╝
echo.
echo 📂 Working directory: %CD%
echo 🧰 Available tools: file read/write, bash commands, code search
echo 🚀 Background processes: can run servers and monitor logs
echo 🛠️  Enabled functions: AI knows it has access to these tools
echo.

REM Set environment variables
REM API key should be configured by user via /configure-api command or environment variable
REM set GROQ_API_KEY=your-api-key-here
set IABUILDER_WORKING_DIR=%CD%
set PYTHONPATH=%IABUILDER_DIR%;%PYTHONPATH%
set GROQ_TOOLS_ENABLED=true

REM Change to project directory and execute
cd /d "%IABUILDER_DIR%"
python launch_iabuilder.py %*
"@

$IabuilderContent | Out-File -FilePath $IabuilderPath -Encoding UTF8 -Force

Write-ColorOutput "Script created successfully" $Green

# Check if the installation directory is already in the PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$InstallDir*") {
    Write-ColorOutput "Adding $InstallDir to your PATH..." $Cyan

    # Add to user PATH
    $newPath = "$currentPath;$InstallDir"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")

    Write-ColorOutput "PATH updated. You may need to restart your terminal." $Yellow
} else {
    Write-ColorOutput "$InstallDir is already in your PATH" $Green
}

Write-ColorOutput "`nInstallation complete!" $Green
Write-ColorOutput "You can now use 'iabuilder' from any directory." $Cyan

# Create directories
$IabuilderUserDir = "$env:USERPROFILE\.iabuilder"
New-Item -ItemType Directory -Path "$IabuilderUserDir\logs" -Force | Out-Null
New-Item -ItemType Directory -Path "$IabuilderUserDir\process_logs" -Force | Out-Null

# Setup virtual environment if needed
Write-ColorOutput "Checking virtual environment..." $Cyan

$VenvPath = Join-Path $ScriptDir "venv"
if (!(Test-Path $VenvPath)) {
    Write-ColorOutput "Creating Python virtual environment..." $Yellow
    Push-Location $ScriptDir
    python -m venv venv

    Write-ColorOutput "Installing dependencies..." $Green
    & "$VenvPath\Scripts\activate.ps1"
    pip install --upgrade pip
    pip install -r requirements.txt

    # Install the package in development mode
    pip install -e $ScriptDir

    Write-ColorOutput "Virtual environment configured correctly" $Green
    Pop-Location
} else {
    Write-ColorOutput "Virtual environment already exists" $Green

    # Update dependencies
    Push-Location $ScriptDir
    & "$VenvPath\Scripts\activate.ps1"
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -e $ScriptDir
    Pop-Location
}

# Success message with usage instructions
Write-ColorOutput "`n=== How to Use IABuilder CLI ===" $Cyan
Write-ColorOutput "Basic usage:" $Yellow
Write-ColorOutput "  1. Navigate to any project directory: cd C:\your-project" $Cyan
Write-ColorOutput "  2. Run iabuilder: iabuilder" $Cyan
Write-ColorOutput "  3. The AI will have access to your project files and directory structure" $Cyan

Write-ColorOutput "`nAlternative launch methods:" $Yellow
Write-ColorOutput "  • Direct execution (no PATH needed): python $ScriptDir\run_iabuilder.py" $Cyan
Write-ColorOutput "  • Using full path: $IabuilderPath" $Cyan

Write-ColorOutput "`nUseful commands:" $Yellow
Write-ColorOutput "  /help - Show all available commands" $Cyan
Write-ColorOutput "  /model - List or switch AI models" $Cyan
Write-ColorOutput "  /tools - List available tools" $Cyan

Write-ColorOutput "`nExample prompts:" $Yellow
Write-ColorOutput "  `"List all Python files in this directory`"" $Cyan
Write-ColorOutput "  `"Read file.py and explain what it does`"" $Cyan
Write-ColorOutput "  `"Create a simple HTML template`"" $Cyan
Write-ColorOutput "  `"Find all TODO comments in JavaScript files`"" $Cyan
Write-ColorOutput "  `"Start a web server in the background and monitor logs`"" $Cyan

Write-ColorOutput "`nLogs are stored in: $IabuilderUserDir\logs" $Blue
Write-ColorOutput "Config file: $IabuilderUserDir\config.json" $Blue

# Run immediately if requested
if ($Run) {
    Write-ColorOutput "`nLaunching IABuilder CLI..." $Green
    Start-Sleep -Seconds 1
    & $IabuilderPath
}