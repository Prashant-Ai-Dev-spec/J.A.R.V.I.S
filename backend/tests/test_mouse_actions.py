import unittest
from backend.desktop_automation.core import DesktopAutomation


class MouseActionsTests(unittest.TestCase):
    def test_click_methods_no_exceptions(self):
        da = DesktopAutomation()
        da.click(10, 10)
        da.double_click(10, 10)
        da.right_click(20, 20)


if __name__ == '__main__':
    unittest.main()
