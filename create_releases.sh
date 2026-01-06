#!/bin/bash
# create_releases.sh - Script to create GitHub releases with platform-specific assets

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              ${GREEN}IABUILDER RELEASE CREATOR${BLUE}              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"

# Get version from setup.py
VERSION=$(grep "version=" setup.py | sed 's/.*version="\([^"]*\)".*/\1/')

if [ -z "$VERSION" ]; then
    echo -e "${RED}Error: Could not find version in setup.py${NC}"
    exit 1
fi

echo -e "${YELLOW}Creating release for version:${NC} ${CYAN}${BOLD}$VERSION${NC}"

# Create release archives for each platform
echo -e "${YELLOW}Creating release archives...${NC}"

# Linux release
echo -e "${CYAN}Creating Linux release...${NC}"
tar -czf "iabuilder-${VERSION}-linux.tar.gz" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='.iabuilder' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    .

# Create a simple installer script for Linux
cat > "install_iabuilder_${VERSION}_linux.sh" << 'EOF'
#!/bin/bash
# Simple installer for IABuilder Linux
set -e

echo "Installing IABuilder..."
# Add installation commands here
echo "Installation complete! Run 'iabuilder' to start."
EOF
chmod +x "install_iabuilder_${VERSION}_linux.sh"

# Windows release (zip)
echo -e "${CYAN}Creating Windows release...${NC}"
zip -r "iabuilder-${VERSION}-windows.zip" . \
    -x "venv/*" "__pycache__/*" ".git/*" "*.log" ".iabuilder/*" "dist/*" "build/*" ".pytest_cache/*" "*.egg-info/*"

# Create Windows installer script
cat > "install_iabuilder_${VERSION}_windows.ps1" << 'EOF'
# Simple installer for IABuilder Windows
Write-Host "Installing IABuilder..."
# Add installation commands here
Write-Host "Installation complete! Run 'iabuilder' to start."
EOF

# macOS release
echo -e "${CYAN}Creating macOS release...${NC}"
tar -czf "iabuilder-${VERSION}-macos.tar.gz" \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.log' \
    --exclude='.iabuilder' \
    --exclude='dist' \
    --exclude='build' \
    --exclude='.pytest_cache' \
    --exclude='*.egg-info' \
    .

# Create macOS installer script
cat > "install_iabuilder_${VERSION}_macos.sh" << 'EOF'
#!/bin/bash
# Simple installer for IABuilder macOS
set -e

echo "Installing IABuilder..."
# Add installation commands here
echo "Installation complete! Run 'iabuilder' to start."
EOF
chmod +x "install_iabuilder_${VERSION}_macos.sh"

echo -e "${GREEN}Release archives created:${NC}"
echo -e "  📦 iabuilder-${VERSION}-linux.tar.gz"
echo -e "  📦 iabuilder-${VERSION}-windows.zip"
echo -e "  📦 iabuilder-${VERSION}-macos.tar.gz"
echo -e "  📦 install_iabuilder_${VERSION}_linux.sh"
echo -e "  📦 install_iabuilder_${VERSION}_windows.ps1"
echo -e "  📦 install_iabuilder_${VERSION}_macos.sh"

echo -e "\n${YELLOW}To create a GitHub release, run:${NC}"
echo -e "${CYAN}gh release create v${VERSION} \\${NC}"
echo -e "${CYAN}  --title \"IABuilder v${VERSION}\" \\${NC}"
echo -e "${CYAN}  --notes \"Release notes for version ${VERSION}\" \\${NC}"
echo -e "${CYAN}  iabuilder-${VERSION}-linux.tar.gz \\${NC}"
echo -e "${CYAN}  iabuilder-${VERSION}-windows.zip \\${NC}"
echo -e "${CYAN}  iabuilder-${VERSION}-macos.tar.gz \\${NC}"
echo -e "${CYAN}  install_iabuilder_${VERSION}_linux.sh \\${NC}"
echo -e "${CYAN}  install_iabuilder_${VERSION}_windows.ps1 \\${NC}"
echo -e "${CYAN}  install_iabuilder_${VERSION}_macos.sh${NC}"

echo -e "\n${GREEN}${BOLD}Release preparation complete!${NC}"