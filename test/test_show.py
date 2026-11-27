from unittest.mock import AsyncMock, MagicMock, patch

from gdotest.TestUtil import GDOTestCase
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.show import show
from gdo.video.LiveIndicator import LiveIndicator


class ShowTest(GDOTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.mode(Mode.render_cli)

    async def test_show_saves_configuration_and_queues_mode(self):
        method = show()
        host = MagicMock()
        host.get_id.return_value = '42'
        host.get_name.return_value = 'Giz'
        method.param_val = MagicMock(side_effect={'speech': 'ar', 'ticker': 'en', 'title': 'Contest'}.get)
        method.param_value = MagicMock(side_effect={'host': host, 'channel': False}.get)
        method.reply = MagicMock(return_value='ok')
        audio, mira, channel = MagicMock(), MagicMock(), MagicMock()
        audio.save_config_val = AsyncMock()
        mira.save_config_val = AsyncMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch('gdo.video.method.show.module_audio.instance', return_value=audio), \
             patch('gdo.video.method.show.module_mira.instance', return_value=mira), \
             patch('gdo.video.method.show.GDO_Channel.with_setting', return_value=[channel]), \
             patch('gdo.video.method.show.Application.db', return_value=db), \
             patch('gdo.video.method.show.IPC.send_to_dog') as send:
            self.assertEqual('ok', await method.gdo_execute())
        audio.save_config_val.assert_awaited_once_with('audio_microphone_language', 'ar')
        channel.save_val.assert_called_once_with('chan_language', 'ar')
        self.assertEqual([('mira_ticker_baselang', 'en'), ('mira_show_host', '42'),
                          ('mira_show_title', 'Contest')],
                         [call.args for call in mira.save_config_val.await_args_list])
        send.assert_called_once_with('video.ipc_liveshow', ['show'])

    async def test_channel_option_requires_a_channel(self):
        method = show()
        method.param_val = MagicMock(return_value='ar')
        method.param_value = MagicMock(side_effect={'host': MagicMock(), 'channel': True}.get)
        method.err = MagicMock(return_value='missing channel')
        self.assertEqual('missing channel', await method.gdo_execute())

    async def test_channel_option_marks_current_channel(self):
        method = show()
        current = MagicMock()
        method._env_channel = current
        host = MagicMock()
        method.param_val = MagicMock(side_effect={'speech': 'ar', 'ticker': 'en', 'title': None}.get)
        method.param_value = MagicMock(side_effect={'host': host, 'channel': True}.get)
        method.reply = MagicMock()
        audio, mira, toggle, db = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        toggle.env_channel.return_value = toggle
        audio.save_config_val = AsyncMock()
        mira.save_config_val = AsyncMock()
        db.is_in_transaction.return_value = True
        with patch('gdo.video.method.show.enabled', return_value=toggle), \
             patch('gdo.video.method.show.module_audio.instance', return_value=audio), \
             patch('gdo.video.method.show.module_mira.instance', return_value=mira), \
             patch('gdo.video.method.show.GDO_Channel.with_setting', return_value=[current]), \
             patch('gdo.video.method.show.Application.db', return_value=db), \
             patch('gdo.video.method.show.Application.defer_after_commit') as defer:
            await method.gdo_execute()
        toggle.env_channel.assert_called_once_with(current)
        toggle.save_config_channel.assert_called_once_with('live_channel', '1')
        current.save_val.assert_called_once_with('chan_language', 'ar')
        defer.assert_called_once()

    def test_title_is_drawn_only_in_show_mode(self):
        from PIL import Image
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('off', 0)):
            show_frame = Image.new('RGB', (640, 360), 'grey')
            work_frame = show_frame.copy()
            LiveIndicator('show', label='Giz', title='Contest').draw(show_frame)
            LiveIndicator('work', label='Giz', title='Contest').draw(work_frame)
        self.assertNotEqual(show_frame.crop((200, 0, 440, 35)).tobytes(),
                            work_frame.crop((200, 0, 440, 35)).tobytes())
