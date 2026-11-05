from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Float import GDT_Float
from gdo.core.GDT_String import GDT_String
from gdo.video.DrawingProtocol import validate_line


class stroke(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [*[GDT_Float(name).not_null().min(0).max(100).positional().tooltip('tt_video_stroke_coordinate')
                  for name in ('x1', 'y1', 'x2', 'y2')],
                GDT_String('color').not_null().initial('#ffffff').maxlen(7).tooltip('tt_video_stroke_color'),
                GDT_Float('width').not_null().initial('0.5').min(.1).max(10).tooltip('tt_video_stroke_width')]

    def gdo_execute(self):
        try:
            line = validate_line(*(self.param_value(name) for name in ('x1', 'y1', 'x2', 'y2')),
                                 self.param_val('color'), self.param_value('width'))
            args = ('video.ipc_stroke', [str(value) for value in line])
            if Application.db().is_in_transaction():
                Application.defer_after_commit(IPC.send_to_dog, *args)
            else:
                IPC.send_to_dog(*args)
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_stroke_queued')
