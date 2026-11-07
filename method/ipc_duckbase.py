from gdo.base.Application import Application
from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.mira.GDT_MiraMood import GDT_MiraMood
from gdo.mira.module_mira import module_mira
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_duckbase(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_MiraMood('key').not_null().positional(),
                GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_String('lang').ascii().maxlen(2).not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            PlaybackTasks.start(self.play())
        return self.empty()

    async def play(self):
        if Application.IS_DOG:
            try:
                video = module_video.instance()
                active = getattr(video, '_duck_event_task', None)
                if active and not active.done():
                    video.finish_duck_event(active)
                key = self.param_val('key')
                await module_mira.instance().save_config_val('mira_mood', key, force=True)
                video.connector.duck_animation(key)
                payload = self.param_val('payload')
                if payload != '-':
                    from gdo.audio.method.ipc_say import ipc_say
                    await ipc_say().input('text', decode_text(payload)).input('lang', self.param_val('lang')).play()
            except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck base animation failed: {error}')
        return self.empty()
