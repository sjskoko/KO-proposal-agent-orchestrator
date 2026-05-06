#!/usr/bin/env bash
# run_agent.sh — run the agent from the command line
set -euo pipefail

GOAL="${1:-}"
AGENT_ID="${2:-main_agent}"

if [ -z "$GOAL" ]; then
  echo "Usage: $0 \"<goal>\" [agent_id]"
  exit 1
fi

source .venv/bin/activate 2>/dev/null || true

python -m apps.cli.main run "$GOAL" --agent "$AGENT_ID"
