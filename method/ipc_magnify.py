from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Float import GDT_Float
from gdo.core.GDT_UInt import GDT_UInt
from gdo.video.module_video import module_video


class ipc_magnify(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional(),
                GDT_Float('zoom').not_null().min(1.1).max(8).positional(),
                GDT_UInt('radius').not_null().min(16).max(240).positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.magnify(self.param_value('enabled'),
                                                          self.param_value('zoom'), self.param_value('radius'))
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video magnify IPC failed: {exc}')
        return self.empty()
