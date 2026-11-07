import json

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_Bool import GDT_Bool
from gdo.language.GDT_Language import GDT_Language
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.StarWarsIPC import encode_text
from gdo.video.DuckAnimations import BASE_DEFAULTS


def queue_and_notify(animation_request, args, key, requester, text):
    IPC.send_to_dog(animation_request, args)
    try:
        from gdo.mira.util import send_to_mira
        message = f'$duck.anim {key} (requested by {json.dumps(requester, ensure_ascii=True)}; animation request queued for Dog)'
        if text:
            message += f'\nSpeech text: {json.dumps(text, ensure_ascii=True)}'
        send_to_mira(message, interrupt=False)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        Logger.warning(f'Duck animation notification failed: {error}')


class duckanim(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.anim'

    def gdo_user_permission(self):
        return 'admin'

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({key: key.title() for key in BASE_DEFAULTS}).errorhint_all().not_null().positional().tooltip('tt_video_duckanim_key'),
                GDT_RestOfText('text').tooltip('tt_video_rolleye_text'),
                GDT_Language('lang').audiolangs().tooltip('tt_audio_say_language'),
                GDT_Bool('base')]

    def gdo_execute(self):
        try:
            key = self.param_val('key').lower()
            text = self.param_val('text')
            base = self.param_value('base')
            base = BASE_DEFAULTS[key] if base is None else base
            if text:
                language = speech_language(self, self.param_val('lang'))
                if language not in VOICES or len(text) > 300:
                    raise ValueError('Choose en, de, ko, vi, ja, sq or ru and speech text of at most 300 characters')
                payload = [key, encode_text(text), language]
                if len(msgspec.json.encode(payload)) > IPC.MAX_EVENT_ARG_SIZE:
                    raise ValueError('Speech request exceeds IPC size limit')
                args = ('video.ipc_duckbase', payload) if base else ('video.ipc_duckanim_speech', payload)
            else:
                args = ('video.ipc_duckbase', [key, '-', '-']) if base else ('video.ipc_duckevent', [key])
            user = getattr(self, '_env_user', None) or Application.get_current_user()
            requester = user.get_name_sid() if user else 'unknown'
            if Application.db().is_in_transaction():
                Application.defer_after_commit(queue_and_notify, *args, key, requester, text)
            else:
                queue_and_notify(*args, key, requester, text)
            return self.empty() if Application.IS_DOG else self.reply('video_duckanim_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
import msgspec.json

from gdo.audio.language import VOICES, speech_language
