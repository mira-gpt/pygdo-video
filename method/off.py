from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.date.GDT_Duration import GDT_Duration


class off(Method):
    def gdo_parameters(self):
        return [GDT_Duration('duration').initial('2s').min(0).max(60).positional().tooltip('tt_video_off_duration')]

    def gdo_user_permission(self):
        return 'owner'

    def gdo_execute(self):
        duration = self.param_value('duration')
        args = [str(2.0 if duration is None else duration)]
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, 'video.ipc_off', args)
        else:
            IPC.send_to_dog('video.ipc_off', args)
        return self.reply('video_off_queued')
