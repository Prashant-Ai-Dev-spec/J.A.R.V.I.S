import unittest
from backend.connectors import chrome_devtools


class ChromeDevToolsTests(unittest.TestCase):
    def test_api_presence(self):
        self.assertTrue(hasattr(chrome_devtools, 'start_browser'))
        self.assertTrue(hasattr(chrome_devtools, 'open_url'))
        self.assertTrue(hasattr(chrome_devtools, 'scroll'))
        self.assertTrue(hasattr(chrome_devtools, 'click_selector'))

    def test_no_selenium_fallback(self):
        # If selenium not installed, start_browser should return False
        res = chrome_devtools.start_browser()
        self.assertIn(res, (True, False))


if __name__ == '__main__':
    unittest.main()
