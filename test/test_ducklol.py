import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.StarWarsIPC import decode_text, encode_text
from gdo.video.method.ipc_ducklol import ipc_ducklol
from gdo.video.method.lol import lol


class DuckLolTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_full_text_and_language_queued(self):
        method = lol()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hallo alle zusammen!', 'lang': 'de'}[key])
        method.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.lol.IPC.send_to_dog') as send:
            self.assertEqual('queued', method.gdo_execute())
        name, args = send.call_args.args
        self.assertEqual('video.ipc_ducklol', name)
        self.assertEqual('Hallo alle zusammen!', decode_text(args[0]))
        self.assertEqual('de', args[1])
        field = method.gdo_parameters()[0]
        field.val(['Hallo', 'alle', 'zusammen!'])
        self.assertEqual('Hallo alle zusammen!', field.get_value())

    def test_user_language_precedes_channel(self):
        method = lol()
        method._env_user = MagicMock()
        method._env_user.get_lang_iso.return_value = 'de'
        method._env_channel = MagicMock()
        method._env_channel.get_lang_iso.return_value = 'en'
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Hallo', 'lang': None}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.lol.IPC.send_to_dog') as send:
            method.gdo_execute()
        self.assertEqual('de', send.call_args.args[1][1])

    async def test_speech_ends_before_idle(self):
        method = ipc_ducklol()
        method.param_val = MagicMock(side_effect=lambda key: {'payload': encode_text('Hallo Welt'), 'lang': 'de'}[key])
        method.empty = MagicMock()
        connector = MagicMock()
        speech = MagicMock()
        speech.input.return_value = speech
        async def speak():
            connector.duck_animation.assert_called_once_with('lol')
        speech.gdo_execute = AsyncMock(side_effect=speak)
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_ducklol.module_video.instance', return_value=MagicMock(connector=connector)), \
                patch('gdo.video.method.ipc_ducklol.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=None))), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await method.gdo_execute()
        self.assertEqual(['lol', 'idle'], [call.args[0] for call in connector.duck_animation.call_args_list])
        speech.input.assert_any_call('text', 'Hallo Welt')
        speech.input.assert_any_call('lang', 'de')

    async def test_idle_restored_even_if_speech_fails(self):
        method = ipc_ducklol()
        method.param_val = MagicMock(side_effect=lambda key: {'payload': encode_text('Oops'), 'lang': 'en'}[key])
        method.empty = MagicMock()
        connector = MagicMock()
        speech = MagicMock()
        speech.input.return_value = speech
        speech.gdo_execute = AsyncMock(side_effect=RuntimeError('failure'))
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_ducklol.module_video.instance', return_value=MagicMock(connector=connector)), \
                patch('gdo.video.method.ipc_ducklol.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=None))), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech), \
                patch('gdo.video.method.ipc_ducklol.Logger.warning'):
            await method.gdo_execute()
        self.assertEqual(['lol', 'idle'], [call.args[0] for call in connector.duck_animation.call_args_list])

    async def test_return_uses_mood_at_end_not_start(self):
        method = ipc_ducklol()
        method.param_val = MagicMock(side_effect=lambda key: {'payload': encode_text('Hello'), 'lang': 'en'}[key])
        method.empty = MagicMock()
        connector = MagicMock()
        saved_mood = MagicMock()
        saved_mood.cfg_mira_mood.return_value = 'quacking'
        loader = MagicMock()
        loader.get_module.return_value = saved_mood
        speech = MagicMock()
        speech.input.return_value = speech
        speech.gdo_execute = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_ducklol.module_video.instance', return_value=MagicMock(connector=connector)), \
                patch('gdo.video.method.ipc_ducklol.ModuleLoader.instance', return_value=loader), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await method.gdo_execute()
        self.assertEqual(['lol', 'quacking'], [call.args[0] for call in connector.duck_animation.call_args_list])
