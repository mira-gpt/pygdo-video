import json

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.VideoTimer import parse_target
from gdo.video.module_video import module_video


class ipc_timer(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            target, event = json.loads(decode_text(self.param_val('payload')))
            module_video.instance().video_timer.set(parse_target(target), event)
        return self.empty()
