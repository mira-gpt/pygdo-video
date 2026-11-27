from gdo.audio.module_audio import module_audio
from gdo.base.Method import Method
from gdo.core.GDT_Percent import GDT_Percent


class duckvol(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.vol'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Percent('volume').min(0).max(100).not_null().positional()]

    async def gdo_execute(self):
        volume = self.param_val('volume')
        await module_audio.instance().save_config_val('audio_speech_volume', volume)
        return self.reply('video_duck_volume_set', (volume,))
