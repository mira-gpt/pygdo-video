from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.video.module_video import module_video
from gdo.audio.PlaybackTasks import PlaybackTasks


class ipc_duckwelcome(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('nickname').maxlen(60).not_null().positional(),
                GDT_Enum('lang').choices({'de': 'Deutsch', 'en': 'English'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            PlaybackTasks.start(module_video.instance().play_welcome(self.param_val('nickname'), self.param_val('lang')))
        return self.empty()
