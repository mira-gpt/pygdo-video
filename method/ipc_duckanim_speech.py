from gdo.base.Application import Application
from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Enum import GDT_Enum
from gdo.language.GDT_Language import GDT_Language
from gdo.core.GDT_String import GDT_String
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class ipc_duckanim_speech(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        keys = ('idle', 'quacking', 'sad', 'high', 'music', 'tipsy', 'drunk', 'embarrassed', 'angry', 'inlove', 'trip', 'tired', 'lol', 'shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz', 'teacher', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news')
        return [GDT_Enum('key').choices({key: key.title() for key in keys}).not_null().positional(),
                GDT_String('payload').ascii().maxlen(1024).not_null().positional(),
                GDT_Language('lang').audiolangs().not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            PlaybackTasks.start(self.play())
        return self.empty()

    async def play(self):
        if Application.IS_DOG:
            event_task = None
            try:
                key = self.param_val('key')
                text = decode_text(self.param_val('payload'))
                if len(text) > 300:
                    raise ValueError('Speech text is limited to 300 characters')
                if key in ('lol', 'shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz', 'teacher', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news'):
                    if key in ('cry', 'lol'):
                        mira = ModuleLoader.instance().get_module('mira')
                        if mira and key == 'cry':
                            await mira.save_config_val('mira_mood', 'sad')
                        elif mira and mira.cfg_mira_mood() == 'sad':
                            await mira.save_config_val('mira_mood', 'idle')
                    event_task = module_video.instance().duck_event(key, duration=None)
                else:
                    module_video.instance().connector.duck_animation(key)
                from gdo.audio.method.ipc_say import ipc_say
                await ipc_say().input('text', text).input('lang', self.param_val('lang')).play()
            except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Duck animation speech failed: {error}')
            finally:
                if event_task is not None:
                    try:
                        module_video.instance().finish_duck_event(event_task)
                    except (ValueError, RuntimeError, OSError, AttributeError) as error:
                        Logger.warning(f'Duck animation restore failed: {error}')
        return self.empty()
