#!/usr/bin/env bash
python3 -m pip install playwright -q
python3 -m playwright install chromium -q
echo "Playwright installed"