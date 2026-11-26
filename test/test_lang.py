import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.lang import lang


class VideoLanguageTest(unittest.IsolatedAsyncioTestCase):
    async def test_video_lang_updates_microphone_and_marked_channels(self):
        Application.mode(Mode.render_cli)
        method = lang()
        method.param_val = MagicMock(return_value='de')
        method.reply = MagicMock()
        audio = MagicMock()
        audio.save_config_val = AsyncMock()
        channels = [MagicMock(), MagicMock()]
        with patch('gdo.video.method.lang.module_audio.instance', return_value=audio), \
             patch('gdo.video.method.lang.GDO_Channel.with_setting', return_value=channels) as lookup:
            await method.gdo_execute()
        audio.save_config_val.assert_awaited_once_with('audio_microphone_language', 'de')
        self.assertEqual(('live_channel', '1', '0'), lookup.call_args.args[1:])
        for channel in channels:
            channel.save_val.assert_called_once_with('chan_language', 'de')
        method.reply.assert_called_once_with('video_language_set', (2, 'de'))
        self.assertEqual('owner', method.gdo_user_permission())

