"""Start or stop an explicitly requested private local recording."""
import asyncio
import os
import subprocess

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.core.GDT_Bool import GDT_Bool
from gdo.video.module_video import module_video


class record(Method):
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
                is_running_dog = int(lock.read().strip()) == os.getpid()
        except (OSError, ValueError):
            is_running_dog = False
        if not Application.IS_DOG or not is_running_dog:
            return self.err('video_error', ('Use this command through the running Dog client.',))
        module = module_video.instance()
        recorder = module.recorder
        enabled = self.param_value('enabled')
        try:
            if enabled is True:
                if not module.connector.is_running():
                    raise RuntimeError('Start video first')
                if module.get_config_value('video_mode') != 'screensharing':
                    raise RuntimeError('Recording currently requires screensharing mode')
                from gdo.audio.module_audio import module_audio
                audio = module_audio.instance()
                mic_user = audio.get_config_val('audio_microphone_session_user') or None
                output_user = audio.get_config_val('audio_output_session_user') or None
                if mic_user and output_user and mic_user != output_user:
                    raise ValueError('Microphone and output must use the same audio session')
                path = await asyncio.to_thread(recorder.start, module.get_config_val('video_desktop_url'), mic_user or output_user)
                await asyncio.sleep(1)
                if not recorder.active():
                    await asyncio.to_thread(recorder.stop)
                    raise RuntimeError('Recording stopped immediately')
                return self.reply('video_record_started', (str(path),))
            if enabled is False:
                stopped = await asyncio.to_thread(recorder.stop)
                if stopped:
                    return self.reply('video_record_stopped_mp4', (str(recorder.path.with_suffix('.mp4')),))
                return self.reply('video_record_not_running')
            return self.reply('video_record_running' if recorder.active() else 'video_record_not_running')
        except (ImportError, OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
            return self.err('video_error', (str(error),))
