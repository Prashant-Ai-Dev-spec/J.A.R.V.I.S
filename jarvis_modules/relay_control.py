"""ESP8266 relay control for J.A.R.V.I.S."""

from __future__ import annotations

from typing import Any

import requests


class RelayControl:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.ip = str(cfg.get("relay_ip", "") or "").strip()
        self.timeout = float(cfg.get("relay_timeout_sec", 3) or 3)

    def _url(self, path: str) -> str:
        if not self.ip:
            raise ValueError("relay_ip is not configured in jarvis_config.json")
        return f"http://{self.ip}/{path.lstrip('/')}"

    def _get_text(self, path: str) -> str:
        response = requests.get(self._url(path), timeout=self.timeout)
        response.raise_for_status()
        return response.text.strip()

    def on(self) -> bool:
        return self._get_text("on") == "RELAY_ON"

    def off(self) -> bool:
        return self._get_text("off") == "RELAY_OFF"

    def status(self) -> str:
        text = self._get_text("status").upper()
        return text if text in {"ON", "OFF"} else text or "UNKNOWN"


def relay_on(cfg: dict[str, Any]) -> bool:
    return RelayControl(cfg).on()


def relay_off(cfg: dict[str, Any]) -> bool:
    return RelayControl(cfg).off()


def relay_status(cfg: dict[str, Any]) -> str:
    return RelayControl(cfg).status()
