from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text


class ipc_duckhigh(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_Enum('lang').choices({'en': 'English', 'de': 'Deutsch', 'ko': 'Korean', 'vi': 'Vietnamese', 'ja': 'Japanese'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                text = decode_text(self.param_val('payload'))
                if len(text) > 300:
                    raise ValueError('Speech text is limited to 300 characters')
                mira = ModuleLoader.instance().get_module('mira')
                if not mira:
                    raise ValueError('Mira module is required')
                await mira.save_config_val('mira_mood', 'high', force=True)
                from gdo.audio.method.ipc_say import ipc_say
                await ipc_say().input('text', text).input('lang', self.param_val('lang')).gdo_execute()
            except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck high speech failed: {error}')
        return self.empty()
