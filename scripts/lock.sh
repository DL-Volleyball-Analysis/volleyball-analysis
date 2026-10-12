#!/usr/bin/env bash
# Regenerate requirements/lock.txt: resolve vball[dev] and the web app backend in a fresh virtual environment on the
# Python version in .python-version, then pin everything it installed.
set -euo pipefail
cd "$(dirname "$0")/.."
py="python$(cat .python-version)"
env_dir="$(mktemp -d)/lockenv"
"$py" -m venv "$env_dir"
"$env_dir/bin/python" -m pip install -q --upgrade pip
"$env_dir/bin/python" -m pip install -q -e ".[dev]" -e webapp/backend
{
  echo "# Pinned versions for CI and development (Python $(cat .python-version)): vball with the dev extra plus the web app backend."
  echo "# Regenerate after changing dependencies in pyproject.toml or webapp/backend/pyproject.toml: scripts/lock.sh"
  "$env_dir/bin/python" -m pip freeze --exclude-editable
} > requirements/lock.txt
rm -rf "$(dirname "$env_dir")"
echo "requirements/lock.txt: $(grep -vc '^#' requirements/lock.txt) packages"
