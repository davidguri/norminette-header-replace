#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${1:-https://github.com/davidguri/norminette-header-replace.git}"

# Prefer pipx if available for a clean global CLI
if command -v pipx >/dev/null 2>&1; then
  pipx install "git+${REPO_URL}"
else
  echo "pipx not found. Installing into a virtualenv under ~/.local/norminette-header-replace"
  PY=${PYTHON:-python3}
  BASE="$HOME/.local/norminette-header-replace"
  rm -rf "$BASE"
  "$PY" -m venv "$BASE"
  # shellcheck disable=SC1090
  source "$BASE/bin/activate"
  pip install --upgrade pip
  pip install "git+${REPO_URL}"
  echo
  echo "Installed. Activate with: source $BASE/bin/activate"
  echo "Then run: norminette-header-replace --help"
fi

echo "Done. Try: norminette-header-replace --help"
