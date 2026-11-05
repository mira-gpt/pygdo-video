from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Float import GDT_Float
from gdo.core.GDT_String import GDT_String
from gdo.video.module_video import module_video


class ipc_stroke(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [*[GDT_Float(name).not_null().min(0).max(100).positional() for name in ('x1', 'y1', 'x2', 'y2')],
                GDT_String('color').not_null().maxlen(7).positional(),
                GDT_Float('width').not_null().min(.1).max(10).positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.draw_line(
                    *(self.param_value(name) for name in ('x1', 'y1', 'x2', 'y2')),
                    self.param_val('color'), self.param_value('width'))
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video stroke IPC failed: {exc}')
        return self.empty()
