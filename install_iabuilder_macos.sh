#!/usr/bin/env bash
# install_iabuilder_macos.sh - Installation script for IABuilder on macOS
# This script installs iabuilder to make it available system-wide
# and sets up the virtual environment
#
# USAGE:
#   ./install_iabuilder_macos.sh             # Install only
#   ./install_iabuilder_macos.sh --run       # Install and run immediately
#   ./install_iabuilder_macos.sh --dir=/path # Install to specific directory

# Exit on error
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Show banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ${GREEN}IABUILDER MACOS INSTALLER${BLUE}              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}This script will install IABuilder on macOS${NC}\n"

# Parse command line arguments
INSTALL_DIR="$HOME/bin"
FORCE_INSTALL=false
RUN_AFTER_INSTALL=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --dir=*)
      INSTALL_DIR="${1#*=}"
      shift
      ;;
    --force)
      FORCE_INSTALL=true
      shift
      ;;
    --run)
      RUN_AFTER_INSTALL=true
      shift
      ;;
    --help)
      echo -e "${CYAN}${BOLD}Usage:${NC}"
      echo -e "  $0 [options]"
      echo -e "\n${CYAN}${BOLD}Options:${NC}"
      echo -e "  --dir=PATH     Install to specified directory (default: ~/bin)"
      echo -e "  --force        Force installation even if already installed"
      echo -e "  --run          Run iabuilder after installation"
      echo -e "  --help         Show this help message"
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}Error: This script is for macOS only.${NC}"
    echo -e "${YELLOW}For Linux, use: ./install_iabuilder.sh${NC}"
    echo -e "${YELLOW}For Windows, use: ./install_iabuilder_windows.ps1${NC}"
    exit 1
fi

# Create installation directory if it doesn't exist
echo -e "${YELLOW}Installation directory:${NC} ${CYAN}$INSTALL_DIR${NC}"
mkdir -p "$INSTALL_DIR"
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Could not create installation directory ${CYAN}$INSTALL_DIR${NC}"
    exit 1
fi

# Check if iabuilder is already installed
if [ -f "$INSTALL_DIR/iabuilder" ] && [ "$FORCE_INSTALL" = false ]; then
    echo -e "${YELLOW}iabuilder is already installed at ${CYAN}$INSTALL_DIR/iabuilder${NC}"
    echo -e "Use ${CYAN}--force${NC} to reinstall or update."

    # Ask for confirmation
    read -p "Do you want to continue with installation? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation canceled.${NC}"
        exit 1
    fi
fi

# Copy the iabuilder script to installation directory
echo -e "Copying iabuilder to ${CYAN}$INSTALL_DIR${NC}..."

# Create the iabuilder script with the correct path to the project
cat > "$INSTALL_DIR/iabuilder" << EOL
#!/bin/bash
# iabuilder - IABuilder CLI that works from any project directory

# Colors for terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory of the script (resolves symlinks)
SCRIPT_PATH="\$(readlink -f "\$0")"
SCRIPT_DIR="\$(dirname "\$SCRIPT_PATH")"
IABUILDER_DIR="\$SCRIPT_DIR"
VENV_PATH="\$IABUILDER_DIR/venv"

# Verify iabuilder directory and virtual environment exist
if [ ! -d "\$IABUILDER_DIR" ]; then
    echo -e "\${RED}Error: IABuilder directory not found at \$IABUILDER_DIR\${NC}"
    echo -e "\${YELLOW}Please verify the installation or reinstall the software\${NC}"
    exit 1
fi

if [ ! -d "\$VENV_PATH" ]; then
    echo -e "\${YELLOW}⚠️ Virtual environment not found. Creating new one...\${NC}"
    cd "\$IABUILDER_DIR"
    python3 -m venv venv
    . "\$VENV_PATH/bin/activate"
    pip install -r requirements.txt
    echo -e "\${GREEN}✅ Virtual environment created and configured\${NC}"
else
    # Virtual environment exists, activate silently
    . "\$VENV_PATH/bin/activate" 2>/dev/null
fi

# Startup banner
echo -e "\${BLUE}╔════════════════════════════════════════════════════════╗\${NC}"
echo -e "\${BLUE}║                    \${GREEN}IABUILDER CLI\${BLUE}                     ║\${NC}"
echo -e "\${BLUE}║   \${YELLOW}Intelligent Architecture Builder with AI Support\${BLUE}   ║\${NC}"
echo -e "\${BLUE}╚════════════════════════════════════════════════════════╝\${NC}"
echo -e "\${GREEN}📂 Working directory:\${NC} \$(pwd)"
echo -e "\${YELLOW}🧰 Available tools:\${NC} file read/write, bash commands, code search"
echo -e "\${YELLOW}🚀 Background processes:\${NC} can run servers and monitor logs"
echo -e "\${YELLOW}🛠️ Enabled functions:\${NC} AI knows it has access to these tools\n"

# Set environment variables
# API key should be configured by user via /configure-api command or environment variable
# export GROQ_API_KEY="your-api-key-here"
export IABUILDER_WORKING_DIR="\$(pwd)"
export PYTHONPATH="\$IABUILDER_DIR:\$PYTHONPATH"
export GROQ_TOOLS_ENABLED="true"

