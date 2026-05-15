import unittest
from backend.desktop_automation.core import DesktopAutomation


class ScalingTests(unittest.TestCase):
    def test_scale_coordinates_fallback(self):
        da = DesktopAutomation()
        # Using fallback screen 1920x1080
        sx, sy = da.scale_coordinates(1280, 720, 640, 360)
        self.assertEqual(sx, int(640 * 1920 / 1280))
        self.assertEqual(sy, int(360 * 1080 / 720))


if __name__ == '__main__':
    unittest.main()
