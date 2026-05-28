from pathlib import Path
from playwright.sync_api import sync_playwright
import time

PHOTOS_DIR = Path(__file__).resolve().parent.parent / "jarvis_photos"
PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

class PlaywrightAdapter:
    def __init__(self, headless=True):
        self.headless = headless

    def fetch(self, url, timeout=15):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=timeout * 1000)
            content = page.content()
            # Save screenshot for vision models
            fname = f"playwright_{int(time.time())}.jpg"
            out = PHOTOS_DIR / fname
            page.screenshot(path=str(out), type='jpeg', quality=60)
            browser.close()
            return {"html": content, "screenshot_path": str(out)}

    def summary(self, content, max_len=2000):
        return content[:max_len]
