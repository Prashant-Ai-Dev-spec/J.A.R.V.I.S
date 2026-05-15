#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 -m pip install pyinstaller

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name JARVIS \
  --add-data "assets:assets" \
  --add-data "contacts.csv:." \
  jarvis_gui.py

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --name JARVIS-Web \
  --add-data "web:web" \
  --add-data "assets:assets" \
  --add-data "contacts.csv:." \
  jarvis_web.py

echo "Done. Check the dist folder."
