import msgspec.json

from gdo.audio.language import VOICES, speech_language
from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text


class shrug(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.shrug'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text').tooltip('tt_video_duckshrug_text'),
                GDT_Enum('lang').choices({'en': 'English', 'de': 'Deutsch'}).tooltip('tt_audio_say_language')]

    def gdo_execute(self):
        try:
            text = self.param_val('text')
            if text:
                language = speech_language(self, self.param_val('lang'))
                if language not in VOICES or len(text) > 300:
                    raise ValueError('Choose en/de and speech text of at most 300 characters')
                payload = [encode_text(text), language]
                if len(msgspec.json.encode(payload)) > IPC.MAX_EVENT_ARG_SIZE:
                    raise ValueError('Speech request exceeds IPC size limit')
                args = ('video.ipc_duckshrug', payload)
            else:
                args = ('video.ipc_duckevent', ['shrug'])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
            return self.reply('video_duckevent_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
