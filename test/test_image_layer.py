import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.ImageLayer import ImageLayer
from gdo.video.method.media import media


class ImageLayerTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_file_overlay_defaults_and_transparency(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'image.png'
            Image.new('RGBA', (40, 20), (255, 0, 0, 255)).save(path)
            layer = ImageLayer.load(path.as_uri())
        frame = Image.new('RGB', (400, 200), 'blue')
        self.assertTrue(layer.draw(frame))
        self.assertEqual(frame.getpixel((10, 6)), (255, 0, 0))
        self.assertEqual(frame.getpixel((0, 0)), (0, 0, 255))
        self.assertEqual(frame.getpixel((110, 6)), (0, 0, 255))

    def test_untrusted_sizes_and_source_are_rejected(self):
        with self.assertRaises(ValueError):
            ImageLayer.load('file://remote/image.png')
        with self.assertRaises(ValueError):
            ImageLayer(Image.new('RGB', (2, 2)), width='-5px')
        with self.assertRaises(ValueError):
            ImageLayer(Image.new('RGB', (2, 2)), width='500%').output_size(640, 360)

    def test_command_queues_image_and_geometry(self):
        command = media()
        values = {'url': 'file:///tmp/image.png', 'width': '25%', 'height': '25%', 'x': '2%', 'y': '2%', 'transition': 'throw'}
        command.param_val = MagicMock(side_effect=values.get)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.media.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_media', list(values.values()))

    def test_fade_and_throw_positions(self):
        from gdo.video.MediaTransition import media_transition
        self.assertEqual((10, 20, 0.0, 0.0), media_transition('fade', 0, 400, 10, 20))
        self.assertEqual((10, 20, 0.0, 1.0), media_transition('fade', 1, 400, 10, 20))
        x, y, angle, alpha = media_transition('throw', 0, 400, 10, 20)
        self.assertEqual((-400, 20, 900, 1.0), (x, y, angle, alpha))
        self.assertEqual((10, 20, 0.0, 1.0), media_transition('throw', 1.2, 400, 10, 20))

    def test_fade_draw_preserves_target_before_and_after(self):
        layer = ImageLayer(Image.new('RGBA', (20, 20), 'red'), width='20px', height='20px', x='0px', y='0px', transition='fade')
        with patch('gdo.video.ImageLayer.time.monotonic', return_value=10):
            layer.begin_transition()
            frame = Image.new('RGB', (100, 100), 'blue')
            layer.draw(frame)
        self.assertEqual((0, 0, 255), frame.getpixel((5, 5)))
        with patch('gdo.video.ImageLayer.time.monotonic', return_value=11):
            layer.draw(frame)
        self.assertEqual((255, 0, 0), frame.getpixel((5, 5)))

    def test_desktop_video_frames_do_not_restart_transition(self):
        from gdo.video.DesktopOverlay import DesktopOverlay
        layer = ImageLayer(Image.new('RGBA', (4, 4), 'red'), transition='throw')
        overlay = DesktopOverlay(screensharing=True)
        first = overlay._image_payload(layer, layer.image, transition_start=True)
        later = overlay._image_payload(layer, layer.image)
        self.assertTrue(first['transition_start'])
        self.assertFalse(later['transition_start'])
        self.assertEqual('throw', later['transition'])
