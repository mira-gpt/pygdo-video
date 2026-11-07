import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.duckmoods import duckmoods


class DuckMoodsTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_base_moods_are_italic_and_current_is_bold(self):
        mira = MagicMock()
        mira.cfg_mira_mood.return_value = 'music'
        with patch('gdo.video.method.duckmoods.module_mira.instance', return_value=mira):
            text = duckmoods().gdo_execute().render(Mode.render_markdown)
        self.assertIn('***music***', text)
        self.assertIn('*idle*', text)
        self.assertIn('lol', text)
        self.assertIn('rolleye', text)
        self.assertNotIn('*lol*', text)

    def test_trigger(self):
        self.assertEqual('duck.moods', duckmoods.gdo_trig())
