#!/usr/bin/env bash
# run_tests.sh — run all or selected test suites
set -euo pipefail

SUITE="${1:-all}"
source .venv/bin/activate 2>/dev/null || true

case "$SUITE" in
  unit)
    echo "==> Running unit tests"
    pytest tests/unit -v
    ;;
  integration)
    echo "==> Running integration tests"
    pytest tests/integration -v
    ;;
  agent)
    echo "==> Running agent eval tests"
    pytest tests/agent_eval -v
    ;;
  skill)
    echo "==> Running skill eval tests"
    pytest tests/skill_eval -v
    ;;
  all)
    echo "==> Running all tests"
    pytest tests/ -v --tb=short
    ;;
  *)
    echo "Usage: $0 [unit|integration|agent|skill|all]"
    exit 1
    ;;
esac
