from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.date.GDT_Duration import GDT_Duration


class zap(Method):
    def gdo_parameters(self):
        return [GDT_Duration('duration').initial('666ms').min(.05).max(30).positional().tooltip('tt_video_zap_duration')]

    def gdo_user_permission(self):
        return 'owner'

    def gdo_execute(self):
        duration = self.param_value('duration')
        args = [str(.666 if duration is None else duration)]
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, 'video.ipc_zap', args)
        else:
            IPC.send_to_dog('video.ipc_zap', args)
        return self.empty() if Application.IS_DOG else self.reply('video_zap_queued')
