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

echo "==> Checking Gemma checkpoint path"
GEMMA_PATH_DEFAULT="/mnt/raid1/CHK/playground/Gemma4/ckpts/gemma-4-26B-A4B-it"
if [ -d "$GEMMA_PATH_DEFAULT" ]; then
  echo "    Found checkpoint directory: $GEMMA_PATH_DEFAULT"
else
  echo "    Warning: checkpoint directory not found: $GEMMA_PATH_DEFAULT"
  echo "    Set GEMMA_MODEL_PATH in .env (or rely on provider auto-scan roots)."
fi

echo ""
echo "Setup complete. Activate with: source .venv/bin/activate"
echo "Run agent:   agent run 'your task here'"
echo "Run tests:   bash scripts/run_tests.sh"
