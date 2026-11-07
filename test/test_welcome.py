import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.welcome import welcome
from gdo.video.module_video import module_video


class WelcomeTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_command_uses_channel_language(self):
        method = welcome()
        method._env_channel = MagicMock()
        method._env_channel.get_lang_iso.return_value = 'de'
        method.param_val = MagicMock(return_value='Tina')
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.welcome.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckwelcome', ['Tina', 'de'])

    async def test_greeting_waves_and_speaks_channel_language(self):
        video = module_video()
        video.duck_event = MagicMock()
        speech = MagicMock()
        speech.input.return_value = speech
        speech.play = AsyncMock()
        with patch('gdo.base.Trans.tiso', return_value='Hallo Tina!') as translate, \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await video.play_welcome('Tina', 'de')
        self.assertEqual(translate.call_args.args[0], 'de')
        video.duck_event.assert_called_once_with('hello')
        speech.input.assert_any_call('text', 'Hallo Tina!')
        speech.input.assert_any_call('lang', 'de')
        speech.play.assert_awaited_once()

    async def test_join_hook_respects_live_mode_and_cooldown(self):
        video = module_video()
        video.play_welcome = AsyncMock()
        mira = MagicMock()
        mira.get_config_value.return_value = False
        loader = MagicMock(get_module=MagicMock(return_value=mira))
        user = MagicMock()
        user.is_type.return_value = False
        user.get_displayname.return_value = 'Tina'
        channel = MagicMock()
        channel.get_lang_iso.return_value = 'de'
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=loader), \
                patch.object(welcome, 'get_config_channel_value', return_value=False) as enabled:
            await video.on_live_join_welcome(user, channel)
            video.play_welcome.assert_not_called()
            mira.get_config_value.return_value = True
            await video.on_live_join_welcome(user, channel)
            video.play_welcome.assert_not_called()
            enabled.return_value = True
            await video.on_live_join_welcome(user, channel)
            await video.on_live_join_welcome(user, channel)
            import asyncio
            await asyncio.sleep(0)
        video.play_welcome.assert_awaited_once_with('Tina', 'de')
        enabled.assert_called_with('video_welcome_enabled')

    def test_channel_opt_in_defaults_off(self):
        setting = welcome._config_channel_for('video_welcome_enabled')
        self.assertEqual(setting.get_initial(), '0')
        self.assertFalse(setting.val(setting.get_initial()).get_value())
