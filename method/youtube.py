from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.video.module_video import module_video


class youtube(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_Enum('action').choices({'start': 'start', 'stop': 'stop', 'status': 'status'}).positional().initial('status')]

    def gdo_execute(self):
        if not Application.IS_DOG:
            return self.err('video_error', ('Use this command through the running Dog client.',))
        module = module_video.instance()
        sender = module.youtube_sender
        action = self.param_val('action') or 'status'
        try:
            if action == 'start':
                if not module.connector.is_running():
                    raise RuntimeError('Start video first with $video.start')
                sender.start()
            elif action == 'stop':
                sender.stop()
            return self.reply('video_youtube_status', (sender.status(),))
        except (OSError, RuntimeError) as error:
            return self.err('video_error', (str(error),))
