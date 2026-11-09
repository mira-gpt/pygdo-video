from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_Bool import GDT_Bool
from gdo.language.GDT_Language import GDT_Language
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.message.GDT_Bold import GDT_Bold
from gdo.message.GDT_Glyph import GDT_Glyph
from gdo.message.GDT_Span import GDT_Span
from gdo.mira.module_mira import module_mira
from gdo.mira.GDT_MiraMood import ANIMATIONS
from gdo.video.StarWarsIPC import encode_text
from gdo.video.DuckAnimations import BASE_DEFAULTS
from gdo.video.module_video import module_video


class duckanim(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.anim'

    def gdo_user_permission(self):
        return 'admin'

    def gdo_parameters(self):
        return [GDT_Enum('key').choices({key: key.title() for key in sorted(BASE_DEFAULTS)}).errorhint_all().positional().tooltip('tt_video_duckanim_key'),
                GDT_RestOfText('text').tooltip('tt_video_rolleye_text'),
                GDT_Language('lang').audiolangs().tooltip('tt_audio_say_language'),
                GDT_Bool('base')]

    def gdo_execute(self):
        try:
            raw_key = self.param_val('key')
            if not raw_key:
                current = module_mira.instance().cfg_mira_mood()
                if Application.IS_DOG:
                    source = getattr(module_video.instance().connector, 'duck_source', None)
                    current = getattr(source, 'mode', None) or current
                output = GDT_Span().add_field(GDT_Glyph('Duck animations: '))
                for index, name in enumerate(sorted(BASE_DEFAULTS)):
                    if index:
                        output.add_field(GDT_Glyph(', '))
                    item = GDT_Glyph(name)
                    output.add_field(GDT_Bold().add_field(item) if name == current else item)
                return output
            key = raw_key.lower()
            text = self.param_val('text') or ANIMATIONS[key]['speech']
            base = self.param_value('base')
            base = BASE_DEFAULTS[key] if base is None else base
            jingle = ANIMATIONS[key]['jingle']
            if jingle:
                from gdo.audio.jingles import jingle_path
                jingle_path(jingle)
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
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
            if jingle:
                if Application.db().is_in_transaction():
                    Application.defer_after_commit(IPC.send_to_dog, 'audio.ipc_jingle', [jingle])
                else:
                    IPC.send_to_dog('audio.ipc_jingle', [jingle])
            return self.empty() if Application.IS_DOG else self.reply('video_duckanim_queued')
        except (ValueError, RuntimeError, OSError) as error:
            return self.err('video_error', (str(error),))
import msgspec.json

from gdo.audio.language import VOICES, speech_language
