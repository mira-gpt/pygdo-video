import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.DuckLayer import DuckLayer
from gdo.video.DuckStatus import volume_label
from gdo.video.VideoConnector import VideoConnector
from gdo.video.module_video import module_video


class DuckLanguageTest(unittest.TestCase):
    def test_language_is_drawn_only_when_configured(self):
        layer = DuckLayer()
        frame = Image.new('RGB', (640, 360))
        layer.draw_mic_language(frame)
        self.assertIsNone(frame.getbbox())
        layer.mic_language = 'fr'
        layer.draw_mic_language(frame)
        self.assertIsNotNone(frame.getbbox())

    def test_compositor_updates_existing_duck(self):
        connector = VideoConnector()
        duck = MagicMock()
        connector.effects.get = MagicMock(return_value=duck)
        connector.set_mic_language('de')
        self.assertEqual('de', duck.mic_language)

    def test_desktop_update_is_sent_to_existing_duck(self):
        overlay = DesktopOverlay()
        overlay.is_running = MagicMock(return_value=True)
        overlay.duck_enabled = True
        overlay._send_payload = MagicMock()
        overlay.set_mic_language('fr')
        overlay._send_payload.assert_called_once_with({'effect': 'duck_language', 'language': 'fr'})

    def test_volume_format_and_validation(self):
        self.assertEqual('32%', volume_label('32.0'))
        self.assertEqual('32.5%', volume_label(32.5))
        self.assertEqual('0%', volume_label(0))
        for value in (None, 'bad', -1, 101, float('nan')):
            self.assertEqual('', volume_label(value))

    def test_volume_drawn_even_without_language(self):
        layer = DuckLayer()
        layer.speech_volume = '32.0'
        frame = Image.new('RGB', (640, 360))
        layer.draw_mic_language(frame)
        self.assertIsNotNone(frame.getbbox())

    def test_volume_updates_existing_duck_in_both_backends(self):
        connector = VideoConnector()
        duck = MagicMock()
        connector.effects.get = MagicMock(return_value=duck)
        connector.set_speech_volume('32.0')
        self.assertEqual('32.0', duck.speech_volume)
        overlay = DesktopOverlay()
        overlay.is_running = MagicMock(return_value=True)
        overlay.duck_enabled = True
        overlay._send_payload = MagicMock()
        overlay.set_speech_volume('32.0')
        overlay._send_payload.assert_called_once_with({'effect': 'duck_volume', 'volume': '32.0'})

    def test_initial_volume_reads_audio_configuration(self):
        audio = MagicMock()
        audio.is_enabled.return_value = True
        audio.get_config_val.return_value = '32.0'
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance') as loader:
            loader.return_value.get_module.return_value = audio
            self.assertEqual('32.0', module_video.current_speech_volume())
        audio.get_config_val.assert_called_once_with('audio_speech_volume')


class DuckVolumeEventTest(unittest.IsolatedAsyncioTestCase):
    async def test_volume_change_reaches_connector(self):
        module = module_video()
        module.connector = MagicMock()
        field = MagicMock()
        field.get_val.return_value = '45.0'
        await module.on_speech_volume_changed(None, field)
        module.connector.set_speech_volume.assert_called_once_with('45.0')
