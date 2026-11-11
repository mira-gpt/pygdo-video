import json

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import encode_text
from gdo.video.VideoTimer import parse_target


class timer(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('date').maxlen(40).not_null().positional(),
                GDT_RestOfText('event').minlen(1).maxlen(200).not_null().positional()]

    def gdo_execute(self):
        try:
            target = parse_target(self.param_val('date'))
            event = self.param_val('event').strip()
            if not event or any(c in event for c in '\r\n\x00'):
                raise ValueError('Event must be a single line')
            payload = encode_text(json.dumps([target.isoformat(), event], ensure_ascii=False))
            args = ('video.ipc_timer', [payload])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
            return self.reply('video_timer_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
