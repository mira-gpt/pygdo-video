from __future__ import annotations

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_Link import GDT_Link
from gdo.video.VideoConnector import VideoConnector

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_video(GDO_Module):
    connector = VideoConnector()

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        pass

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_String('video_desktop_url').maxlen(2048),
            GDT_String('video_file_url').maxlen(2048),
            GDT_String('video_webcam_url').maxlen(2048),
            GDT_Bool('video_duck_overlay').not_null().initial('0').tooltip('tt_video_duck_overlay'),
            GDT_String('video_output_device').not_null().initial('/dev/video2').maxlen(255),
        ]

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        pass

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-video.js')
        self.add_css('css/pygdo-video.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_video'))
