from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.date.GDT_Duration import GDT_Duration
from gdo.video.AsciiArt import AsciiArt
from gdo.video.module_video import module_video


class ipc_asciiart(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Duration('duration').not_null().min(0.1).max(300).positional()]

    def gdo_execute(self):
        if not Application.IS_DOG:
            return self.empty()
        try:
            module_video.instance().connector.put_effect('asciiart', AsciiArt(self.param_value('duration')))
        except (ValueError, RuntimeError, OSError, AttributeError) as exc:
            Logger.warning(f'Video ASCII art IPC failed: {exc}')
        return self.empty()
