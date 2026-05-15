import unittest
from backend.desktop_automation.core import DesktopAutomation


class DesktopAutomationSanityTests(unittest.TestCase):
    def test_api_surface(self):
        da = DesktopAutomation()
        self.assertTrue(hasattr(da, 'screenshot'))
        self.assertTrue(hasattr(da, 'press_hotkey'))
        self.assertTrue(hasattr(da, 'type_text'))
        self.assertTrue(hasattr(da, 'click'))
        self.assertTrue(hasattr(da, 'scale_coordinates'))


if __name__ == '__main__':
    unittest.main()
