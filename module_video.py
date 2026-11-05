from __future__ import annotations

import os

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_Link import GDT_Link
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

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        if not GDO_Server.get_by_connector('video'):
            GDO_Server.blank({'serv_name': 'Video', 'serv_connector': 'video'}).insert()

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_Enum('video_mode').choices({
                'off': 'off',
                'composite': 'composite',
                'desktop_overlays': 'desktop_overlays',
            }).not_null().initial('off').tooltip('tt_video_mode'),
            GDT_String('video_desktop_url').maxlen(2048).tooltip('tt_video_desktop_url'),
            GDT_String('video_bg_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_bg_image_url'),
            GDT_String('video_overlay_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_overlay_image_url'),
            GDT_String('video_file_url').maxlen(2048).tooltip('tt_video_file_url'),
            GDT_String('video_webcam_url').maxlen(2048).tooltip('tt_video_webcam_url'),
            GDT_Bool('video_duck_overlay').not_null().initial('0').tooltip('tt_video_duck_overlay'),
            GDT_String('video_output_device').not_null().initial('/dev/video2').maxlen(255).tooltip('tt_video_output_device'),
            GDT_Bool('video_output_preview').not_null().initial('0').tooltip('tt_video_output_preview'),
            GDT_Bool('video_live').not_null().initial('0').tooltip('tt_video_live'),
        ]

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        Connector.register(Video, is_text=False)

    def start_compositor(self):
        mode = self.get_config_value('video_mode')
        if self.connector.is_running():
            raise RuntimeError('Video worker is already running; stop it before switching modes')
        if mode == 'off':
            raise ValueError('Video mode is off')
        if mode == 'desktop_overlays':
            worker = DesktopOverlay()
            worker.start(self.get_config_val('video_overlay_image_url'))
            self.connector = worker
            return
        if mode != 'composite':
            raise ValueError('Unknown video mode')
        if (self.get_config_val('video_file_url') or self.get_config_val('video_webcam_url')
                or self.get_config_value('video_duck_overlay')):
            raise ValueError('Video file, webcam and duck layers are not implemented yet')
        worker = VideoConnector()
        worker.start(
            self.get_config_val('video_desktop_url'), self.get_config_val('video_bg_image_url'),
            self.get_config_value('video_output_preview'), self.get_config_value('video_live'),
            self.get_config_val('video_output_device'))
        self.connector = worker

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-video.js')
        self.add_css('css/pygdo-video.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_video'))
