from html import escape
import json
import secrets

from gdo.base.IPC import IPC
from gdo.base.util.href import href
from gdo.form.GDT_CSRF import GDT_CSRF
from gdo.form.GDT_Submit import GDT_Submit
from gdo.form.MethodForm import MethodForm
from gdo.message.GDT_HTML import GDT_HTML
from gdo.core.GDT_Container import GDT_Container
from gdo.video.StreamAuth import require_stream_access
from gdo.video.module_video import module_video


class stream(MethodForm):
    def gdo_connectors(self):
        return 'web'

    def gdo_needs_authentication(self):
        return False

    def gdo_create_form(self, form):
        if getattr(self, '_env_user', None) and self._env_user.is_admin():
            form.add_field(GDT_CSRF())
            form.actions().add_fields(
                GDT_Submit('enable_stream').text_raw('Enable stream').calling(self.enable_stream),
                GDT_Submit('disable_stream').text_raw('Disable stream').calling(self.disable_stream),
            )

    def enable_stream(self):
        return self.queue_control(True)

    def disable_stream(self):
        return self.queue_control(False)

    def queue_control(self, enabled):
        if not getattr(self, '_env_user', None) or not self._env_user.is_admin():
            return self.err('err_permission', ('admin',))
        IPC.send_to_dog('video.stream_control', ['1' if enabled else '0'])
        return GDT_HTML().text('Stream change requested; check stream status for the result.')

    def gdo_execute(self):
        if not require_stream_access():
            return GDT_HTML().text('Stream access denied. Check your account permissions and stream credentials.')
        return super().gdo_execute()

    def render_page(self):
        playlist = escape(href('video', 'stream_asset', '_asset=index.m3u8'), quote=True)
        playlist_js = json.dumps(href('video', 'stream_asset', '_asset=index.m3u8'))
        presence = json.dumps(href('video', 'stream_presence'))
        viewer = json.dumps(secrets.token_hex(16))
        player_js = escape(module_video.instance().www_path('node_modules/hls.js/dist/hls.min.js'), quote=True)
        player = GDT_HTML().html(
            '<h1>Live stream</h1><video id="gdo-live-stream" controls autoplay playsinline '
            'style="display:block;width:100%;height:auto;max-height:max(1px,calc(100vh - 18rem));object-fit:contain"></video>'
            f'<p><a href="{playlist}">Open the HLS stream</a> in an HLS-capable player such as VLC.</p>'
            f'<script src="{player_js}"></script>'
            '<script>(() => {'
            f'const video=document.getElementById("gdo-live-stream"), url={presence}, viewer={viewer}, playlist={playlist_js};'
            'let joined=false;'
            'function send(action){const body=new URLSearchParams({viewer,action});'
            'fetch(url,{method:"POST",body,credentials:"same-origin",keepalive:true}).catch(()=>{});}'
            'video.addEventListener("playing",()=>{if(!joined){joined=true;send("join");}});'
            'function leave(){if(joined){joined=false;send("quit");}}'
            'video.addEventListener("pause",leave);window.addEventListener("pagehide",leave);'
            'setInterval(()=>{if(joined)send("heartbeat");},5000);'
            'function start(){if(video.canPlayType("application/vnd.apple.mpegurl")){video.src=playlist;}'
            'else if(window.Hls&&Hls.isSupported()){const hls=new Hls();hls.loadSource(playlist);hls.attachMedia(video);}}'
            'if(document.readyState==="complete")start();else window.addEventListener("load",start,{once:true});'
            '})();</script>')
        if getattr(self, '_env_user', None) and self._env_user.is_admin():
            dj_link = GDT_HTML().html(f'<p><a href="{escape(href("video", "dj"), quote=True)}">DJ settings</a></p>')
            return GDT_Container().vertical().add_fields(player, self.get_form(), dj_link)
        return player
