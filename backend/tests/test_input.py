import unittest
from backend.desktop_automation.core import DesktopAutomation


class InputSanityTests(unittest.TestCase):
    def test_type_and_hotkey_no_exceptions(self):
        da = DesktopAutomation()
        # Should not raise even if pyautogui missing; functionality is best-effort
        da.press_hotkey('ctrl', 'a')
        da.type_text('Test @#$', use_clipboard_paste=False)


if __name__ == '__main__':
    unittest.main()
