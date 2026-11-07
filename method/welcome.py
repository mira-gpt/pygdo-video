from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String


class welcome(Method):
    @classmethod
    def gdo_method_config_channel(cls):
        return [GDT_Bool('video_welcome_enabled').not_null().initial('0')]

    @classmethod
    def gdo_trig(cls):
        return 'duck.welcome'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('nickname').maxlen(60).not_null().positional().tooltip('tt_video_welcome_nickname')]

    def gdo_execute(self):
        language = self._env_channel.get_lang_iso() if self._env_channel else self._env_user.get_lang_iso()
        if language not in ('de', 'en'):
            return self.err('video_error', ('No supported welcome voice for this channel language',))
        args = ('video.ipc_duckwelcome', [self.param_val('nickname'), language])
        if Application.db().is_in_transaction():
            Application.defer_after_commit(IPC.send_to_dog, *args)
        else:
            IPC.send_to_dog(*args)
        return self.empty() if Application.IS_DOG else self.reply('video_welcome_queued')
