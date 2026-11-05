import unittest
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.Magnify import Magnify
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.magnify import magnify
from gdo.video.method.ipc_magnify import ipc_magnify


class MagnifyTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_mouse_lens_changes_frame_and_follows_pointer(self):
        pointer = MagicMock()
        pointer.position.return_value = (160, 90, 320, 180)
        frame = Image.new('RGB', (320, 180), 'black')
        ImageDraw.Draw(frame).rectangle((155, 85, 165, 95), fill='red')
        lens = Magnify(pointer, zoom=2, radius=32)
        lens.draw(frame)
        self.assertGreater(frame.getpixel((170, 90))[0], 200)
        pointer.position.assert_called_once()

    def test_disabled_desktop_is_not_silently_magnified(self):
        worker = VideoConnector()
        worker.desktop = ':0.0'
        with self.assertRaisesRegex(ValueError, 'desktop source'):
            worker.magnify(True)

    def test_disabling_desktop_removes_magnifier(self):
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        worker.effects.put('magnify', MagicMock())
        worker.set_layer('desktop', False)
        self.assertEqual(worker.effects.ordered(), [])

    def test_command_queues_and_dog_receives_parameters(self):
        command = magnify()
        command.param_value = MagicMock(side_effect={'enabled': True, 'zoom': 3., 'radius': 70}.get)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.magnify.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_magnify', ['1', '3.0', '70'])
        handler = ipc_magnify()
        handler.param_value = MagicMock(side_effect={'enabled': True, 'zoom': 3., 'radius': 70}.get)
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_magnify.module_video.instance', return_value=module):
            handler.gdo_execute()
        module.connector.magnify.assert_called_once_with(True, 3., 70)
