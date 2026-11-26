import unittest
from unittest.mock import MagicMock

from PIL import Image
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.DuckLayer import DuckLayer
from gdo.video.VideoConnector import VideoConnector


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
