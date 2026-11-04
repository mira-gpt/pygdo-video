from gdo.base.Method import Method
from gdo.video.module_video import module_video


class stop(Method):
    def gdo_user_permission(self):
        return 'owner'

    async def gdo_execute(self):
        await module_video.instance().connector.stop()
        return self.reply('video_stopped')
