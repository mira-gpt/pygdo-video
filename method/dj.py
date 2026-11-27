"""Admin control panel for the shared live show configuration."""
from html import escape
import subprocess

from gdo.audio.session import audio_session_command
from gdo.base.ModuleLoader import ModuleLoader
from gdo.base.util.href import href
from gdo.form.MethodForm import MethodForm
from gdo.message.GDT_HTML import GDT_HTML
from gdo.core.GDT_Container import GDT_Container


SHOW_SETTINGS = {
    'video': ('video_mode', 'video_monitor', 'video_desktop_url',
              'video_duck_overlay', 'video_duck3d_overlay', 'video_mic_overlay',
              'video_thoughts_overlay', 'video_thoughts_audio', 'video_thoughts_translate', 'video_stream_sidebar',
              'video_timer_frequency'),
    'audio': ('audio_output_device', 'audio_output_session_user',
              'audio_microphone_session_user', 'audio_microphone',
              'audio_microphone_language', 'audio_speech_volume', 'audio_announce_songs'),
    'mira': ('mira_livemode', 'mira_show_host', 'mira_current_song_enabled'),
}


class dj(MethodForm):
    def gdo_connectors(self):
        return 'web'

    def gdo_user_permission(self):
        return 'admin'

    def configured_modules(self):
        loader = ModuleLoader.instance()
        return [(loader.get_module(name), keys) for name, keys in SHOW_SETTINGS.items()]

    def gdo_create_form(self, form):
        form.text_raw('Live-show configuration. Audio session users select where defaults are read; they are not the current sink or microphone names.')
        for module, keys in self.configured_modules():
            if module and module.is_enabled():
                fields = module.module_config()
                form.add_fields(*(fields[key] for key in keys if key in fields))
        super().gdo_create_form(form)

    async def form_submitted(self):
        for module, keys in self.configured_modules():
            if module and module.is_enabled():
                fields = module.module_config()
                for key in keys:
                    if key in fields:
                        field = fields[key]
                        if field.get_prev() != field.get_val():
                            await module.save_config_val(key, field.get_val(), True)
        return self.redirect(href('video', 'dj'), 'msg_form_submitted')

    @staticmethod
    def audio_defaults(audio):
        values = []
        for label, kind, key in (('Output sink', 'sink', 'audio_output_session_user'),
                                 ('Microphone source', 'source', 'audio_microphone_session_user')):
            try:
                command = audio_session_command(['pactl', f'get-default-{kind}'], audio.get_config_val(key) or None)
                value = subprocess.run(command, check=True, capture_output=True, text=True, timeout=2).stdout.strip()
            except (OSError, ValueError, subprocess.SubprocessError):
                value = 'Unavailable from web process'
            values.append(f'<li>{label}: {escape(value or "Unavailable")}</li>')
        return '<p>Current audio session defaults (may differ from already running capture processes):</p><ul>' + ''.join(values) + '</ul>'

    def render_page(self):
        audio = ModuleLoader.instance().get_module('audio')
        defaults = self.audio_defaults(audio) if audio and audio.is_enabled() else ''
        return GDT_Container().vertical().add_fields(
            GDT_HTML().html(f'<p><a href="{escape(href("video", "stream"), quote=True)}">Open live stream</a></p>{defaults}'),
            self.get_form())
