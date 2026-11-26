import unittest
from unittest.mock import MagicMock, patch

from gdo.video.WebMedia import document_for, validate_url
from gdo.video.DesktopOverlay import DesktopOverlay


class WebMediaTest(unittest.TestCase):
    def test_url_validation(self):
        for url in ('https://example.org/a', 'http://example.org', 'file:///tmp/a.png'):
            self.assertEqual(validate_url(url), url)
        for url in ('javascript:alert(1)', 'file://host/a', 'https://u:p@example.org/'):
            with self.assertRaises(ValueError):
                validate_url(url)

    def test_video_is_user_started_and_loops(self):
        document = document_for('https://example.org/movie.mp4?x=1&y=2')
        self.assertIn('<video controls loop playsinline', document)
        self.assertNotIn('autoplay', document)
        self.assertIn('&amp;', document)
        self.assertIsNone(document_for('https://example.org/page'))

    def test_desktop_uses_monitor_geometry_and_cleans_up(self):
        overlay = DesktopOverlay(geometry=(1920, 1080, 100, 20))
        overlay.is_running = MagicMock(return_value=True)
        overlay.remove_effect = MagicMock()
        with patch('gdo.video.DesktopOverlay.subprocess.Popen') as popen:
            popen.return_value.poll.return_value = None
            overlay.show_web_media('https://example.org', '50%', '50%', '10%', '10%', 'throw')
            args = popen.call_args.args[0]
            self.assertEqual(['292', '128', '960', '540', 'throw'], args[-5:])
            overlay._stop_web_media()
            popen.return_value.terminate.assert_called_once()
