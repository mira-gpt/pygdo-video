from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Enum import GDT_Enum
from gdo.video.module_video import module_video


class ipc_duckevent(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({'idle': 'Idle', 'quacking': 'Quacking', 'lol': 'LOL', 'shrug': 'Shrug', 'cry': 'Cry'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                key = self.param_val('key')
                mira = ModuleLoader.instance().get_module('mira')
                if key == 'lol' and mira and mira.cfg_mira_mood() == 'sad':
                    await mira.save_config_val('mira_mood', 'idle')
                elif key == 'cry' and mira:
                    await mira.save_config_val('mira_mood', 'sad')
                module_video.instance().duck_event(key)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck event failed: {error}')
        return self.empty()
