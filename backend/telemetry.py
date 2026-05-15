"""Simple telemetry logger with opt-out.
Logs events to a local file unless JARVIS_TELEMETRY=0 is set in environment.
"""
import os
import json
from datetime import datetime

TELEMETRY_ENABLED = os.environ.get('JARVIS_TELEMETRY', '1') != '0'
LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'telemetry.log')


def log_event(event: str, payload: dict | None = None) -> None:
    if not TELEMETRY_ENABLED:
        return
    entry = {'ts': datetime.utcnow().isoformat() + 'Z', 'event': event, 'payload': payload or {}}
    try:
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
