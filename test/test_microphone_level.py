import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.MicrophoneLevel import MicrophoneLevel
from gdo.video.VideoConnector import VideoConnector
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.method.ipc_mic import ipc_mic
from gdo.video.method.mic import mic


class MicrophoneLevelTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_states_draw_and_loud_differs_from_silence(self):
        images = []
        for status, level in [('off', 0), ('unknown', 0), ('on', 0), ('on', .2)]:
            frame = Image.new('RGB', (320, 180))
            with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=(status, level)):
                self.assertTrue(MicrophoneLevel().draw(frame))
            images.append(frame.tobytes())
        self.assertEqual(4, len(set(images)))

    def test_command_and_ipc_adds_layer(self):
        command = mic()
        command.param_value = MagicMock(return_value=True)
        command.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.mic.IPC.send_to_dog') as send:
            command.gdo_execute()
        send.assert_called_once_with('video.ipc_mic', ['1'])
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        handler = ipc_mic()
        handler.param_value = MagicMock(return_value=True)
        handler.empty = MagicMock()
        module = MagicMock(connector=worker)
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_mic.module_video.instance', return_value=module):
            handler.gdo_execute()
        self.assertIsInstance(worker.effects.get('mic'), MicrophoneLevel)

    def test_desktop_meter_starts_and_stops_forwarding(self):
        worker = DesktopOverlay(screensharing=True)
        worker.process = MagicMock()
        worker.process.poll.return_value = None
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('on', .1)), \
                patch.object(worker, '_send_payload') as send:
            worker.microphone_meter(True)
            import time
            deadline = time.monotonic() + 1
            while not send.called and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(send.called)
            worker.microphone_meter(False)
            self.assertEqual({'effect': 'mic', 'remove': True}, send.call_args.args[0])