# Change to project directory and execute
cd "\$IABUILDER_DIR" && exec python3 launch_iabuilder.py "\$@"
EOL

# Make the script executable
chmod +x "$INSTALL_DIR/iabuilder"

# Check if the installation directory is already in the PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "Adding ${CYAN}$INSTALL_DIR${NC} to your PATH..."

    # Detect shell and update appropriate config file
    SHELL_NAME=$(basename "$SHELL")

    if [ "$SHELL_NAME" = "bash" ]; then
        CONFIG_FILE=~/.bashrc
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> $CONFIG_FILE
    elif [ "$SHELL_NAME" = "zsh" ]; then
        CONFIG_FILE=~/.zshrc
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> $CONFIG_FILE
    else
        # Default to bashrc if shell not recognized
        CONFIG_FILE=~/.bashrc
        echo "export PATH=\"$INSTALL_DIR:\$PATH\"" >> $CONFIG_FILE
    fi

    echo -e "${YELLOW}PATH updated in ${CYAN}$CONFIG_FILE${NC}"
    echo -e "${YELLOW}You may need to restart your terminal or run:${NC} ${CYAN}source $CONFIG_FILE${NC}"
else
    echo -e "${GREEN}$INSTALL_DIR is already in your PATH${NC}"
fi

echo -e "\n${GREEN}${BOLD}Installation complete!${NC}"
echo -e "You can now use ${CYAN}${BOLD}iabuilder${NC} from any directory."

# Create log directory
mkdir -p ~/.iabuilder/logs
mkdir -p ~/.iabuilder/process_logs

# Setup virtual environment if needed
echo -e "${CYAN}Checking virtual environment...${NC}"
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    cd "$SCRIPT_DIR"
    python3 -m venv venv

    echo -e "${GREEN}Installing dependencies...${NC}"
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"

    # Install the package in development mode
    pip install -e "$SCRIPT_DIR"

    echo -e "${GREEN}Virtual environment configured correctly${NC}"
else
    echo -e "${GREEN}Virtual environment already exists${NC}"

    # Update dependencies
    source "$SCRIPT_DIR/venv/bin/activate"
    pip install --upgrade pip
    pip install -r "$SCRIPT_DIR/requirements.txt"
    pip install -e "$SCRIPT_DIR"
fi

# Make run script executable
chmod +x "$SCRIPT_DIR/run_iabuilder.py"

# Create an alias if not on Windows
if [ "$(uname)" != "Windows_NT" ]; then
    if [ ! -f "$HOME/.bash_aliases" ]; then
        touch "$HOME/.bash_aliases"
    fi

    if ! grep -q "alias iabuilder-direct" "$HOME/.bash_aliases"; then
        echo "alias iabuilder-direct='python3 $SCRIPT_DIR/run_iabuilder.py'" >> "$HOME/.bash_aliases"
        echo -e "${GREEN}Added alias ${CYAN}iabuilder-direct${GREEN} to .bash_aliases${NC}"
        echo -e "${YELLOW}Run ${CYAN}source ~/.bash_aliases${YELLOW} to use it immediately${NC}"
    fi
fi

# Success message with usage instructions
echo -e "\n${CYAN}${BOLD}=== How to Use IABuilder CLI ===${NC}"
echo -e "${YELLOW}Basic usage:${NC}"
echo -e "  1. Navigate to any project directory: ${CYAN}cd ~/your-project${NC}"
echo -e "  2. Run iabuilder: ${CYAN}iabuilder${NC}"
echo -e "  3. The AI will have access to your project files and directory structure"

echo -e "\n${YELLOW}Alternative launch methods:${NC}"
echo -e "  • Direct execution (no PATH needed): ${CYAN}python3 $SCRIPT_DIR/run_iabuilder.py${NC}"
echo -e "  • Using alias (after reloading shell): ${CYAN}iabuilder-direct${NC}"

echo -e "\n${YELLOW}Useful commands:${NC}"
echo -e "  ${CYAN}/help${NC} - Show all available commands"
echo -e "  ${CYAN}/model${NC} - List or switch AI models"
echo -e "  ${CYAN}/tools${NC} - List available tools"

echo -e "\n${YELLOW}Example prompts:${NC}"
echo -e "  ${CYAN}\"List all Python files in this directory\"${NC}"
echo -e "  ${CYAN}\"Read file.py and explain what it does\"${NC}"
echo -e "  ${CYAN}\"Create a simple HTML template\"${NC}"
echo -e "  ${CYAN}\"Find all TODO comments in JavaScript files\"${NC}"
echo -e "  ${CYAN}\"Start a web server in the background and monitor logs\"${NC}"

echo -e "\n${BLUE}Logs are stored in:${NC} ${CYAN}~/.iabuilder/logs${NC}"
echo -e "${BLUE}Config file:${NC} ${CYAN}~/.iabuilder/config.json${NC}"

# Run immediately if requested
if [ "$RUN_AFTER_INSTALL" = true ]; then
    echo -e "\n${GREEN}${BOLD}Launching IABuilder CLI...${NC}\n"
    sleep 1
    "$INSTALL_DIR/iabuilder"
fi