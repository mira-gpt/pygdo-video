"""Controller for one X11 desktop image overlay; no capture or video output."""

import os
import base64
import io
import json
import subprocess
import threading
import time

from gdo.video.VideoConnector import VideoConnector
from gdo.video.StarWars import StarWars


class DesktopOverlay:
    def __init__(self, screensharing=False):
        self.lock = threading.RLock()
        self.process = None
        self.enabled = False
        self.screensharing = screensharing
        self.media_layer = None

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
            media, self.media_layer = self.media_layer, None
            process = self.process
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            process.stdin.close()
        if media and hasattr(media, 'close'):
            media.close()
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
        from gdo.video.MediaLayer import VideoLayer
        if key != 'media' or not isinstance(layer, ImageLayer) or z is not None:
            raise ValueError('Desktop overlay currently accepts only the media layer')
        if isinstance(layer, VideoLayer):
            layer.start()
        payload = self._image_payload(layer, layer.image)
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            previous, self.media_layer = self.media_layer, layer
            self._send_payload(payload)
        if previous and hasattr(previous, 'close'):
            previous.close()
        if isinstance(layer, VideoLayer):
            threading.Thread(target=self._pump_video, args=(layer,), daemon=True,
                             name='video-desktop-media').start()

    def _image_payload(self, layer, image):
        from gdo.video.ImageLayer import ImageLayer
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        if buffer.tell() > ImageLayer.MAX_BYTES:
            raise ValueError('Decoded image is too large for desktop overlay')
        return {'effect': 'image', 'png': base64.b64encode(buffer.getvalue()).decode('ascii'),
                'width': layer.width, 'height': layer.height, 'x': layer.x, 'y': layer.y}

    def _send_payload(self, payload):
        try:
            self.process.stdin.write((json.dumps(payload) + '\n').encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError('Desktop overlay stopped') from exc

    def _pump_video(self, layer):
        last = -1
        while True:
            image, generation, finished = layer.snapshot()
            with self.lock:
                if self.media_layer is not layer or not self.is_running():
                    return
                if finished:
                    self.media_layer = None
                    try:
                        self._send_payload({'effect': 'image', 'remove': True})
                    except RuntimeError:
                        pass
                    return
                if generation != last:
                    try:
                        self._send_payload(self._image_payload(layer, image))
                    except (RuntimeError, ValueError):
                        self.media_layer = None
                        layer.close()
                        return
                    last = generation
            time.sleep(.1)

    def remove_effect(self, key):
        if key != 'media':
            raise ValueError('Desktop overlay currently supports removing only the media layer')
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            media, self.media_layer = self.media_layer, None
            try:
                self.process.stdin.write(b'{"effect":"image","remove":true}\n')
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as exc:
                raise RuntimeError('Desktop overlay stopped') from exc
        if media and hasattr(media, 'close'):
            media.close()

    def status(self):
        if self.is_running():
            return f'running; desktop overlay={"on" if self.enabled else "off"}'
        if self.process and self.process.returncode:
            return f'stopped (desktop overlay exited with code {self.process.returncode})'
        return 'stopped'
