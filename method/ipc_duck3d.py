from gdo.base.Application import Application
from gdo.base.Logger import Logger
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
                module_video.instance().connector.duck3d(self.param_value('enabled'))
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'3D duck failed: {error}')
        return self.empty()
