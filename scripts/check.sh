#!/usr/bin/env bash
# Every check CI runs (.github/workflows/ci.yml), locally, before a commit: lint, format, types, tests with the coverage
# gate, dependency audit, and the frontend's lint, tests and build. Stops at the first failure.
#   scripts/check.sh            everything
#   scripts/check.sh --python   Python only (skips the frontend)
set -euo pipefail
cd "$(dirname "$0")/.."
py="${PYTHON:-.venv/bin/python}"
step() { printf '\n== %s\n' "$1"; }

step "ruff check";   "$py" -m ruff check src scripts tests webapp/backend
step "ruff format";  "$py" -m ruff format --check src scripts tests webapp/backend
step "mypy";         "$py" -m mypy
step "pytest";       "$py" -m pytest -q --cov --cov-report=term:skip-covered --cov-fail-under=90
step "pip-audit";    "$py" -m pip_audit -r requirements/lock.txt
if [[ "${1:-}" != "--python" ]]; then
  cd webapp/frontend
  step "npm audit";  npm audit --audit-level=high
  step "oxlint";     npm run -s lint
  step "vitest";     npm run -s test:coverage
  step "build";      npm run -s build
fi
printf '\nall checks passed\n'
