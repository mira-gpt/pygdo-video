from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.video.module_video import module_video


class ipc_duckanim(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({'idle': 'Idle', 'quacking': 'Quacking', 'sad': 'Sad', 'lol': 'LOL'}).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.duck_animation(self.param_val('key'))
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'3D duck animation failed: {error}')
        return self.empty()
