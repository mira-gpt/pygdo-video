import asyncio

from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_Bool import GDT_Bool
from gdo.ui.GDT_CSSLength import GDT_CSSLength
from gdo.video.MediaLayer import load_media
from gdo.video.module_video import module_video


class ipc_media(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('url').not_null().maxlen(768).positional(),
                *[GDT_CSSLength(name).not_null().positional() for name in ('width', 'height', 'x', 'y')],
                GDT_Enum('transition').initial('fade').choices({'fade': 'Fade', 'throw': 'Throw', 'cyclone': 'Cyclone'}).positional(),
                GDT_Bool('autoplay').initial('0').positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                if self.param_val('url').lower() == 'off':
                    await asyncio.to_thread(module_video.instance().connector.remove_effect, 'media')
                    return self.empty()
                kwargs = {name: self.param_val(name) for name in ('width', 'height', 'x', 'y')}
                kwargs['transition'] = self.param_val('transition') or 'fade'
                autoplay = bool(self.param_value('autoplay'))
                from gdo.video.DesktopOverlay import DesktopOverlay
                if isinstance(module_video.instance().connector, DesktopOverlay):
                    await asyncio.to_thread(module_video.instance().connector.show_web_media,
                                            self.param_val('url'), autoplay=autoplay, **kwargs)
                    return self.empty()
                layer = await asyncio.to_thread(load_media, self.param_val('url'), **kwargs)
                try:
                    from gdo.video.MediaLayer import VideoLayer
                    if isinstance(layer, VideoLayer) and not autoplay:
                        raise ValueError('Paused video playback requires desktop screensharing mode; use autoplay=1 for the compositor')
                    await asyncio.to_thread(module_video.instance().connector.put_effect, 'media', layer)
                except Exception:
                    if hasattr(layer, 'close'):
                        await asyncio.to_thread(layer.close)
                    raise
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video image IPC failed: {exc}')
        return self.empty()
