from __future__ import annotations

import os

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Width import GDT_Width
from gdo.ui.GDT_Height import GDT_Height
from gdo.video.VideoConnector import VideoConnector
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.core.Connector import Connector
from gdo.core.GDO_Server import GDO_Server
from gdo.video.connector.Video import Video

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_video(GDO_Module):
    connector = VideoConnector()

    def gdo_friendencies(self) -> list:
        return ['audio']

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        if not GDO_Server.get_by_connector('video'):
            GDO_Server.blank({'serv_name': 'Video', 'serv_connector': 'video'}).insert()

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_Enum('video_mode').choices({
                'off': 'off',
                'virtualwebcam': 'virtualwebcam',
                'screensharing': 'screensharing',
            }).not_null().initial('off').tooltip('tt_video_mode'),
            GDT_String('video_desktop_url').maxlen(2048).tooltip('tt_video_desktop_url'),
            GDT_String('video_bg_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_bg_image_url'),
            GDT_String('video_overlay_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_overlay_image_url'),
            GDT_String('video_file_url').maxlen(2048).tooltip('tt_video_file_url'),
            GDT_String('video_webcam_url').maxlen(2048).tooltip('tt_video_webcam_url'),
            GDT_Bool('video_duck_overlay').not_null().initial('0').tooltip('tt_video_duck_overlay'),
            GDT_String('video_duck3d_pythonpath').maxlen(512).tooltip('tt_video_duck3d_pythonpath'),
            GDT_String('video_output_device').not_null().initial('/dev/video2').maxlen(255).tooltip('tt_video_output_device'),
            GDT_Bool('video_output_preview').not_null().initial('0').tooltip('tt_video_output_preview'),
            GDT_Width('video_preview_w').not_null().initial('320').min(1).max(8192).tooltip('tt_video_preview_w'),
            GDT_Height('video_preview_h').not_null().initial('180').min(1).max(8192).tooltip('tt_video_preview_h'),
            GDT_Bool('video_live').not_null().initial('0').tooltip('tt_video_live'),
        ]

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        Connector.register(Video, is_text=False)

    def gdo_subscribe_events(self):
        from gdo.base.Application import Application
        Application.EVENTS.subscribe('audio_speech_start', self.on_speech_start)
        Application.EVENTS.subscribe('audio_speech_end', self.on_speech_end)
        Application.EVENTS.subscribe('audio_speech_envelope', self.on_speech_envelope)

    async def on_speech_envelope(self, speech_id, levels, step_ms):
        try:
            self.connector.speech_envelope(speech_id, levels, step_ms)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass

    async def on_speech_start(self, speech_id, text):
        try:
            self.connector.speech_start(speech_id, text)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass  # Video is optional; speech must continue.

    async def on_speech_end(self, speech_id):
        try:
            self.connector.speech_end(speech_id)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass

    def start_compositor(self):
        mode = self.get_config_value('video_mode')
        if self.connector.is_running():
            raise RuntimeError('Video worker is already running; stop it before switching modes')
        if mode == 'off':
            raise ValueError('Video mode is off')
        if mode == 'screensharing':
            worker = DesktopOverlay(screensharing=True)
            worker.duck3d_pythonpath = self.get_config_val('video_duck3d_pythonpath')
            worker.start(self.get_config_val('video_overlay_image_url'))
            self.connector = worker
            return
        if mode != 'virtualwebcam':
            raise ValueError('Unknown video mode')
        if (self.get_config_val('video_file_url') or self.get_config_val('video_webcam_url')
                or self.get_config_value('video_duck_overlay')):
            raise ValueError('Video file, webcam and duck layers are not implemented yet')
        worker = VideoConnector()
        worker.duck3d_pythonpath = self.get_config_val('video_duck3d_pythonpath')
        worker.start(
            self.get_config_val('video_desktop_url'), self.get_config_val('video_bg_image_url'),
            self.get_config_value('video_output_preview'), self.get_config_value('video_live'),
            self.get_config_val('video_output_device'), self.get_config_value('video_preview_w'),
            self.get_config_value('video_preview_h'))
        self.connector = worker

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-video.js')
        self.add_css('css/pygdo-video.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_video'))
