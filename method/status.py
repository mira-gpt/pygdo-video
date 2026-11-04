from gdo.base.Method import Method
from gdo.video.module_video import module_video


class status(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_execute(self):
        return self.reply('video_status', (module_video.instance().connector.status(),))
