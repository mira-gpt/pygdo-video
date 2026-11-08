from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Bool import GDT_Bool


class liveshow(Method):
    @classmethod
    def gdo_trig(cls):
        return 'live'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Bool('enabled').positional().tooltip('tt_video_liveshow_enabled')]

    def gdo_execute(self):
        enabled = self.param_value('enabled')
        if enabled is None:
            mira = ModuleLoader.instance().get_module('mira')
            if not mira:
                return self.err('video_error', ('Mira module is required for live-show status',))
            return self.reply('video_liveshow_status_on' if mira.get_config_value('mira_quacking') else 'video_liveshow_status_off')
        args = ('video.ipc_liveshow', ['1' if enabled else '0'])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('video_liveshow_queued')
