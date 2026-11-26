import unittest
from unittest.mock import MagicMock, patch

from gdo.video.WebMedia import document_for, validate_url, youtube_embed_code, youtube_video_id
from gdo.video.DesktopOverlay import DesktopOverlay


class WebMediaTest(unittest.TestCase):
    def test_youtube_links_generate_user_started_embed(self):
        for url in ('https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'https://youtu.be/dQw4w9WgXcQ?t=4',
                    'https://www.youtube.com/shorts/dQw4w9WgXcQ',
                    'https://youtube.com/live/dQw4w9WgXcQ',
                    'https://www.youtube.com/embed/dQw4w9WgXcQ'):
            with self.subTest(url=url):
                self.assertEqual('dQw4w9WgXcQ', youtube_video_id(url))
                code = youtube_embed_code(url)
                self.assertIn('youtube.com/embed/dQw4w9WgXcQ?', code)
                self.assertIn('loop=1&amp;playlist=dQw4w9WgXcQ', code)
                self.assertNotIn('autoplay', code)
                self.assertIn(code, document_for(url))

    def test_youtube_rejects_lookalike_and_bad_ids(self):
        for url in ('https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ',
                    'https://youtu.be/invalid', 'https://youtube.com/watch?v=dQw4w9WgXcQ&v=abcdefghijk'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                youtube_embed_code(url)

    def test_cyclone_spirals_into_final_position(self):
        from gdo.video.MediaTransition import media_transition
        start = media_transition('cyclone', 0, 1000, 100, 100)
        middle = media_transition('cyclone', .25, 1000, 100, 100)
        end = media_transition('cyclone', 2, 1000, 100, 100)
        self.assertNotEqual(start[:2], end[:2])
        self.assertGreater(middle[1], 100)
        self.assertEqual(end, (100.0, 100.0, 0.0, 1.0))

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

    def test_autoplay_is_explicit_for_video_and_youtube(self):
        url = 'https://example.org/movie.mp4'
        self.assertNotIn(' autoplay', document_for(url))
        self.assertIn(' autoplay', document_for(url, autoplay=True))
        youtube = 'https://youtu.be/dQw4w9WgXcQ'
        self.assertNotIn('autoplay', document_for(youtube))
        self.assertIn('autoplay=1', document_for(youtube, autoplay=True))
        self.assertIn('allow="autoplay;', document_for(youtube, autoplay=True))

    def test_desktop_uses_monitor_geometry_and_cleans_up(self):
        overlay = DesktopOverlay(geometry=(1920, 1080, 100, 20))
        overlay.is_running = MagicMock(return_value=True)
        overlay.remove_effect = MagicMock()
        with patch('gdo.video.DesktopOverlay.subprocess.Popen') as popen:
            popen.return_value.poll.return_value = None
            overlay.show_web_media('https://example.org', '50%', '50%', '10%', '10%', 'throw')
            args = popen.call_args.args[0]
            self.assertEqual(['292', '128', '960', '540', 'throw', '', '0'], args[-7:])
            overlay._stop_web_media()
            popen.return_value.terminate.assert_called_once()
