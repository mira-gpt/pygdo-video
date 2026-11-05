from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.MicrophoneLevel import MicrophoneLevel
from gdo.video.VideoConnector import VideoConnector
from gdo.video.module_video import module_video


class ipc_mic(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    def gdo_execute(self):
        if Application.IS_DOG:
            try:
                connector = module_video.instance().connector
                if not isinstance(connector, VideoConnector):
                    raise ValueError('Microphone meter currently requires virtual-webcam mode')
                if self.param_value('enabled'):
                    connector.put_effect('mic', MicrophoneLevel())
                else:
                    connector.remove_effect('mic')
            except (ValueError, RuntimeError, OSError) as error:
                Logger.warning(f'Video microphone meter failed: {error}')
        return self.empty()
