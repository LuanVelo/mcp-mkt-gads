#!/bin/bash
# setup.sh — Instalação inicial e configuração do Google Ads MCP Server
# Cria virtualenv, instala dependências e abre o setup UI.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="${PYTHON:-python3}"

echo "=== Google Ads MCP — Setup Inicial ==="
echo ""

# Verifica Python 3.11+
if ! command -v "$PYTHON" &>/dev/null; then
    echo "❌ Python não encontrado. Instale Python 3.11+ e tente novamente."
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 11 ]; }; then
    echo "❌ Python $PY_VERSION encontrado, mas é necessário Python 3.11+."
    exit 1
fi

echo "✅ Python $PY_VERSION encontrado."

# Cria virtualenv se não existir
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Criando virtualenv em .venv..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Ativa o virtualenv
source "$VENV_DIR/bin/activate"

# Instala dependências
echo "📦 Instalando dependências..."
pip install -r "$SCRIPT_DIR/requirements.txt" --quiet
echo "✅ Dependências instaladas."

# Cria diretório de logs se não existir
mkdir -p "$SCRIPT_DIR/logs"

echo ""
echo "🚀 Abrindo interface de configuração..."
echo "   Acesse http://localhost:5001 no seu browser para configurar as credenciais."
echo ""

python "$SCRIPT_DIR/setup_ui/app.py"
