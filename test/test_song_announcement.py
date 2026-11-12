import unittest
from unittest.mock import MagicMock, patch

from gdo.video.module_video import module_video


class SongAnnouncementTest(unittest.IsolatedAsyncioTestCase):
    async def test_announcement_requires_opt_in_and_thoughts_audio(self):
        module = module_video()
        module._commentary_follower = MagicMock()
        module.get_config_value = MagicMock(return_value=True)
        audio = MagicMock()
        audio.is_enabled.return_value = True
        audio.get_config_val.return_value = 'de'
        loader = MagicMock()
        loader.get_module.return_value = audio
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=loader), \
                patch('gdo.base.Trans.Trans.tiso2', return_value='Läuft gerade: A - B'):
            audio.get_config_value.return_value = False
            await module.on_current_song_changed('A', 'B')
            module._commentary_follower.announce.assert_not_called()
            audio.get_config_value.return_value = True
            module.get_config_value.return_value = False
            await module.on_current_song_changed('A', 'B')
            module._commentary_follower.announce.assert_not_called()
            module.get_config_value.return_value = True
            await module.on_current_song_changed('A', 'B')
            module._commentary_follower.announce.assert_called_once_with('Läuft gerade: A - B')
