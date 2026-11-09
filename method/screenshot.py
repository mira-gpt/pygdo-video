"""Capture the configured local X11 desktop as a publicly accessible PNG."""
import asyncio
import os
import re
import secrets
import subprocess
from pathlib import Path

from gdo.base.Application import Application
from gdo.base.Method import Method
from gdo.video.module_video import module_video


def capture_screenshot(display, destination):
    if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
        raise ValueError('Configure a local X11 display first')
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-f', 'x11grab',
         '-i', display, '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15, check=True)
    if not result.stdout.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Screenshot capture did not return a PNG')
    path = Path(destination) / f'cheese-{secrets.token_hex(16)}.png'
    # Exclusive creation avoids overwriting other public files.
    with path.open('xb') as output:
        output.write(result.stdout)
    os.chmod(path, 0o644)
    return path.name


class screenshot(Method):
    @classmethod
    def gdo_trig(cls):
        return 'cheese'

    def gdo_user_permission(self):
        return 'admin'

    async def gdo_execute(self):
        try:
            display = module_video.instance().get_config_val('video_desktop_url')
            destination = Path(Application.file_path('gdo/mira/public'))
            name = await asyncio.to_thread(capture_screenshot, display, destination)
            scheme = 'https' if str(Application.config('core.force_tls', '0')).lower() in ('1', 'true', 'https') else 'http'
            root = Application.web_root().strip('/')
            prefix = f'/{root}' if root else ''
            url = f'{scheme}://{Application.domain()}{prefix}/gdo/mira/public/{name}'
            return self.reply('video_screenshot_public', (url,))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            return self.err('video_error', (str(error),))
