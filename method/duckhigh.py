from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.core.GDT_Enum import GDT_Enum
from gdo.language.GDT_Language import GDT_Language
from gdo.audio.language import VOICES, speech_language
from gdo.video.StarWarsIPC import encode_text
import msgspec.json


class duckhigh(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.high'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text'), GDT_Language('lang').audiolangs()]

    def gdo_execute(self):
        text = self.param_val('text')
        if text:
            language = speech_language(self, self.param_val('lang'))
            if language not in VOICES or len(text) > 300:
                return self.err('video_error', ('Choose en, de, ko, vi, ja, sq or ru and speech text of at most 300 characters',))
            payload = [encode_text(text), language]
            if len(msgspec.json.encode(payload)) > IPC.MAX_EVENT_ARG_SIZE:
                return self.err('video_error', ('Speech request exceeds IPC size limit',))
            args = ('video.ipc_duckhigh', payload)
        else:
            args = ('mira.ipc_mood', ['high'])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.reply('video_duckanim_queued')
