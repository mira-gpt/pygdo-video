import os
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image

from gdo.video.VideoConnector import VideoConnector


class CompositorTest(unittest.TestCase):
    def test_real_preview_process_accepts_composite(self):
        with tempfile.TemporaryDirectory() as directory:
            image = os.path.join(directory, 'background.png')
            Image.new('RGB', (20, 20), 'blue').save(image)
            connector = VideoConnector()
            with patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy'}):
                connector.start(None, image, True, False, None)
                try:
                    self.assertEqual(connector.background.getpixel((0, 0)), (0, 0, 255))
                    self.assertEqual(connector.background.getpixel((639, 359)), (0, 0, 255))
                    time.sleep(1)
                    self.assertIn('running', connector.status())
                    self.assertIsNone(connector.outputs[0].poll())
                finally:
                    self.assertTrue(connector.stop())

    def test_background_and_desktop_switch_with_running_output(self):
        with tempfile.TemporaryDirectory() as directory:
            image = os.path.join(directory, 'background.png')
            Image.new('RGB', (20, 20), 'red').save(image)
            connector = VideoConnector()
            sink = ['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'rawvideo',
                    '-pixel_format', 'rgb24', '-video_size', '640x360', '-framerate', '15',
                    '-i', 'pipe:0', '-f', 'null', '-']
            capture = ['ffmpeg', '-nostdin', '-loglevel', 'error', '-re', '-f', 'lavfi',
                       '-i', 'testsrc=size=640x360:rate=15', '-pix_fmt', 'rgb24',
                       '-f', 'rawvideo', 'pipe:1']
            with patch.object(VideoConnector, 'output_commands', return_value=[sink]), \
                 patch.object(VideoConnector, 'desktop_command', return_value=capture):
                connector.start(':0', image, True, False, '')
                try:
                    deadline = time.monotonic() + 5
                    while connector.frame is None and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertIsNotNone(connector.frame, connector.status())
                    original_output = connector.outputs[0]
                    connector.set_layer('desktop', False)
                    deadline = time.monotonic() + 5
                    while connector.capture is not None and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertIsNone(connector.capture)
                    self.assertIs(original_output, connector.outputs[0])
                    connector.set_layer('bg_image', False)
                    self.assertIn('bg_image=off', connector.status())
                    connector.set_layer('desktop', True)
                    deadline = time.monotonic() + 5
                    while connector.frame is None and time.monotonic() < deadline:
                        time.sleep(0.05)
                    self.assertIsNotNone(connector.frame, connector.status())
                    self.assertIs(original_output, connector.outputs[0])
                finally:
                    self.assertTrue(connector.stop())

    def test_output_is_opt_in(self):
        with self.assertRaises(ValueError):
            VideoConnector.output_commands(False, False, '/dev/video2')


if __name__ == '__main__':
    unittest.main()
