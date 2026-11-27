import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.duckvol import duckvol


class DuckVolumeTest(unittest.IsolatedAsyncioTestCase):
    async def test_updates_shared_speech_setting(self):
        Application.mode(Mode.render_cli)
        method = duckvol()
        method.param_val = MagicMock(return_value='42')
        method.reply = MagicMock()
        audio = MagicMock()
        audio.save_config_val = AsyncMock()
        with patch('gdo.video.method.duckvol.module_audio.instance', return_value=audio):
            await method.gdo_execute()
        audio.save_config_val.assert_awaited_once_with('audio_speech_volume', '42')
        method.reply.assert_called_once_with('video_duck_volume_set', ('42',))
        self.assertEqual('duck.vol', method.gdo_trig())
        self.assertEqual('owner', method.gdo_user_permission())

    def test_volume_parameter_is_bounded(self):
        field = duckvol().gdo_parameters()[0]
        self.assertEqual(0, field._min)
        self.assertEqual(100, field._max)
        self.assertTrue(field._not_null)
