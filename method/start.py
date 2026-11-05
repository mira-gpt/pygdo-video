import asyncio

from gdo.base.Method import Method
from gdo.video.module_video import module_video


class start(Method):
    def gdo_user_permission(self):
        return 'owner'

    async def gdo_execute(self):
        module = module_video.instance()
        try:
            module.start_compositor()
        except (ValueError, OSError, RuntimeError) as exc:
            return self.err('video_error', (str(exc),))
        await asyncio.sleep(0.5)
        if not module.connector.is_running():
            return self.err('video_error', (module.connector.status(),))
        return self.reply('video_started')
