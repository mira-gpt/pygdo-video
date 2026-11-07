import asyncio

from gdo.audio.module_audio import module_audio
from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.Method import Method
from gdo.core.GDT_Float import GDT_Float
from gdo.video.module_video import module_video


class ipc_zap(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Float('duration').not_null().min(.05).max(30).positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            duration = float(self.param_value('duration'))
            try:
                module_video.instance().connector.zap(duration)
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Video zap failed: {error}')
            try:
                target = module_audio.instance().cfg_output_device()
                if not target:
                    raise ValueError('Audio output device is not configured')
                process = await asyncio.create_subprocess_exec(
                    'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error',
                    '-re', '-f', 'lavfi', '-i', f'anoisesrc=color=white:amplitude=0.08:duration={duration}',
                    '-f', 'pulse', '-device', target, 'tv-static',
                    stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
                if await process.wait():
                    Logger.warning('TV static audio playback failed')
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'TV static audio failed: {error}')
        return self.empty()
