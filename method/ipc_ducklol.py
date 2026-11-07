from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Enum import GDT_Enum
from gdo.language.GDT_Language import GDT_Language
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_ducklol(Method):
    animation = 'lol'
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_Language('lang').audiolangs().not_null().positional()]

    async def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        event_task = None
        try:
            text = decode_text(self.param_val('payload'))
            if len(text) > 300:
                raise ValueError('Speech text is limited to 300 characters')
            language = self.param_val('lang')
            from gdo.audio.method.ipc_say import ipc_say
            mira = ModuleLoader.instance().get_module('mira')
            if self.animation == 'lol' and mira and mira.cfg_mira_mood() == 'sad':
                await mira.save_config_val('mira_mood', 'idle')
            elif self.animation == 'cry' and mira:
                await mira.save_config_val('mira_mood', 'sad')
            event_task = module_video.instance().duck_event(self.animation, duration=None)
            speech = ipc_say().input('text', text).input('lang', language)
            await speech.gdo_execute()
        except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Duck LOL speech failed: {error}')
        finally:
            if event_task is not None:
                try:
                    module_video.instance().finish_duck_event(event_task)
                except (ValueError, RuntimeError, OSError, AttributeError) as error:
                    Logger.warning(f'Duck idle restore failed: {error}')
        return self.empty()
