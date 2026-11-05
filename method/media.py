import msgspec.json

from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_CSSLength import GDT_CSSLength


class media(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_String('url').not_null().maxlen(768).positional().tooltip('tt_video_media_url'),
                GDT_CSSLength('width').not_null().initial('25%').tooltip('tt_video_image_width'),
                GDT_CSSLength('height').not_null().initial('25%').tooltip('tt_video_image_height'),
                GDT_CSSLength('x').not_null().initial('2%').tooltip('tt_video_image_x'),
                GDT_CSSLength('y').not_null().initial('2%').tooltip('tt_video_image_y')]

    def gdo_execute(self):
        values = [self.param_val(key) for key in ('url', 'width', 'height', 'x', 'y')]
        if len(msgspec.json.encode(values)) > IPC.MAX_EVENT_ARG_SIZE:
            return self.err('video_error', ('Media request exceeds IPC size limit',))
        try:
            args = ('video.ipc_media', values)
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_media_queued')
