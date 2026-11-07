from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Float import GDT_Float
from gdo.video.module_video import module_video


class ipc_off(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Float('duration').not_null().min(0).max(60).positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.crt_off(float(self.param_value('duration')))
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'CRT off effect failed: {error}')
        return self.empty()
