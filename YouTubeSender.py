"""Lifecycle for the local, private YouTube HLS sender."""
import atexit
import subprocess
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
