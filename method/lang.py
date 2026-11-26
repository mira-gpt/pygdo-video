from gdo.audio.method.language import language
from gdo.audio.language import LANGUAGES
from gdo.audio.module_audio import module_audio
from gdo.core.GDO_Channel import GDO_Channel
from gdo.core.GDT_Enum import GDT_Enum
from gdo.mira.method.enabled import enabled


class lang(language):
    """Video shortcut for the shared microphone-language setting."""

    def gdo_parameters(self):
        return [GDT_Enum('language').choices(LANGUAGES).not_null().positional().tooltip('tt_audio_language')]

    async def gdo_execute(self):
        language = self.param_val('language')
        channels = list(GDO_Channel.with_setting(enabled(), 'live_channel', '1', '0'))
        await module_audio.instance().save_config_val('audio_microphone_language', language)
        for channel in channels:
            channel.save_val('chan_language', language)
        return self.reply('video_language_set', (len(channels), language))

