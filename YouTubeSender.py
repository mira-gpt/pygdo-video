"""Lifecycle for the local, private YouTube HLS sender."""
import atexit
import subprocess
import shutil
import sys
import threading
from pathlib import Path


class YouTubeSender:
    def __init__(self, script=None):
        self.script = Path(script) if script else Path(__file__).with_name('youtube_hls_sender.py')
        self.process = None
        self.lock = threading.RLock()
        atexit.register(self.stop)

    def status(self):
        with self.lock:
            if self.process is None:
                return 'stopped'
            result = self.process.poll()
            return 'running' if result is None else f'exited ({result})'

    def preflight(self):
        from gdo.video.youtube_hls_sender import validate_url
        if self.status() == 'running':
            raise RuntimeError('YouTube sender is already running')
        if not self.script.is_file() or not shutil.which('ffmpeg'):
            raise RuntimeError('YouTube sender or ffmpeg is unavailable')
        secret = Path('/home/mira/data/youtube-streaming.nf0')
        if secret.stat().st_mode & 0o077:
            raise RuntimeError('YouTube URL file must be private')
        url = next((line.split(':', 1)[1].strip() for line in secret.read_text(encoding='utf8').splitlines()
                    if line.lower().startswith('url:')), '')
        validate_url(url)

    def start(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                raise RuntimeError('YouTube sender is already running')
            if not self.script.is_file():
                raise RuntimeError('Local HLS sender script is missing')
            self.process = subprocess.Popen([sys.executable, str(self.script)],
                                            stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)

    def stop(self):
        with self.lock:
            if self.process is None or self.process.poll() is not None:
                return False
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            return True
