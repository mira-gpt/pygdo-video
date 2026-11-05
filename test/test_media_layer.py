import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from gdo.video.MediaLayer import VideoLayer, load_media
from gdo.video.VideoConnector import VideoConnector
from gdo.video.DesktopOverlay import DesktopOverlay


class MediaLayerTest(unittest.TestCase):
    @staticmethod
    def make_video(path):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc2=size=96x64:rate=10', '-t', '2', '-c:v', 'mpeg4', str(path)],
                       check=True, timeout=15)

    def test_real_video_decodes_and_cleans_up_when_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'video.mp4'
            self.make_video(path)
            layer = load_media(path.as_uri())
            self.assertIsInstance(layer, VideoLayer)
            worker = VideoConnector()
            worker.worker = MagicMock()
            worker.worker.is_alive.return_value = True
            try:
                worker.put_effect('media', layer)
                deadline = time.monotonic() + 5
                while layer.generation < 2 and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertGreaterEqual(layer.generation, 2)
                self.assertFalse(layer.finished)
                self.assertTrue(worker.remove_effect('media'))
                self.assertFalse(os.path.exists(layer.path))
            finally:
                layer.close()

    @unittest.skipUnless(os.environ.get('PYGDO_VIDEO_GUI_TEST') == '1', 'requires an X11 desktop')
    def test_real_video_is_sent_to_desktop_overlay_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'video.mp4'
            self.make_video(path)
            layer = load_media(path.as_uri())
            overlay = DesktopOverlay(screensharing=True)
            logo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'img', 'itmb-logo.png'))
            overlay.start(logo)
            try:
                deadline = time.monotonic() + 5
                while not overlay.is_running() and time.monotonic() < deadline:
                    time.sleep(.05)
                overlay.put_effect('media', layer)
                while layer.generation < 2 and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertGreaterEqual(layer.generation, 2)
                self.assertTrue(overlay.is_running())
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn('IsViewable', result.stdout)
                overlay.remove_effect('media')
                self.assertFalse(os.path.exists(layer.path))
            finally:
                overlay.stop()
                layer.close()
