#!/usr/bin/env bash
# Creates .venv and installs dependencies. System packages are only installed with --system (needs sudo).
set -euo pipefail
cd "$(dirname "$0")"

echo "== Inspecting environment =="
echo "OS: $(uname -sm)"
PY="${PYTHON:-python3}"
"$PY" --version

if [[ "${1:-}" == "--system" && -f /etc/os-release && "$(. /etc/os-release; echo "$ID")" =~ ^(ubuntu|debian)$ ]]; then
  echo "== Installing Ubuntu system libraries (sudo) =="
  sudo apt-get update
  sudo apt-get install -y python3-venv python3-pip libgl1 libegl1 libxkbcommon0 libxkbcommon-x11-0 \
    libxcb-cursor0 libpulse0 libpulse-mainloop-glib0 ffmpeg pipewire-pulse wireplumber pulseaudio-utils
elif [[ "$(uname -s)" == "Linux" ]]; then
  echo "Tip: run './setup.sh --system' once to install Qt/PipeWire system libraries on Ubuntu."
fi

[[ -d .venv ]] || "$PY" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c "import PySide6; print('PySide6', PySide6.__version__)"
echo "== Done. Start with ./run.sh =="
