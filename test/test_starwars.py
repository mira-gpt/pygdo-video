import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.base.Parser import Parser
from gdo.base.Render import Mode
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWars import StarWars
from gdo.video.method.starwars import starwars


class StarWarsTest(unittest.IsolatedAsyncioTestCase):
    def test_effect_draws_and_expires(self):
        effect = StarWars('Hello moderator', now=0)
        frame = Image.new('RGB', (640, 360), 'black')
        self.assertTrue(effect.draw(frame, now=2))
        self.assertIsNotNone(frame.getbbox())
        self.assertFalse(effect.draw(frame, now=100))

    async def test_nested_gdo_result_becomes_effect_text(self):
        Application.mode(Mode.render_cli)
        outer, inner = starwars(), Method()
        inner.execute = AsyncMock(return_value=GDT_String().val('Hello moderator'))
        parser = Parser(Mode.render_cli, None, None, None, None)
        with patch.object(parser, 'get_method', side_effect=lambda name: outer if name == 'video.starwars' else inner):
            parsed = parser.parse_line('video.starwars $(wget https://example.test/hello.txt)')
        module = MagicMock()
        outer.reply = MagicMock(return_value='started')
        with patch('gdo.video.method.starwars.module_video.instance', return_value=module):
            self.assertEqual('started', await parsed._nested_execute(parsed, True))
        module.connector.starwars.assert_called_once_with('Hello moderator')
        inner.execute.assert_awaited_once()

    def test_text_is_bounded(self):
        for text in ('', ' ' * 4, 'x' * 4097):
            with self.subTest(size=len(text)), self.assertRaises(ValueError):
                StarWars(text)
