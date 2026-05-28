"""
Browsing adapter: supports 'requests' and 'playwright' providers.
Playwright provider requires playwright package and browsers installed.
"""
import requests
from typing import Any

class BrowsingAdapter:
    def __init__(self, provider='requests', api_key=None):
        self.provider = provider
        self.api_key = api_key
        self._playwright_adapter = None
        if provider == 'playwright':
            try:
                from backend.playwright_adapter import PlaywrightAdapter
                self._playwright_adapter = PlaywrightAdapter()
            except Exception:
                self._playwright_adapter = None

    def fetch(self, url, timeout=10) -> Any:
        if self.provider == 'requests':
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return {'html': r.text}
        if self.provider == 'playwright':
            if not self._playwright_adapter:
                raise RuntimeError('Playwright adapter not available. Run install_playwright script.')
            return self._playwright_adapter.fetch(url, timeout=timeout)
        raise NotImplementedError('Provider not implemented')

    def summary(self, html_obj, max_len=2000):
        if isinstance(html_obj, dict) and 'html' in html_obj:
            return str(html_obj['html'])[:max_len]
        return str(html_obj)[:max_len]
