#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/mobile/android"

python3 -m venv .buildozer-venv
source .buildozer-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install buildozer cython
buildozer -v android debug

echo "APK created under mobile/android/bin/."
