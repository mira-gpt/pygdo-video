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
                key = effect_key(self.param_val('key'))
                if key in ('away', 'all'):
                    from gdo.base.ModuleLoader import ModuleLoader
                    mira = ModuleLoader.instance().get_module('mira')
                    task = getattr(mira, '_away_task', None) if mira else None
                    if task:
                        task.cancel()
                        mira._away_task = None
                module_video.instance().connector.close_effects(key)
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video close IPC failed: {exc}')
        return self.empty()
