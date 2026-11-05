import unittest
from unittest.mock import MagicMock, patch

from PIL import Image

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.AsciiArt import AsciiArt
from gdo.video.method.asciiart import asciiart
from gdo.video.method.ipc_asciiart import ipc_asciiart


class AsciiArtTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_filter_transforms_frame_then_expires(self):
        frame = Image.new('RGB', (160, 90), 'white')
        original = frame.tobytes()
        effect = AsciiArt(5, now=0)
        self.assertTrue(effect.draw(frame, now=1))
        self.assertNotEqual(frame.tobytes(), original)
        self.assertFalse(effect.draw(frame, now=5))

    def test_command_queues_dog_and_handler_installs_key(self):
        command = asciiart()
        command.param_value = MagicMock(return_value=5.0)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
             patch('gdo.video.method.asciiart.IPC.send_to_dog') as send:
            self.assertEqual('queued', command.gdo_execute())
        send.assert_called_once_with('video.ipc_asciiart', ['5.0s'])
        handler = ipc_asciiart()
        handler.param_value = MagicMock(return_value=5.0)
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_asciiart.module_video.instance', return_value=module):
            handler.gdo_execute()
        self.assertEqual(module.connector.put_effect.call_args.args[0], 'asciiart')
        self.assertIsInstance(module.connector.put_effect.call_args.args[1], AsciiArt)
