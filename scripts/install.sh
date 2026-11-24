#!/usr/bin/env bash
# Claumeet installer for macOS / Linux (EXPERIMENTAL: the supported platform is Windows 10/11).
# Per-user, no sudo. Creates a private virtual environment and installs pinned dependencies.
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-}"
for c in python3.12 python3.13 python3; do
  if [ -z "$PY" ] && command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then PY="$c"; fi
done
[ -n "$PY" ] || { echo "!! Python 3.12+ is required. Install it from https://www.python.org/downloads/ and run this again."; exit 1; }
if ! command -v google-chrome >/dev/null && ! command -v chromium >/dev/null && [ ! -d "/Applications/Google Chrome.app" ]; then
  echo "!! Google Chrome was not found. Install it from https://www.google.com/chrome/ and run this again."; exit 1
fi
VENV="${CLAUMEET_VENV:-$HOME/.local/share/ClaudeMeetAgent/venv}"
"$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -e .
"$VENV/bin/python" -m claude_agent doctor || true
cat <<MSG

Claumeet is installed (experimental on this OS).
Next, in YOUR OWN terminal (the key prompt is hidden, so don't paste the key into a chat):
  $VENV/bin/claumeet setup      # Google account + free Gemini key + test
  $VENV/bin/claumeet run        # opens the Control Center on http://127.0.0.1:8765
MSG
