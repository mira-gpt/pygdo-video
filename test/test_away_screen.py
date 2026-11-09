import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.video.AwayScreen import AwayScreen
from gdo.video.DesktopOverlay import DesktopOverlay


class AwayScreenTest(unittest.TestCase):
    def test_cycle_and_render_without_changing_original_message(self):
        screen = AwayScreen(['Back soon', 'Bin gleich zurück'], 1.42, now=10)
        self.assertEqual('Back soon', screen.current(10))
        self.assertEqual('Bin gleich zurück', screen.current(11.5))
        self.assertEqual('Back soon', screen.current(12.9))
        frame = Image.new('RGB', (640, 360), 'white')
        self.assertTrue(screen.draw(frame, now=10))
        self.assertLess(frame.getpixel((0, 0))[0], 255)

    def test_invalid_input_rejected(self):
        for messages, cycle in (([], 1.42), (['hi'], 0), ([''], 1), (['x' * 301], 1)):
            with self.subTest(messages=messages, cycle=cycle), self.assertRaises(ValueError):
                AwayScreen(messages, cycle)

    def test_desktop_sends_one_validated_payload(self):
        overlay = DesktopOverlay(screensharing=True)
        overlay.is_running = MagicMock(return_value=True)
        with patch.object(overlay, '_send_payload') as send:
            overlay.away(['Hello', 'Hallo'], 1.42)
        send.assert_called_once_with({'effect': 'away', 'messages': ['Hello', 'Hallo'], 'cycle': 1.42})
