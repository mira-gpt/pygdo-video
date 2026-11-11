import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_transcript_fades_after_ten_seconds(self):
        from gdo.video.TranscriptFade import transcript_alpha
        self.assertEqual(1, transcript_alpha(110, 100))
        self.assertAlmostEqual(.5, transcript_alpha(110.5, 100))
        self.assertEqual(0, transcript_alpha(111, 100))
        self.assertEqual(1, transcript_alpha(110.5, 105))

    def test_zero_warning_cycles_only_after_sustained_valid_zero(self):
        from gdo.video.MicWarning import MicWarning
        warning = MicWarning()
        texts = ['first', 'second']
        self.assertIsNone(warning.update('on', 0, 10, texts))
        self.assertIsNone(warning.update('on', 0, 12.9, texts))
        self.assertEqual('first', warning.update('on', 0, 13, texts))
        self.assertEqual('second', warning.update('on', 0, 17, texts))
        self.assertIsNone(warning.update('on', .001, 18, texts))
        self.assertIsNone(warning.update('unknown', 0, 25, texts))
        self.assertIsNone(warning.update('on', 0, 30, texts))

    def test_warning_translations_cover_voice_languages(self):
        import tomlkit
        from pathlib import Path
        from gdo.audio.language import LANGUAGES
        directory = Path(__file__).resolve().parents[1] / 'lang'
        for iso in LANGUAGES:
            with self.subTest(language=iso):
                data = tomlkit.parse((directory / f'video_{iso}.toml').read_text())
                self.assertTrue(data['video_mic_no_gain'])

    def test_zero_level_replaces_transcript_after_delay(self):
        overlay = MicrophoneLevel()
        frame = Image.new('RGB', (320, 180))
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('on', 0)), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'), \
                patch('gdo.video.MicrophoneLevel.warning_texts', return_value=['Microphone off']), \
                patch('gdo.video.MicrophoneLevel.time.monotonic', return_value=10):
            overlay.draw(frame)
        first = frame.tobytes()
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('on', 0)), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'), \
                patch('gdo.video.MicrophoneLevel.warning_texts', return_value=['Microphone off']), \
                patch('gdo.video.MicrophoneLevel.time.monotonic', return_value=14):
            overlay.draw(frame)
        self.assertNotEqual(first, frame.tobytes())

    def test_states_draw_and_loud_differs_from_silence(self):
        images = []
        for status, level, transcription, text in [('off', 0, 'off', ''), ('on', .2, 'off', ''), ('on', .2, 'on', 'Hello there')]:
            frame = Image.new('RGB', (320, 180))
            with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=(status, level)), \
                 patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value=transcription), \
                 patch('gdo.audio.meter.MicrophoneMeter.transcription_text_snapshot', return_value=text):
                self.assertTrue(MicrophoneLevel().draw(frame))
            images.append(frame.tobytes())
        self.assertEqual(3, len(set(images)))

    def test_meter_is_in_bottom_right(self):
        from gdo.video.TickerLayout import ticker_bounds
        frame = Image.new('RGB', (640, 360))
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('off', 0)), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_text_snapshot', return_value=''):
            MicrophoneLevel().draw(frame)
        self.assertNotEqual((0, 0, 0), frame.getpixel((458, 326)))
        self.assertEqual((0, 0, 0), frame.getpixel((12, 326)))
        left, right = ticker_bounds(640)
        self.assertEqual((384, 628), (left, right))
        self.assertNotEqual((0, 0, 0), frame.getpixel((left, 326)))

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
        module.save_config_val = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_mic.module_video.instance', return_value=module):
            asyncio.run(handler.gdo_execute())
        self.assertIsInstance(worker.effects.get('mic'), MicrophoneLevel)

    def test_desktop_meter_starts_and_stops_forwarding(self):
        worker = DesktopOverlay(screensharing=True)
        worker.process = MagicMock()
        worker.process.poll.return_value = None
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('on', .1)), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'), \
                patch('gdo.audio.meter.MicrophoneMeter.transcription_text_snapshot', return_value=''), \
                patch.object(worker, '_send_payload') as send:
            worker.microphone_meter(True)
            import time
            deadline = time.monotonic() + 1
            while not send.called and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertTrue(send.called)
            self.assertEqual('off', send.call_args.args[0]['transcription'])
            self.assertEqual('', send.call_args.args[0]['text'])
            from gdo.audio.meter import MicrophoneMeter
            before = send.call_count
            MicrophoneMeter.update(b'\x00\x40' * 100)
            deadline = time.monotonic() + 1
            while send.call_count == before and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertGreater(send.call_count, before)
            worker.microphone_meter(False)
            self.assertEqual({'effect': 'mic', 'remove': True}, send.call_args.args[0])
