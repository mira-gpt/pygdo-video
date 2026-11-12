from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.module_video import module_video


class ipc_thoughts(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional(),
                GDT_Bool('audio').not_null().initial('0').positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                module = module_video.instance()
                enabled = self.param_value('enabled')
                module.connector.thoughts(enabled)
                await module.save_config_val('video_thoughts_overlay', '1' if enabled else '0')
                await module.save_config_val('video_thoughts_audio', '1' if enabled and self.param_value('audio') else '0')
                if worker := getattr(module, '_commentary_follower', None):
                    worker.set_audio(False)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Commentary overlay failed: {error}')
        return self.empty()
