from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_String import GDT_String
from gdo.mira.GDT_MiraLiveMode import GDT_MiraLiveMode


class liveshow(Method):
    @classmethod
    def gdo_trig(cls):
        return 'live'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('mode').positional().tooltip('tt_video_liveshow_enabled')]

    def gdo_execute(self):
        mode = self.param_val('mode')
        if mode is None:
            mira = ModuleLoader.instance().get_module('mira')
            if not mira:
                return self.err('video_error', ('Mira module is required for live-show status',))
            return self.reply('video_liveshow_status', (mira.cfg_mira_livemode(),))
        mode = {'1': 'show', '0': 'off'}.get(mode.lower(), mode.lower())
        if mode not in GDT_MiraLiveMode.MODES:
            return self.err('video_liveshow_invalid')
        args = ('video.ipc_liveshow', [mode])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('video_liveshow_queued')
