from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_ducklol(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_Enum('lang').choices({'en': 'English', 'de': 'Deutsch'}).not_null().positional()]

    async def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        switched = False
        connector = None
        try:
            text = decode_text(self.param_val('payload'))
            if len(text) > 300:
                raise ValueError('Speech text is limited to 300 characters')
            language = self.param_val('lang')
            from gdo.audio.method.ipc_say import ipc_say
            connector = module_video.instance().connector
            connector.duck_animation('lol')
            switched = True
            speech = ipc_say().input('text', text).input('lang', language)
            await speech.gdo_execute()
        except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Duck LOL speech failed: {error}')
        finally:
            if switched:
                try:
                    connector.duck_animation('idle')
                except (ValueError, RuntimeError, OSError, AttributeError) as error:
                    Logger.warning(f'Duck idle restore failed: {error}')
        return self.empty()
