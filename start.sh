#!/bin/bash
# start.sh — Inicia o Google Ads MCP Server
# Se config.json não existir, abre o setup UI primeiro.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"
VENV_DIR="$SCRIPT_DIR/.venv"

# Ativa o virtualenv se existir
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
fi

if [ ! -f "$CONFIG_FILE" ]; then
    echo "⚠️  config.json não encontrado. Iniciando setup guiado..."
    echo "   Acesse http://localhost:5001 para configurar as credenciais."
    echo ""
    python "$SCRIPT_DIR/setup_ui/app.py"
else
    echo "✅ config.json encontrado. Iniciando Google Ads MCP Server..."
    python "$SCRIPT_DIR/server.py"
fi
