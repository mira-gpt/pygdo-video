import os
import re
import subprocess
import time
import unittest

from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.ImageLayer import ImageLayer
from PIL import Image


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
            overlay.vintage(True)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                vintage_window = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                                capture_output=True, text=True)
                if vintage_window.returncode == 0 and 'IsViewable' in vintage_window.stdout:
                    break
                time.sleep(.05)
            self.assertIn('IsViewable', vintage_window.stdout)
            overlay.vintage(False)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                vintage_window = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                                capture_output=True, text=True)
                if 'IsUnMapped' in vintage_window.stdout:
                    break
                time.sleep(.05)
            self.assertIn('IsUnMapped', vintage_window.stdout)
            overlay.set_layer('overlay', False)
            self.assertTrue(self.wait_for('IsUnMapped'))
            overlay.set_layer('overlay', True)
            self.assertTrue(self.wait_for('IsViewable'))
            overlay.starwars('Hello moderator')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                        capture_output=True, text=True)
                if result.returncode == 0 and 'IsViewable' in result.stdout:
                    break
                time.sleep(0.05)
            self.assertEqual(result.returncode, 0)
            self.assertIn('IsViewable', result.stdout)
        finally:
            self.assertTrue(overlay.stop())
        self.assertFalse(overlay.is_running())

    def test_screensharing_effect_covers_x11_screen(self):
        root = subprocess.run(['xwininfo', '-root'], capture_output=True, text=True, check=True).stdout
        width = int(re.search(r'Width:\s+(\d+)', root).group(1))
        height = int(re.search(r'Height:\s+(\d+)', root).group(1))
        overlay = DesktopOverlay(screensharing=True)
        image = os.path.join(os.path.dirname(__file__), '..', 'img', 'itmb-logo.png')
        overlay.start(os.path.abspath(image))
        try:
            self.assertTrue(self.wait_for('IsViewable'), overlay.status())
            overlay.starwars('Screensharing test')
            deadline = time.monotonic() + 5
            result = None
            while time.monotonic() < deadline:
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                        capture_output=True, text=True)
                if result.returncode == 0 and 'IsViewable' in result.stdout:
                    break
                time.sleep(0.05)
            self.assertIsNotNone(result)
            self.assertEqual(result.returncode, 0)
            self.assertIn(f'Width: {width}', result.stdout)
            self.assertIn(f'Height: {height}', result.stdout)
            self.assertIn('Absolute upper-left X:  0', result.stdout)
            self.assertIn('Absolute upper-left Y:  0', result.stdout)
        finally:
            overlay.stop()

    def test_screensharing_image_layer_shows_and_removes(self):
        overlay = DesktopOverlay(screensharing=True)
        image = os.path.join(os.path.dirname(__file__), '..', 'img', 'itmb-logo.png')
        overlay.start(os.path.abspath(image))
        try:
            self.assertTrue(self.wait_for('IsViewable'), overlay.status())
            overlay.put_effect('media', ImageLayer(Image.new('RGBA', (20, 20), 'red')))
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                        capture_output=True, text=True)
                if result.returncode == 0 and 'IsViewable' in result.stdout:
                    break
                time.sleep(.05)
            self.assertIn('IsViewable', result.stdout)
            overlay.remove_effect('media')
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                        capture_output=True, text=True)
                if 'IsUnMapped' in result.stdout:
                    break
                time.sleep(.05)
            self.assertIn('IsUnMapped', result.stdout)
        finally:
            overlay.stop()


if __name__ == '__main__':
    unittest.main()
