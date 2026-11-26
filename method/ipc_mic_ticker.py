from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_UInt import GDT_UInt
from gdo.video.MicTicker import MicTicker
from gdo.video.StarWarsIPC import decode_text


class ipc_mic_ticker(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_UInt('repeats').min(1).max(2).initial('1').positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                MicTicker.enqueue(decode_text(self.param_val('payload')), self.param_value('repeats') or 1)
            except (ValueError, RuntimeError) as error:
                Logger.warning(f'Microphone ticker enqueue failed: {error}')
        return self.empty()
