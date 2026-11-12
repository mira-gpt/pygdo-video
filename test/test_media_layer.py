import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image

from gdo.video.MediaLayer import VideoLayer, load_media
from gdo.video.VideoConnector import VideoConnector
from gdo.video.DesktopOverlay import DesktopOverlay


class MediaLayerTest(unittest.TestCase):
    def test_video_transition_waits_for_first_drawable_frame(self):
        layer = VideoLayer('/unused', transition='throw')
        layer.begin_transition()
        frame = Image.new('RGBA', (640, 360))
        with patch('gdo.video.ImageLayer.time.monotonic', return_value=100):
            layer.draw(frame)
            self.assertIsNone(layer.transition_start)
            layer.generation = 1
            layer.draw(frame)
            self.assertEqual(100, layer.transition_start)

    def test_desktop_waits_for_first_frame_to_start_transition(self):
        overlay = DesktopOverlay()
        overlay.is_running = MagicMock(return_value=True)
        overlay._send_payload = MagicMock()
        layer = VideoLayer('/unused', transition='throw')
        layer.start = MagicMock()
        image = Image.new('RGBA', (10, 10), 'red')
        layer.snapshot = MagicMock(side_effect=[(image, 0, False), (image, 1, False),
                                                (image, 2, False), (image, 2, True)])
        with patch('gdo.video.DesktopOverlay.threading.Thread') as thread, \
             patch('gdo.video.DesktopOverlay.time.sleep'):
            overlay.put_effect('media', layer)
            self.assertEqual({'effect': 'image', 'remove': True}, overlay._send_payload.call_args.args[0])
            thread.assert_called_once()
            overlay._pump_video(layer)
        messages = [call.args[0] for call in overlay._send_payload.call_args_list]
        frames = [message for message in messages if 'png' in message]
        self.assertEqual(2, len(frames))
        self.assertTrue(frames[0]['transition_start'])
        self.assertFalse(frames[1]['transition_start'])
        self.assertEqual({'effect': 'image', 'remove': True}, messages[-1])

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
            suffix = f' [test-media-{os.getpid()}]'
            overlay = DesktopOverlay(screensharing=True, window_suffix=suffix)
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
                result = subprocess.run(['xwininfo', '-name', 'Mira Starwars Effect' + suffix],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn('IsViewable', result.stdout)
                overlay.remove_effect('media')
                self.assertFalse(os.path.exists(layer.path))
            finally:
                overlay.stop()
                layer.close()
