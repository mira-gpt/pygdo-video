from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String
from gdo.video.EffectKey import effect_key


class close(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('key').maxlen(32).positional().tooltip('tt_video_close_key'),
                GDT_Bool('all').not_null().initial('0').tooltip('tt_video_close_all')]

    def gdo_execute(self):
        try:
            key = self.param_val('key')
            all_effects = self.param_value('all')
            if bool(key) == bool(all_effects):
                raise ValueError('Specify one effect key or --all')
            key = 'all' if all_effects else effect_key(key)
            args = ('video.ipc_close', [key])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.empty() if Application.IS_DOG else self.reply('video_close_queued')
