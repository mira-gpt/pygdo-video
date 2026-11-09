"""Queue a message on the common microphone ticker."""
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text


def queue_ticker(text):
    if not isinstance(text, str) or not text.strip() or len(text) > 300 or any(c in text for c in '\r\n\x00'):
        raise ValueError('Ticker text must be a single line of at most 300 characters')
    args = ('video.ipc_mic_ticker', [encode_text(text)])
    if Application.db().is_in_transaction():
        Application.defer_after_commit(IPC.send_to_dog, *args)
    else:
        IPC.send_to_dog(*args)


class mic_ticker(Method):
    @classmethod
    def gdo_trig(cls):
        return 'mic.ticker'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text').minlen(1).maxlen(300).not_null().positional()]

    def gdo_execute(self):
        try:
            queue_ticker(self.param_val('text'))
            return self.reply('video_mic_ticker_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
