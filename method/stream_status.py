"""Public, non-authenticating status for the stream navigation link."""
import time

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.message.GDT_HTML import GDT_HTML
from gdo.video.DirectStream import active_asset


class stream_status(Method):
    def gdo_connectors(self):
        return 'web'

    def gdo_execute(self):
        Application.header('Cache-Control', 'no-store')
        path = active_asset(Application.files_path('secret_video_stream'), 'index.m3u8')
        try:
            live = path is not None and time.time() - path.stat().st_mtime < 15
        except OSError:
            live = False
        if not live:
            Application.status('404 Not Found')
        return GDT_HTML().text('live' if live else 'offline')
