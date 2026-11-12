from gdo.base.Application import Application
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.message.GDT_HTML import GDT_HTML
from gdo.video.DirectStream import active_asset
from gdo.video.StreamAuth import require_stream_access


class stream_presence(Method):
    def gdo_connectors(self):
        return 'web'

    def gdo_parameters(self):
        return [GDT_String('viewer').not_null().maxlen(32).pattern(r'^[0-9a-f]{32}$'),
                GDT_Enum('action').choices({'join': 'join', 'heartbeat': 'heartbeat', 'quit': 'quit'}).not_null()]

    def gdo_execute(self):
        if not require_stream_access():
            return GDT_HTML().text('Stream access denied.')
        if Application.get_request_method() != 'POST':
            Application.status('405 Method Not Allowed')
            return GDT_HTML().text('POST required.')
        if not active_asset(Application.files_path('secret_video_stream'), 'index.m3u8'):
            Application.status('404 Not Found')
            return GDT_HTML().text('Stream is not available.')
        IPC.send('video.ipc_stream_presence', [self.param_val('viewer'), self.param_val('action')])
        return GDT_HTML().text('OK')
