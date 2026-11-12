from html import escape
import json
import secrets

from gdo.base.Method import Method
from gdo.base.util.href import href
from gdo.message.GDT_HTML import GDT_HTML
from gdo.video.StreamAuth import require_stream_access
from gdo.video.module_video import module_video


class stream(Method):
    def gdo_connectors(self):
        return 'web'

    def gdo_execute(self):
        if not require_stream_access():
            return GDT_HTML().text('Stream access requires HTTPS and the configured password.')
        playlist = escape(href('video', 'stream_asset', '_asset=index.m3u8'), quote=True)
        playlist_js = json.dumps(href('video', 'stream_asset', '_asset=index.m3u8'))
        presence = json.dumps(href('video', 'stream_presence'))
        viewer = json.dumps(secrets.token_hex(16))
        player_js = escape(module_video.instance().www_path('node_modules/hls.js/dist/hls.min.js'), quote=True)
        return GDT_HTML().html(
            '<h1>Live stream</h1><video id="gdo-live-stream" controls autoplay playsinline '
            'style="max-width:100%"></video>'
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
