from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.EffectKey import effect_key
from gdo.video.module_video import module_video


class ipc_close(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('key').not_null().maxlen(32).positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.close_effects(effect_key(self.param_val('key')))
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video close IPC failed: {exc}')
        return self.empty()
