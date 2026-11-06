from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.ModuleLoader import ModuleLoader
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.module_video import module_video


class ipc_duck3d(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                connector = module_video.instance().connector
                enabled = self.param_value('enabled')
                connector.duck3d(enabled)
                mira = ModuleLoader.instance().get_module('mira') if enabled else None
                if mira:
                    connector.duck_animation(mira.cfg_mira_mood())
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'3D duck failed: {error}')
        return self.empty()
