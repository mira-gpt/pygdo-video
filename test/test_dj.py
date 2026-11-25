import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from gdo.video.method.dj import SHOW_SETTINGS, dj


class DJTest(unittest.TestCase):
    def test_page_is_admin_only(self):
        self.assertEqual('admin', dj().gdo_user_permission())
        self.assertEqual('web', dj().gdo_connectors())

    def test_no_stream_password_in_show_settings(self):
        self.assertNotIn('video_gdo_stream_key', SHOW_SETTINGS['video'])
        self.assertIn('mira_show_host', SHOW_SETTINGS['mira'])
        self.assertIn('video_mic_overlay', SHOW_SETTINGS['video'])

    def test_audio_defaults_are_escaped_and_unavailable_is_safe(self):
        audio = MagicMock()
        audio.get_config_val.return_value = ''
        with patch('gdo.video.method.dj.subprocess.run', side_effect=[
            SimpleNamespace(stdout='<speaker>'), OSError('unavailable')
        ]):
            html = dj.audio_defaults(audio)
        self.assertIn('&lt;speaker&gt;', html)
        self.assertIn('Unavailable from web process', html)


if __name__ == '__main__':
    unittest.main()
