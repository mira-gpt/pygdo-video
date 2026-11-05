"""Bounded image and silent video layer for the video compositor."""
import io
import os
import subprocess
import tempfile
import threading

from PIL import Image, UnidentifiedImageError
from gdo.video.ImageLayer import ImageLayer


class VideoLayer(ImageLayer):
    FRAME_SIZE = (320, 180)
    MAX_BYTES = 32 * 1024 * 1024

    def __init__(self, path, **kwargs):
        super().__init__(Image.new('RGBA', self.FRAME_SIZE, (0, 0, 0, 0)), **kwargs)
        self.path = path
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.finished = False
        self.started = False
        self.process = None
        self.thread = None
        self.generation = 0

    def start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
            self.process = subprocess.Popen([
                'ffmpeg', '-nostdin', '-loglevel', 'error', '-re',
                '-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm,avi,gif',
                '-i', self.path, '-t', '300', '-an', '-vf',
                'fps=10,scale=320:180:force_original_aspect_ratio=decrease,format=rgba,'
                'pad=320:180:(ow-iw)/2:(oh-ih)/2:color=black@0',
                '-f', 'rawvideo', '-pix_fmt', 'rgba', 'pipe:1'],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.thread = threading.Thread(target=self._read, daemon=True, name='video-media-decoder')
            self.thread.start()

    def _read(self):
        size = self.FRAME_SIZE[0] * self.FRAME_SIZE[1] * 4
        try:
            while not self.stopped.is_set():
                data = bytearray()
                while len(data) < size and not self.stopped.is_set():
                    chunk = self.process.stdout.read(size - len(data))
                    if not chunk:
                        return
                    data.extend(chunk)
                if len(data) == size:
                    with self.lock:
                        self.image = Image.frombytes('RGBA', self.FRAME_SIZE, bytes(data))
                        self.generation += 1
        finally:
            self.finished = True
            self._cleanup()

    def _cleanup(self):
        process = self.process
        if process:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stdout:
                process.stdout.close()
        try:
            os.unlink(self.path)
        except FileNotFoundError:
            pass

    def close(self):
        self.stopped.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(timeout=3)
        if not self.thread:
            self._cleanup()

    def draw(self, frame):
        with self.lock:
            if self.finished:
                return False
            return super().draw(frame)

    def snapshot(self):
        with self.lock:
            return self.image.copy(), self.generation, self.finished


def load_media(url, **kwargs):
    data = ImageLayer.read_url(url, VideoLayer.MAX_BYTES)
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > ImageLayer.MAX_PIXELS:
                raise ValueError('Image dimensions are too large')
            if getattr(image, 'n_frames', 1) == 1:
                if len(data) > ImageLayer.MAX_BYTES:
                    raise ValueError('Image exceeds 4 MiB')
                image.load()
                return ImageLayer(image, **kwargs)
    except UnidentifiedImageError:
        pass
    path = None
    try:
        with tempfile.NamedTemporaryFile(prefix='pygdo-video-', suffix='.bin', delete=False) as file:
            path = file.name
            file.write(data)
        probe = subprocess.run(['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                                '-format_whitelist', 'mov,matroska,webm,avi,gif',
                                '-select_streams', 'v:0', '-show_entries', 'stream=codec_type',
                                '-of', 'csv=p=0', path], capture_output=True, timeout=10)
        if probe.returncode or b'video' not in probe.stdout:
            raise ValueError('Unsupported or invalid video')
        layer = VideoLayer(path, **kwargs)
        path = None
        return layer
    finally:
        if path:
            os.unlink(path)
