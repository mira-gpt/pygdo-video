import unittest
from unittest.mock import MagicMock

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.yt_embed import yt_embed


class YoutubeEmbedMethodTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_returns_code_as_escaped_html(self):
        command = yt_embed()
        command.param_val = MagicMock(return_value='https://youtu.be/dQw4w9WgXcQ')
        result = command.gdo_execute()
        self.assertEqual('video.yt.embed', command.gdo_trigger())
        self.assertIn('<iframe', result.render_txt())
        self.assertIn('&lt;iframe', result.render_html())
        self.assertNotIn('<iframe', result.render_html())

    def test_invalid_url_reports_error(self):
        command = yt_embed()
        command.param_val = MagicMock(return_value='https://example.org/')
        command.err = MagicMock(return_value='invalid')
        self.assertEqual('invalid', command.gdo_execute())
