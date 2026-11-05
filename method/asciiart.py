from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.date.GDT_Duration import GDT_Duration


class asciiart(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Duration('duration').not_null().initial('5s').min(0.1).max(300)
                .positional().tooltip('tt_video_asciiart_duration')]

    def gdo_execute(self):
        duration = self.param_value('duration')
        args = ('video.ipc_asciiart', [f'{duration}s'])
        try:
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_asciiart_queued')
