import asyncio

from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.ui.GDT_CSSLength import GDT_CSSLength
from gdo.video.ImageLayer import ImageLayer
from gdo.video.module_video import module_video


class ipc_image(Method):
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
                    await asyncio.to_thread(module_video.instance().connector.remove_effect, 'image')
                    return self.empty()
                kwargs = {name: self.param_val(name) for name in ('width', 'height', 'x', 'y')}
                layer = await asyncio.to_thread(ImageLayer.load, self.param_val('url'), **kwargs)
                await asyncio.to_thread(module_video.instance().connector.put_effect, 'image', layer)
            except (ValueError, RuntimeError, OSError, AttributeError) as exc:
                Logger.warning(f'Video image IPC failed: {exc}')
        return self.empty()
