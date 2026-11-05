from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text


class draw(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('prompt').not_null().tooltip('tt_video_draw_prompt')]

    def gdo_execute(self):
        try:
            args = ('video.ipc_draw', [encode_text(self.param_value('prompt'))])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_draw_queued')
