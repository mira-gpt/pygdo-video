from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.video.module_video import module_video


class ipc_stream_presence(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('viewer').not_null().maxlen(32).positional(),
                GDT_Enum('action').choices({'join': 'join', 'heartbeat': 'heartbeat', 'quit': 'quit'}).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            module = module_video.instance()
            if module.direct_stream.active():
                await module.stream_presence.update(self.param_val('viewer'), self.param_val('action'))
        return self.empty()
