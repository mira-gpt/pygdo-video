import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.base.Parser import Parser
from gdo.base.Render import Mode
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWars import StarWars
from gdo.video.StarWarsIPC import decode_text, encode_text
from gdo.video.method.starwars import starwars
from gdo.video.method.ipc_starwars import ipc_starwars
from gdo.video.VideoConnector import VideoConnector


class StarWarsTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

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
        outer.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
             patch('gdo.video.method.starwars.IPC.send_to_dog') as send:
            self.assertEqual('queued', await parsed._nested_execute(parsed, True))
        self.assertEqual('video.ipc_starwars', send.call_args.args[0])
        self.assertEqual('Hello moderator', decode_text(send.call_args.args[1][0]))
        inner.execute.assert_awaited_once()

    def test_dog_executes_queued_effect(self):
        handler = ipc_starwars()
        handler.param_val = MagicMock(return_value=encode_text('Hello moderator'))
        handler.empty = MagicMock(return_value=None)
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_starwars.module_video.instance', return_value=module):
            handler.gdo_execute()
        module.connector.starwars.assert_called_once_with('Hello moderator')

    def test_dispatch_waits_for_transaction_commit(self):
        method = starwars()
        method.param_value = MagicMock(return_value='Hello')
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = True
        with patch.object(Application, 'db', return_value=db), \
             patch.object(Application, 'defer_after_commit') as deferred, \
             patch('gdo.video.method.starwars.IPC.send_to_dog') as send:
            self.assertEqual('queued', method.gdo_execute())
        send.assert_not_called()
        self.assertEqual(deferred.call_args.args[0], send)
        self.assertEqual(decode_text(deferred.call_args.args[2][0]), 'Hello')

    def test_preview_dimensions_do_not_change_frame_size(self):
        command = VideoConnector.output_commands(True, False, None, 480, 270)[0]
        self.assertEqual(command[command.index('-x') + 1], '480')
        self.assertEqual(command[command.index('-y') + 1], '270')
        self.assertEqual(command[command.index('-video_size') + 1], '640x360')

    def test_ipc_rejects_invalid_or_oversized_payloads(self):
        for payload in ('not base64!', 'x' * 1025):
            with self.subTest(payload=payload[:10]), self.assertRaises(ValueError):
                decode_text(payload)

    def test_text_is_bounded(self):
        for text in ('', ' ' * 4, 'x' * 4097):
            with self.subTest(size=len(text)), self.assertRaises(ValueError):
                StarWars(text)
