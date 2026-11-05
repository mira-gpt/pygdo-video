"""Controller for one X11 desktop image overlay; no capture or video output."""

import os
import base64
import io
import json
import subprocess
import threading

from gdo.video.VideoConnector import VideoConnector
from gdo.video.StarWars import StarWars


class DesktopOverlay:
    def __init__(self, screensharing=False):
        self.lock = threading.RLock()
        self.process = None
        self.enabled = False
        self.screensharing = screensharing

    def start(self, image):
        image = VideoConnector.local_file(image)
        with self.lock:
            if self.is_running():
                raise RuntimeError('Desktop overlay is already running')
            script = os.path.join(os.path.dirname(__file__), 'desktop_overlay.py')
            self.process = subprocess.Popen(['/usr/bin/python3', script, image,
                                             'screensharing' if self.screensharing else 'overlay'], stdin=subprocess.PIPE,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.enabled = True

    def is_running(self):
        return bool(self.process and self.process.poll() is None)

    def set_layer(self, name, enabled):
        if name != 'overlay':
            raise ValueError('Available desktop overlay layer: overlay')
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            try:
                self.process.stdin.write(b'show\n' if enabled else b'hide\n')
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc
            self.enabled = enabled

    def stop(self):
        with self.lock:
            if not self.is_running():
                return False
            process = self.process
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
            return True

    def starwars(self, text):
        StarWars(text)  # validate before sending untrusted text to the helper
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            try:
                command = json.dumps({'effect': 'starwars', 'text': text}, ensure_ascii=True)
                self.process.stdin.write((command + '\n').encode('utf-8'))
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc

    def vintage(self, enabled):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            try:
                self.process.stdin.write((json.dumps({'effect': 'vintage', 'enabled': bool(enabled)}) + '\n').encode())
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc

    def put_effect(self, key, layer, z=None):
        from gdo.video.ImageLayer import ImageLayer
        if key != 'image' or not isinstance(layer, ImageLayer) or z is not None:
            raise ValueError('Desktop overlay currently accepts only the image layer')
        buffer = io.BytesIO()
        layer.image.save(buffer, format='PNG')
        if buffer.tell() > ImageLayer.MAX_BYTES:
            raise ValueError('Decoded image is too large for desktop overlay')
        payload = {'effect': 'image', 'png': base64.b64encode(buffer.getvalue()).decode('ascii'),
                   'width': layer.width, 'height': layer.height, 'x': layer.x, 'y': layer.y}
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            try:
                self.process.stdin.write((json.dumps(payload) + '\n').encode())
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc

    def remove_effect(self, key):
        if key != 'image':
            raise ValueError('Desktop overlay currently supports removing only the image layer')
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            try:
                self.process.stdin.write(b'{"effect":"image","remove":true}\n')
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc

    def status(self):
        if self.is_running():
            return f'running; desktop overlay={"on" if self.enabled else "off"}'
        if self.process and self.process.returncode:
            return f'stopped (desktop overlay exited with code {self.process.returncode})'
        return 'stopped'
