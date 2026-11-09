from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.module_video import module_video


class ipc_mic(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module = module_video.instance()
                enabled = self.param_value('enabled')
                module.connector.microphone_meter(enabled)
                await module.save_config_val('video_mic_overlay', '1' if enabled else '0')
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Video microphone meter failed: {error}')
        return self.empty()
