from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.method.ipc_duckevent import ipc_duckevent
from gdo.video.module_video import module_video


class ipc_duckanim_speech(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        keys = ('idle', 'quacking', 'sad', 'high', 'music', 'tipsy', 'drunk', 'embarrassed', 'angry', 'lol', 'shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz')
        return [GDT_Enum('key').choices({key: key.title() for key in keys}).not_null().positional(),
                GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_Enum('lang').choices({'en': 'English', 'de': 'Deutsch', 'ko': 'Korean', 'vi': 'Vietnamese', 'ja': 'Japanese'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                key = self.param_val('key')
                text = decode_text(self.param_val('payload'))
                if len(text) > 300:
                    raise ValueError('Speech text is limited to 300 characters')
                if key in ('shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz'):
                    await ipc_duckevent().input('key', key).gdo_execute()
                else:
                    module_video.instance().connector.duck_animation(key)
                from gdo.audio.method.ipc_say import ipc_say
                await ipc_say().input('text', text).input('lang', self.param_val('lang')).gdo_execute()
            except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck animation speech failed: {error}')
        return self.empty()
