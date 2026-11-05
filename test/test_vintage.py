import random
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.Vintage import Vintage
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.vintage import vintage
from gdo.video.method.ipc_vintage import ipc_vintage


class VintageTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_scratches_vary_and_overlay_can_be_removed(self):
        effect = Vintage(random.Random(42))
        frames = []
        for i in range(20):
            frame = Image.new('RGB', (160, 90), (70, 70, 70))
            self.assertTrue(effect.draw(frame, now=10 + i * .1))
            frames.append(frame.tobytes())
        self.assertGreater(len(set(frames)), 5)
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        worker.vintage(True)
        self.assertEqual(worker.effects.ordered()[0][0], 'vintage')
        worker.vintage(False)
        self.assertEqual(worker.effects.ordered(), [])

    def test_command_and_dog_handler(self):
        command = vintage()
        command.param_value = MagicMock(return_value=True)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
             patch('gdo.video.method.vintage.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_vintage', ['1'])
        handler = ipc_vintage()
        handler.param_value = MagicMock(return_value=False)
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_vintage.module_video.instance', return_value=module):
            handler.gdo_execute()
        module.connector.vintage.assert_called_once_with(False)
