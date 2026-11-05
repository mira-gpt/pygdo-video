from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.video.module_video import module_video


class ipc_preview(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module_video.instance().connector.restart_preview()
            except (RuntimeError, AttributeError, OSError) as error:
                Logger.warning(f'Video preview restart failed: {error}')
        return self.empty()
