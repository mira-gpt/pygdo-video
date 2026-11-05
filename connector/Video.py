"""Dog lifecycle adapter for the local video compositor."""

import asyncio

from gdo.base.Logger import Logger
from gdo.core.Connector import Connector


class Video(Connector):
    async def gdo_connect(self):
        from gdo.video.module_video import module_video
        module = module_video.instance()
        mode = module.get_config_value('video_mode')
        if mode == 'off':
            self._connected = True
            return True
        try:
            module.start_compositor()
            await asyncio.sleep(0.5)
            if not module.connector.is_running():
                raise RuntimeError(module.connector.status())
        except (ValueError, OSError, RuntimeError) as exc:
            Logger.warning(f'Video connector could not start: {exc}')
            self._connected = False
            return False
        self._connected = True
        return True

    async def gdo_disconnect(self, quit_message):
        from gdo.video.module_video import module_video
        await asyncio.to_thread(module_video.instance().connector.stop)
