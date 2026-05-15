import os
import tempfile
import unittest
from backend.desktop_automation.utils import save_screenshot


class ScreenshotSaveTests(unittest.TestCase):
    def test_save_screenshot_writes_file(self):
        fd, path = tempfile.mkstemp(suffix='.png')
        os.close(fd)
        try:
            ok = save_screenshot(path)
            self.assertTrue(ok, 'save_screenshot should return True')
            self.assertTrue(os.path.exists(path))
            self.assertTrue(os.path.getsize(path) > 0)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
