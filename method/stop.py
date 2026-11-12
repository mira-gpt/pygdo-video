import asyncio

from gdo.base.Method import Method
from gdo.video.module_video import module_video


class stop(Method):
    def gdo_user_permission(self):
        return 'owner'

    async def gdo_execute(self):
        try:
            await asyncio.to_thread(module_video.instance().recorder.stop)
        except (OSError, RuntimeError) as error:
            return self.err('video_error', (str(error),))
        if not await asyncio.to_thread(module_video.instance().connector.stop):
            return self.err('video_error', ('Connector is not running or did not stop',))
        return self.reply('video_stopped')
