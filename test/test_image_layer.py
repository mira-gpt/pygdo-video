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
        values = {'url': 'file:///tmp/image.png', 'width': '25%', 'height': '25%', 'x': '2%', 'y': '2%'}
        command.param_val = MagicMock(side_effect=values.get)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.media.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_media', list(values.values()))
