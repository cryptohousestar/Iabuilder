#!/bin/bash
# reinstall.sh - Script to reinstall IABuilder CLI
# This script resets and reinstalls iabuilder with all recent changes

# Colors for terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Banner
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                 ${RED}REINSTALL IABUILDER${BLUE}                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo -e "${YELLOW}Este script reinstalará iabuilder con todos los cambios recientes${NC}\n"

# Check if iabuilder is installed
if [ -f "$HOME/bin/iabuilder" ]; then
    echo -e "${CYAN}Eliminando instalación existente...${NC}"
    rm -f "$HOME/bin/iabuilder"
else
    echo -e "${YELLOW}No se encontró instalación previa en ~/bin/iabuilder${NC}"
fi

# Check virtual environment
if [ -d "$SCRIPT_DIR/venv" ]; then
    echo -e "${YELLOW}¿Desea eliminar el entorno virtual existente? (s/n)${NC}"
    read -r reset_venv
    if [[ "$reset_venv" =~ ^[Ss]$ ]]; then
        echo -e "${CYAN}Eliminando entorno virtual existente...${NC}"
        rm -rf "$SCRIPT_DIR/venv"
    else
        echo -e "${CYAN}Conservando entorno virtual existente${NC}"
    fi
fi

# Check config directory
if [ -d "$HOME/.iabuilder" ]; then
    echo -e "${YELLOW}¿Desea conservar la configuración existente en ~/.iabuilder? (s/n)${NC}"
    read -r keep_config
    if [[ "$keep_config" =~ ^[Ss]$ ]]; then
        echo -e "${CYAN}Conservando configuración existente${NC}"
    else
        echo -e "${CYAN}Respaldando y eliminando configuración existente...${NC}"
        # Backup
        backup_dir="$HOME/.iabuilder-backup-$(date +%Y%m%d_%H%M%S)"
        mv "$HOME/.iabuilder" "$backup_dir"
        echo -e "${GREEN}Configuración anterior respaldada en: ${backup_dir}${NC}"
    fi
fi

# Run the installer
echo -e "${CYAN}Ejecutando instalador...${NC}"
chmod +x "$SCRIPT_DIR/install_iabuilder.sh"
"$SCRIPT_DIR/install_iabuilder.sh" --force

# Confirmation
echo -e "\n${GREEN}${BOLD}¡Reinstalación completa!${NC}"
echo -e "${CYAN}Puede ejecutar ${YELLOW}iabuilder${CYAN} desde cualquier directorio.${NC}"
echo -e "${CYAN}También puede ejecutar ${YELLOW}python3 $SCRIPT_DIR/run_iabuilder.py${CYAN} directamente.${NC}"
echo -e "\n${GREEN}Ejemplo de uso:${NC}"
echo -e "${YELLOW}cd ~/mi-proyecto${NC}"
echo -e "${YELLOW}iabuilder${NC}"

exit 0
