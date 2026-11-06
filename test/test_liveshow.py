import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.MicrophoneLevel import MicrophoneLevel
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.ipc_liveshow import ipc_liveshow
from gdo.video.method.liveshow import liveshow
from gdo.video.module_video import module_video


class LiveShowTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_queues_command(self):
        method = liveshow()
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.liveshow.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_liveshow', ['1'])

    async def test_dog_persists_mode(self):
        handler = ipc_liveshow()
        handler.param_value = MagicMock(return_value=True)
        handler.empty = MagicMock()
        mira = MagicMock()
        mira.save_config_val = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_liveshow.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=mira))):
            await handler.gdo_execute()
        mira.save_config_val.assert_awaited_once_with('mira_quacking', '1', force=True)

    async def test_event_updates_video_without_starting_capture(self):
        module = module_video()
        module.connector = MagicMock()
        field = MagicMock()
        field.get_value.return_value = True
        await module.on_mira_quacking_changed(None, field)
        module.connector.liveshow.assert_called_once_with(True)
        module.connector.start.assert_not_called()
        module.connector.microphone_meter.assert_not_called()

    def test_composite_frame_turns_red(self):
        frame = Image.new('RGB', (640, 360))
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('off', 0)), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_text_snapshot', return_value=''):
            MicrophoneLevel(True).draw(frame)
        self.assertEqual(frame.getpixel((458, 326)), (255, 35, 35))

    def test_connector_tracks_mode_before_meter_created(self):
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        worker.liveshow(True)
        worker.microphone_meter(True)
        self.assertTrue(worker.effects.get('mic').liveshow)
        worker.liveshow(False)
        self.assertFalse(worker.effects.get('mic').liveshow)

    def test_desktop_sends_state_without_starting_meter(self):
        worker = DesktopOverlay(screensharing=True)
        worker.process = MagicMock()
        worker.process.poll.return_value = None
        with patch.object(worker, '_send_payload') as send:
            worker.liveshow(True)
        send.assert_called_once_with({'effect': 'liveshow', 'enabled': True})
        self.assertIsNone(worker._mic_stop)
