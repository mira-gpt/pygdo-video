from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text


class ducktext(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text').not_null().tooltip('tt_video_ducktext_text')]

    def gdo_execute(self):
        try:
            text = self.param_value('text')
            if len(text) > 250:
                raise ValueError('Duck captions are limited to 250 characters')
            args = ('video.ipc_ducktext', [encode_text(text)])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
            return self.empty() if Application.IS_DOG else self.reply('video_ducktext_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
