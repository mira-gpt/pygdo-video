from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.Render import Mode
from gdo.core.GDT_Enum import GDT_Enum


class ipc_record(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Enum('action').choices({'start': 'start', 'stop': 'stop', 'status': 'status'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            from gdo.video.method.record import is_running_dog_process
            if not is_running_dog_process():
                Logger.warning('Video recording IPC ignored outside the running Dog process.')
                return self.empty()
            action = self.param_val('action')
            arguments = {'start': ['--enabled=1'], 'stop': ['--enabled=0'], 'status': []}[action]
            result = await IPC.execute_dog_event('video.record', arguments)
            if result:
                Logger.message('Video recording IPC: ' + result.render(Mode.render_txt))
        return self.empty()
