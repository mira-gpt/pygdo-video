"""Local compositor with independently switchable preview and V4L2 output."""

import os
import re
import stat
import subprocess
import threading
from urllib.parse import unquote, urlsplit

from PIL import Image, ImageOps
from gdo.video.StarWars import StarWars
from gdo.video.LayerStack import LayerStack
from gdo.video.Vintage import Vintage
from gdo.video.Magnify import Magnify, X11Pointer
from gdo.video.Drawing import Drawing


class VideoConnector:
    WIDTH, HEIGHT, FPS = 640, 360, 15

    def __init__(self):
        self.lock = threading.RLock()
        self.worker = None
        self.stop_event = threading.Event()
        self.capture = None
        self.outputs = []
        self.frame = None
        self.error = None
        self.effects = LayerStack()
        self.enabled = {'desktop': False, 'bg_image': False}

    @staticmethod
    def local_file(value):
        parsed = urlsplit(value or '')
        if parsed.scheme == 'file' and not parsed.netloc and not parsed.query and not parsed.fragment:
            value = unquote(parsed.path)
        elif parsed.scheme:
            raise ValueError('Only local image files are supported')
        if not value or not os.path.isabs(value) or not os.path.isfile(value):
            raise ValueError('Background image must be an existing absolute file')
        return value

    @staticmethod
    def validate_output(output):
        if not re.fullmatch(r'/dev/video[0-9]+', output or ''):
            raise ValueError('Output must be a /dev/videoN device')
        device = os.path.basename(output)
        if not os.path.realpath('/sys/class/video4linux/' + device).startswith('/sys/devices/virtual/video4linux/'):
            raise ValueError('Output must be an existing virtual video device')
        if not stat.S_ISCHR(os.stat(output).st_mode):
            raise ValueError('Output is not a character device')

    @classmethod
    def desktop_command(cls, display):
        if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
            raise ValueError('Desktop must be an X11 display such as :0.0')
        return ['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'x11grab',
                '-framerate', str(cls.FPS), '-i', display, '-vf',
                f'scale={cls.WIDTH}:{cls.HEIGHT}:force_original_aspect_ratio=decrease,'
                f'pad={cls.WIDTH}:{cls.HEIGHT}:(ow-iw)/2:(oh-ih)/2',
                '-pix_fmt', 'rgb24', '-f', 'rawvideo', 'pipe:1']

    @classmethod
    def output_commands(cls, preview, live, device, preview_w=320, preview_h=180):
        source = ['-f', 'rawvideo', '-pixel_format', 'rgb24', '-video_size',
                  f'{cls.WIDTH}x{cls.HEIGHT}', '-framerate', str(cls.FPS), '-i', 'pipe:0']
        commands = []
        if preview:
            commands.append(['ffplay', '-loglevel', 'error', '-window_title', 'Mira Video Preview',
                             '-left', '0', '-top', '0', '-x', str(preview_w), '-y', str(preview_h), *source])
        if live:
            cls.validate_output(device)
            commands.append(['ffmpeg', '-nostdin', '-loglevel', 'error', *source,
                             '-pix_fmt', 'yuv420p', '-f', 'v4l2', device])
        if not commands:
            raise ValueError('Enable video_output_preview or video_live before starting')
        return commands

    def start(self, desktop, image, preview, live, device, preview_w=320, preview_h=180):
        with self.lock:
            if self.worker and self.worker.is_alive():
                raise RuntimeError('Video connector is already running')
            if desktop:
                self.desktop_command(desktop)
            background = Image.new('RGB', (self.WIDTH, self.HEIGHT), 'black')
            if image:
                with Image.open(self.local_file(image)) as original:
                    background = ImageOps.fit(original.convert('RGB'), (self.WIDTH, self.HEIGHT),
                                              method=Image.Resampling.LANCZOS)
            commands = self.output_commands(preview, live, device, preview_w, preview_h)
            self.desktop, self.background = desktop, background
            self.image_configured = bool(image)
            self.enabled = {'desktop': bool(desktop), 'bg_image': bool(image)}
            self.frame, self.error = None, None
            for _, effect in self.effects.ordered():
                if hasattr(effect, 'close'):
                    effect.close()
            self.effects.clear()
            self.stop_event.clear()
            self.outputs = []
            try:
                for command in commands:
                    self.outputs.append(subprocess.Popen(command, stdin=subprocess.PIPE,
                                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            except Exception:
                self._terminate_outputs()
                raise
            self.worker = threading.Thread(target=self._run, name='video-compositor', daemon=True)
            self.worker.start()

    def _capture_frames(self, process):
        size = self.WIDTH * self.HEIGHT * 3
        try:
            while not self.stop_event.is_set():
                chunks = bytearray()
                while len(chunks) < size:
                    chunk = process.stdout.read(size - len(chunks))
                    if not chunk:
                        return
                    chunks.extend(chunk)
                with self.lock:
                    if self.capture is not process:
                        return
                    self.frame = bytes(chunks)
        finally:
            if not self.stop_event.is_set():
                with self.lock:
                    if self.capture is process and self.enabled['desktop']:
                        self.error = 'Desktop capture stopped; check X11 permissions and display'
                        self.stop_event.set()

    def _start_capture(self):
        process = subprocess.Popen(self.desktop_command(self.desktop), stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        self.capture = process
        threading.Thread(target=self._capture_frames, args=(process,), daemon=True).start()

    def _stop_capture(self):
        process, self.capture = self.capture, None
        self.frame = None
        if process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdout.close()

    def set_layer(self, name, enabled):
        if name not in self.enabled:
            raise ValueError('Available layers: desktop, bg_image')
        with self.lock:
            if not self.worker or not self.worker.is_alive():
                raise RuntimeError('Video connector is not running')
            if enabled and name == 'desktop' and not self.desktop:
                raise ValueError('Configure video_desktop_url first')
            if enabled and name == 'bg_image' and not self.image_configured:
                raise ValueError('Configure video_bg_image_url first')
            self.enabled[name] = enabled
            if name == 'desktop' and not enabled:
                self.effects.remove('magnify')

    def starwars(self, text):
        effect = StarWars(text)
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Video connector is not running')
            self.effects.put('starwars', effect)

    def put_effect(self, key, effect, z=None):
        """Install a frame-drawing effect; called by plugins in the Dog process."""
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Video connector is not running')
            if key == 'media':
                effect.output_size(self.WIDTH, self.HEIGHT)
                if hasattr(effect, 'start'):
                    effect.start()
            previous = self.effects.get(key)
            self.effects.put(key, effect, z)
            if previous and hasattr(previous, 'close'):
                previous.close()

    def remove_effect(self, key):
        with self.lock:
            previous = self.effects.get(key)
            removed = self.effects.remove(key)
            if previous and hasattr(previous, 'close'):
                previous.close()
            return removed

    def close_effects(self, key):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Video connector is not running')
            keys = [name for name, _ in self.effects.ordered()] if key == 'all' else [key]
            for name in keys:
                self.remove_effect(name)

    def vintage(self, enabled):
        if enabled:
            self.put_effect('vintage', Vintage())
        else:
            self.remove_effect('vintage')

    def magnify(self, enabled, zoom=2.0, radius=90):
        if not enabled:
            self.remove_effect('magnify')
            return
        with self.lock:
            if not self.desktop or not self.enabled['desktop']:
                raise ValueError('Enable an X11 desktop source before magnifying')
            self.put_effect('magnify', Magnify(X11Pointer(self.desktop), zoom, radius))

    def draw_line(self, *line):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Video connector is not running')
            drawing = self.effects.get('drawing')
            if drawing is None:
                drawing = Drawing()
                self.effects.put('drawing', drawing)
            drawing.add(*line)

    def clear_drawing(self):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Video connector is not running')
            return self.effects.remove('drawing')

    def _run(self):
        try:
            while not self.stop_event.is_set():
                with self.lock:
                    if self.enabled['desktop'] and not self.capture:
                        self._start_capture()
                    elif not self.enabled['desktop'] and self.capture:
                        self._stop_capture()
                    frame = self.frame if self.enabled['desktop'] else None
                    if frame is None:
                        frame = (self.background if self.enabled['bg_image'] else
                                 Image.new('RGB', (self.WIDTH, self.HEIGHT), 'black')).tobytes()
                    if self.effects.ordered():
                        canvas = Image.frombytes('RGB', (self.WIDTH, self.HEIGHT), frame)
                        for key, effect in self.effects.ordered():
                            if not effect.draw(canvas):
                                self.effects.remove(key)
                        frame = canvas.tobytes()
                for output in self.outputs:
                    output.stdin.write(frame)
                    output.stdin.flush()
                self.stop_event.wait(1 / self.FPS)
        except Exception as exc:
            if not self.stop_event.is_set():
                self.error = f'Video output failed: {exc}'
        finally:
            with self.lock:
                self._stop_capture()
                for _, effect in self.effects.ordered():
                    if hasattr(effect, 'close'):
                        effect.close()
                self.effects.clear()
            self._terminate_outputs()

    def _terminate_outputs(self):
        for process in self.outputs:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            if process.stdin:
                process.stdin.close()
        self.outputs = []

    def stop(self):
        with self.lock:
            worker = self.worker
            if not worker or not worker.is_alive():
                return False
            self.stop_event.set()
            # Terminating consumers also unblocks a writer if a consumer stalled.
            for process in self.outputs:
                if process.poll() is None:
                    process.terminate()
        worker.join(timeout=5)
        return not worker.is_alive()

    def status(self):
        if self.is_running():
            return 'running; layers: ' + ', '.join(f'{k}={"on" if v else "off"}' for k, v in self.enabled.items())
        return f'stopped ({self.error})' if self.error else 'stopped'

    def is_running(self):
        return bool(self.worker and self.worker.is_alive())
