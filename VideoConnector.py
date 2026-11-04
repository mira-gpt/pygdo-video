"""Explicitly controlled FFmpeg output to a Linux virtual video device."""

import asyncio
import os
import re
import stat
from urllib.parse import unquote, urlsplit


class VideoConnector:
    def __init__(self):
        self.process = None
        self._lock = asyncio.Lock()

    @staticmethod
    def command(mode, source, output):
        if not re.fullmatch(r'/dev/video[0-9]+', output or ''):
            raise ValueError('Output must be a /dev/videoN device')
        device = os.path.basename(output)
        sys_device = os.path.realpath('/sys/class/video4linux/' + device)
        if not sys_device.startswith('/sys/devices/virtual/video4linux/'):
            raise ValueError('Output must be an existing virtual video device')
        if not stat.S_ISCHR(os.stat(output).st_mode):
            raise ValueError('Output is not a character device')
        if mode == 'file':
            if not source:
                raise ValueError('Set video_input_url to a local video file')
            parsed = urlsplit(source)
            if parsed.scheme == 'file' and not parsed.netloc and not parsed.query and not parsed.fragment:
                source = unquote(parsed.path)
            elif parsed.scheme:
                raise ValueError('Only local files are supported in V1')
            if not os.path.isabs(source) or not os.path.isfile(source):
                raise ValueError('Input must be an existing absolute file path')
            input_args = ['-re', '-stream_loop', '-1', '-i', source]
        elif mode == 'desktop':
            display = source or os.environ.get('DISPLAY', '')
            if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display):
                raise ValueError('Set video_input_url to an X11 display such as :0.0')
            input_args = ['-f', 'x11grab', '-framerate', '30', '-i', display]
        else:
            raise ValueError('This input mode is not implemented yet')
        return ['ffmpeg', '-nostdin', '-loglevel', 'error', *input_args,
                '-an', '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease,'
                'pad=1280:720:(ow-iw)/2:(oh-ih)/2', '-r', '30',
                '-pix_fmt', 'yuv420p', '-f', 'v4l2', output]

    async def start(self, mode, source, output):
        async with self._lock:
            if self.process and self.process.returncode is None:
                raise RuntimeError('Video connector is already running')
            cmd = self.command(mode, source, output)
            self.process = await asyncio.create_subprocess_exec(
                *cmd, stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await asyncio.sleep(0.3)
            if self.process.returncode is not None:
                raise RuntimeError('FFmpeg exited during startup; check the source and device')

    async def stop(self):
        async with self._lock:
            process = self.process
            if not process or process.returncode is not None:
                return False
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), 5)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
            return True

    def status(self):
        return 'running' if self.process and self.process.returncode is None else 'stopped'
