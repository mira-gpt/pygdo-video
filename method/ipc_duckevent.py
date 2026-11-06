from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.video.module_video import module_video


class ipc_duckevent(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({'idle': 'Idle', 'quacking': 'Quacking', 'lol': 'LOL'}).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().duck_event(self.param_val('key'))
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck event failed: {error}')
        return self.empty()
