#!/usr/bin/env python3
"""Start a separate Shreya-branded JARVIS web server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

os.environ.setdefault("JARVIS_CONFIG_PATH", str(BASE_DIR / "jarvis_config.shreya.json"))
os.environ.setdefault("JARVIS_MOBILE_RUNTIME_DIR", str(BASE_DIR / ".jarvis_runtime_shreya" / "mobile_companion"))
os.environ.setdefault("JARVIS_PUBLIC_VIDEOS_DIR", str(Path.home() / "Videos" / "Shreya JARVIS"))

if len(sys.argv) == 1:
    sys.argv.extend(["--host", "127.0.0.1", "--port", "8766"])

from jarvis_web import main


if __name__ == "__main__":
    main()
