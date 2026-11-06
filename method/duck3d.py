from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool


class duck3d(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional().tooltip('tt_video_duck3d_enabled')]

    def gdo_execute(self):
        args = ('video.ipc_duck3d', ['1' if self.param_value('enabled') else '0'])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('video_duck3d_queued')
