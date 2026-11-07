from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Float import GDT_Float
from gdo.core.GDT_UInt import GDT_UInt


class magnify(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional().tooltip('tt_video_magnify_enabled'),
                GDT_Float('zoom').not_null().initial('2').min(1.1).max(8).tooltip('tt_video_magnify_zoom'),
                GDT_UInt('radius').not_null().initial('90').min(16).max(240).tooltip('tt_video_magnify_radius')]

    def gdo_execute(self):
        args = ('video.ipc_magnify', ['1' if self.param_value('enabled') else '0',
                                     str(self.param_value('zoom')), str(self.param_value('radius'))])
        try:
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.empty() if Application.IS_DOG else self.reply('video_magnify_queued')
