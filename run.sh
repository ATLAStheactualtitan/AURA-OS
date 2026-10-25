#!/usr/bin/env bash
# ./run.sh            fullscreen shell
# ./run.sh --windowed [--no-fullscreen]  development window
# ./run.sh --test     run the test suite
set -euo pipefail
cd "$(dirname "$0")"
[[ -x .venv/bin/python ]] || { echo "Run ./setup.sh first"; exit 1; }
# macOS dev hosts can flag venv files as hidden, which makes Qt skip its plugins.
[[ "$(uname -s)" == "Darwin" ]] && chflags -R nohidden .venv 2>/dev/null || true
if [[ "${1:-}" == "--test" ]]; then
  QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}" exec .venv/bin/python -m pytest -q tests
fi
exec .venv/bin/python -m aura "$@"
