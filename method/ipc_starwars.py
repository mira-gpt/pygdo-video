from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_starwars(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional()]

    def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        try:
            text = decode_text(self.param_val('payload'))
            module_video.instance().connector.starwars(text)
        except (ValueError, RuntimeError, OSError) as exc:
            Logger.warning(f'Video starwars IPC failed: {exc}')
        return self.empty()
