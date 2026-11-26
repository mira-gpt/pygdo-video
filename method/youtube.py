from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Enum import GDT_Enum
from gdo.video.module_video import module_video
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.VideoConnector import VideoConnector


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
                sender.preflight()
                device = module.get_config_val('video_output_device')
                if device != '/dev/video2':
                    raise ValueError('YouTube sender requires video_output_device /dev/video2')
                VideoConnector.validate_output(device)
                if not VideoConnector.virtual_camera_allowed():
                    raise ValueError('Virtual camera is disabled in this configuration')
                started_worker = False
                started_output = False
                try:
                    if not module.connector.is_running():
                        module.start_compositor(mode_override='screensharing', live_override=True)
                        started_worker = True
                    elif isinstance(module.connector, DesktopOverlay):
                        if module.connector.virtual_output is None:
                            module.connector.start_virtual_output(module.get_config_val('video_desktop_url'), device)
                            started_output = True
                        elif getattr(module.connector.virtual_output, 'youtube_device', None) != device:
                            raise RuntimeError('Virtual camera already running; check its destination before starting YouTube')
                    else:
                        raise RuntimeError('Stop the running video worker before YouTube setup')
                    if not module.connector.is_running():
                        raise RuntimeError('Video worker did not start')
                    sender.start()
                except Exception:
                    if started_worker:
                        module.connector.stop()
                    elif started_output:
                        module.connector.virtual_output.stop()
                        module.connector.virtual_output = None
                    raise
            elif action == 'stop':
                sender.stop()
            return self.reply('video_youtube_status', (sender.status(),))
        except (OSError, RuntimeError, ValueError) as error:
            return self.err('video_error', (str(error),))
