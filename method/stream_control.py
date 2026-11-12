"""Start or stop direct streaming explicitly through the Dog client."""
import asyncio
import os
import subprocess

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.module_video import module_video


class stream_control(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_transactional(self):
        return False

    def gdo_parameters(self):
        return [GDT_Bool('enabled').positional()]

    async def gdo_execute(self):
        from gdo.core.method.launch import launch
        try:
            with open(launch.lock_path(), encoding='ascii') as lock:
                is_dog = int(lock.read().strip()) == os.getpid()
        except (OSError, ValueError):
            is_dog = False
        if not Application.IS_DOG or not is_dog:
            return self.err('video_error', ('Use this command through the running Dog client.',))
        module = module_video.instance()
        enabled = self.param_value('enabled')
        try:
            if enabled is True:
                if not module.connector.is_running() or module.get_config_value('video_mode') != 'screensharing':
                    raise RuntimeError('Start the screensharing overlay first')
                from gdo.audio.module_audio import module_audio
                audio = module_audio.instance()
                mic_user = audio.get_config_val('audio_microphone_session_user') or None
                output_user = audio.get_config_val('audio_output_session_user') or None
                if mic_user and output_user and mic_user != output_user:
                    raise ValueError('Microphone and output must use the same audio session')
                if not module.direct_stream.active():
                    await module.stream_presence.expire(all_viewers=True)
                await asyncio.to_thread(module.direct_stream.start, module.get_config_val('video_desktop_url'), mic_user or output_user)
                await asyncio.sleep(1)
                if not module.direct_stream.active():
                    await asyncio.to_thread(module.direct_stream.stop)
                    raise RuntimeError('Direct stream encoder stopped immediately')
                return self.reply('video_direct_stream_started_protected' if module.get_config_val('video_gdo_stream_key') else 'video_direct_stream_started_public')
            if enabled is False:
                stopped = await asyncio.to_thread(module.direct_stream.stop)
                await module.stream_presence.expire(all_viewers=True)
                return self.reply('video_direct_stream_stopped' if stopped else 'video_direct_stream_off')
            return self.reply('video_direct_stream_running' if module.direct_stream.active() else 'video_direct_stream_off')
        except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            return self.err('video_error', (str(error),))
