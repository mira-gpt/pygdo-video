from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Bool import GDT_Bool


class ipc_liveshow(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                mira = ModuleLoader.instance().get_module('mira')
                if not mira:
                    raise ValueError('Mira module is required for liveshow mode')
                await mira.save_config_val('mira_quacking', '1' if self.param_value('enabled') else '0', force=True)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Live show mode failed: {error}')
        return self.empty()
