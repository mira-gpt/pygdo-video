import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.DuckLayer import DuckLayer
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.duck import duck
from gdo.video.method.ipc_duck import ipc_duck


class DuckTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_caption_expires_and_poses_are_cached(self):
        layer = DuckLayer()
        with patch('gdo.video.DuckLayer.time.monotonic', return_value=100):
            layer.caption('Hello stream')
            shown = Image.new('RGB', (640, 360))
            layer.draw(shown)
            layer.draw(Image.new('RGB', (640, 360)))
            self.assertEqual(1, len(layer._scaled))
        with patch('gdo.video.DuckLayer.time.monotonic', return_value=109):
            expired = Image.new('RGB', (640, 360))
            layer.draw(expired)
        self.assertNotEqual(shown.tobytes(), expired.tobytes())

    def test_draw_and_speech_id_prevents_old_end_hiding_new_caption(self):
        layer = DuckLayer()
        before = Image.new('RGB', (640, 360))
        layer.draw(before)
        layer.speech_start('one', 'First')
        layer.speech_start('two', 'Second')
        layer.speech_end('one')
        self.assertEqual('Second', layer.text)
        during = Image.new('RGB', (640, 360))
        layer.draw(during)
        self.assertNotEqual(before.tobytes(), during.tobytes())
        layer.speech_end('two')
        self.assertIsNone(layer.speech_id)
        self.assertEqual('', layer.text)

    def test_command_and_compositor(self):
        method = duck()
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duck.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duck', ['1'])
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        handler = ipc_duck()
        handler.param_value = MagicMock(return_value=True)
        handler.empty = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duck.module_video.instance', return_value=MagicMock(connector=worker)):
            handler.gdo_execute()
        worker.speech_start('id', 'Hello')
        self.assertEqual('Hello', worker.effects.get('duck').text)
        worker.speech_end('id')
        self.assertEqual('', worker.effects.get('duck').text)

    def test_desktop_only_exposes_spoken_text_when_enabled(self):
        worker = DesktopOverlay(screensharing=True)
        worker.process = MagicMock()
        worker.process.poll.return_value = None
        with patch.object(worker, '_send_payload') as send:
            worker.speech_start('id', 'private')
            send.assert_not_called()
            worker.duck(True)
            worker.duck_caption('Hi everyone')
            self.assertEqual({'effect': 'duck_caption', 'text': 'Hi everyone'}, send.call_args.args[0])
            worker.speech_start('first', 'Hello')
            worker.speech_start('second', 'World')
            worker.speech_end('first')
            self.assertEqual('World', send.call_args.args[0]['text'])
            worker.speech_end('second')
            self.assertFalse(send.call_args.args[0]['speaking'])
            worker.duck(False)
            self.assertTrue(send.call_args.args[0]['remove'])
