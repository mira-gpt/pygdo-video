import asyncio

from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_CSSLength import GDT_CSSLength
from gdo.video.MediaLayer import load_media
from gdo.video.module_video import module_video


class ipc_media(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_String('url').not_null().maxlen(768).positional(),
                *[GDT_CSSLength(name).not_null().positional() for name in ('width', 'height', 'x', 'y')]]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                if self.param_val('url').lower() == 'off':
                    await asyncio.to_thread(module_video.instance().connector.remove_effect, 'media')
                    return self.empty()
                kwargs = {name: self.param_val(name) for name in ('width', 'height', 'x', 'y')}
                layer = await asyncio.to_thread(load_media, self.param_val('url'), **kwargs)
                try:
                    await asyncio.to_thread(module_video.instance().connector.put_effect, 'media', layer)
                except Exception:
                    if hasattr(layer, 'close'):
                        await asyncio.to_thread(layer.close)
                    raise
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video image IPC failed: {exc}')
        return self.empty()
