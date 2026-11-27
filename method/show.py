from gdo.audio.language import LANGUAGES
from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDO_Channel import GDO_Channel
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_User import GDT_User
from gdo.mira.method.enabled import enabled
from gdo.mira.module_mira import module_mira


class show(Method):
    @classmethod
    def gdo_trigger(cls):
        return 'live.show'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [
            GDT_Enum('speech').choices(LANGUAGES).not_null().positional(),
            GDT_String('ticker').ascii().minlen(2).maxlen(3).pattern(r'^[a-z]{2,3}$').not_null().positional(),
            GDT_User('host').not_null().positional(),
            GDT_String('title').maxlen(160).positional(),
            GDT_Bool('channel').initial('0'),
        ]

    async def gdo_execute(self):
        speech = self.param_val('speech')
        ticker = self.param_val('ticker')
        host = self.param_value('host')
        channel = self._env_channel
        if self.param_value('channel') and not channel:
            return self.err('live_show_channel_required')
        if self.param_value('channel'):
            enabled().env_channel(channel).save_config_channel('live_channel', '1')
        channels = list(GDO_Channel.with_setting(enabled(), 'live_channel', '1', '0'))
        await module_audio.instance().save_config_val('audio_microphone_language', speech)
        for current in channels:
            current.save_val('chan_language', speech)
        mira = module_mira.instance()
        await mira.save_config_val('mira_ticker_baselang', ticker)
        await mira.save_config_val('mira_show_host', host.get_id())
        await mira.save_config_val('mira_show_title', self.param_val('title'))
        args = ('video.ipc_liveshow', ['show'])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('live_show_configured', (speech, ticker, host.get_name(), len(channels)))
