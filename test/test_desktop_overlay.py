import os
import subprocess
import time
import unittest

from gdo.video.DesktopOverlay import DesktopOverlay


@unittest.skipUnless(os.environ.get('PYGDO_VIDEO_GUI_TEST') == '1', 'requires an X11 desktop')
class DesktopOverlayTest(unittest.TestCase):
    def window_state(self):
        result = subprocess.run(['xwininfo', '-name', 'Mira Desktop Overlay'],
                                capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else ''

    def wait_for(self, expected):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if expected in self.window_state():
                return True
            time.sleep(0.05)
        return False

    def test_image_overlay_shows_hides_and_stops(self):
        overlay = DesktopOverlay()
        image = os.path.join(os.path.dirname(__file__), '..', 'img', 'itmb-logo.png')
        overlay.start(os.path.abspath(image))
        try:
            self.assertTrue(self.wait_for('IsViewable'), overlay.status())
            overlay.set_layer('overlay', False)
            self.assertTrue(self.wait_for('IsUnMapped'))
            overlay.set_layer('overlay', True)
            self.assertTrue(self.wait_for('IsViewable'))
        finally:
            self.assertTrue(overlay.stop())
        self.assertFalse(overlay.is_running())


if __name__ == '__main__':
    unittest.main()
