from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_ducktext(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                text = decode_text(self.param_val('payload'))
                if len(text) > 250:
                    raise ValueError('Duck caption too long')
                module_video.instance().connector.duck_caption(text)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Video duck caption failed: {error}')
        return self.empty()
