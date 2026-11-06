from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum


class duckanim(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.anim'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({'idle': 'Idle', 'quacking': 'Quacking', 'sad': 'Sad', 'lol': 'LOL', 'LOL': 'LOL'}).not_null().positional().tooltip('tt_video_duckanim_key')]

    def gdo_execute(self):
        args = ('video.ipc_duckanim', [self.param_val('key').lower()])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('video_duckanim_queued')
