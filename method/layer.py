from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String
from gdo.video.module_video import module_video


class layer(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('name').not_null().positional(),
                GDT_Bool('enabled').not_null().positional()]

    def gdo_execute(self):
        name, enabled = self.param_val('name'), self.param_value('enabled')
        try:
            module_video.instance().connector.set_layer(name, enabled)
        except (ValueError, RuntimeError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_layer_changed', (name, 'on' if enabled else 'off'))
