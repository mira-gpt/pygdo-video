import tomllib
import unittest
from pathlib import Path

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.youtube import youtube


class YouTubeHelpTest(unittest.TestCase):
    def test_action_choices_and_help_are_consistent(self):
        Application.mode(Mode.render_cli)
        choices = youtube().gdo_parameters()[0].init_choices()
        self.assertEqual({'start', 'stop', 'status'}, set(choices))
        languages = Path(__file__).resolve().parents[1] / 'lang'
        for language in ('en', 'de'):
            with (languages / f'video_{language}.toml').open('rb') as source:
                description = tomllib.load(source)['md_video_youtube']
            for choice in choices:
                self.assertIn(choice, description)
