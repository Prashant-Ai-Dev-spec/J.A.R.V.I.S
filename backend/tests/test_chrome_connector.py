import unittest
from backend.connectors import chrome_connector


class ChromeConnectorTests(unittest.TestCase):
    def test_api_presence(self):
        self.assertTrue(hasattr(chrome_connector, 'open_url'))
        self.assertTrue(hasattr(chrome_connector, 'scroll'))

    def test_scroll_call(self):
        # Call scroll and ensure it returns a bool (True if performed, False if fallback missing)
        res = chrome_connector.scroll(100)
        self.assertIn(res, (True, False))


if __name__ == '__main__':
    unittest.main()
