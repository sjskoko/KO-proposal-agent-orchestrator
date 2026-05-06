#!/usr/bin/env bash
# setup_local.sh — bootstrap local development environment
set -euo pipefail

echo "==> Checking Python version (>=3.11 required)"
python3 --version

echo "==> Creating virtual environment"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Installing project with dev dependencies"
pip install -e ".[dev]"

echo "==> Copying env file"
if [ ! -f .env ]; then
  cp config/env.example .env
  echo "    Created .env — edit it to add API keys"
fi

echo "==> Creating workspace directories"
mkdir -p workspace data/memory data/traces
touch data/memory/.gitkeep data/traces/.gitkeep workspace/.gitkeep

echo "==> Checking Ollama"
if command -v ollama &>/dev/null; then
  echo "    Ollama found: $(ollama --version)"
  echo "    Pulling Gemma 4 model (this may take a while)..."
  ollama pull gemma4:27b || echo "    Warning: could not pull gemma4:27b — start Ollama and retry"
else
  echo "    Ollama not found. Install from https://ollama.ai and run: ollama pull gemma4:27b"
fi

echo ""
echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Run agent:   agent run 'your task here'"
echo "Run tests:   bash scripts/run_tests.sh"
