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
from gdo.video.DrawingProtocol import validate_line


class DesktopOverlay:
    def __init__(self, screensharing=False, window_suffix=''):
        self.lock = threading.RLock()
        self.process = None
        self.enabled = False
        self.screensharing = screensharing
        self.window_suffix = window_suffix
        self.media_layer = None
        self._mic_stop = None
        self._mic_wake = None
        self.duck_enabled = False
        self.duck_speech_id = None
        self.duck_source = None
        self.duck3d_pythonpath = None
        self.liveshow_enabled = False

    def liveshow(self, enabled):
        with self.lock:
            self.liveshow_enabled = bool(enabled)
            if self.is_running():
                self._send_payload({'effect': 'liveshow', 'enabled': self.liveshow_enabled})

    def start(self, image):
        image = VideoConnector.local_file(image)
        with self.lock:
            if self.is_running():
                raise RuntimeError('Desktop overlay is already running')
            script = os.path.join(os.path.dirname(__file__), 'desktop_overlay.py')
            self.process = subprocess.Popen(['/usr/bin/python3', script, image,
                                             'screensharing' if self.screensharing else 'overlay',
                                             self.window_suffix], stdin=subprocess.PIPE,
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
        source, self.duck_source = self.duck_source, None
        if source:
            source.close()
        with self.lock:
            if self._mic_stop:
                self._mic_stop.set()
                self._mic_wake.set()
                self._mic_stop = None
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

    def zap(self, duration=.666):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            self._send_payload({'effect': 'zap', 'duration': duration})

    def crt_off(self, duration=2.0):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            self._send_payload({'effect': 'crt_off', 'duration': duration})

    def draw_line(self, *line):
        line = validate_line(*line)
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            self._send_payload({'effect': 'drawing', 'line': line})

    def clear_drawing(self):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            self._send_payload({'effect': 'drawing', 'clear': True})

    def put_effect(self, key, layer, z=None):
        from gdo.video.ImageLayer import ImageLayer
        from gdo.video.MediaLayer import VideoLayer
        if key != 'media' or not isinstance(layer, ImageLayer) or z is not None:
            raise ValueError('Desktop overlay currently accepts only the media layer')
        layer.begin_transition()
        if isinstance(layer, VideoLayer):
            layer.start()
        payload = self._image_payload(layer, layer.image, transition_start=True)
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

    def _image_payload(self, layer, image, transition_start=False):
        from gdo.video.ImageLayer import ImageLayer
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        if buffer.tell() > ImageLayer.MAX_BYTES:
            raise ValueError('Decoded image is too large for desktop overlay')
        return {'effect': 'image', 'png': base64.b64encode(buffer.getvalue()).decode('ascii'),
                'width': layer.width, 'height': layer.height, 'x': layer.x, 'y': layer.y,
                'transition': layer.transition, 'transition_start': transition_start}

    def _send_payload(self, payload):
        try:
            self.process.stdin.write((json.dumps(payload) + '\n').encode())
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise RuntimeError('Desktop overlay stopped') from exc

    def duck(self, enabled):
        source, self.duck_source = self.duck_source, None
        if source:
            source.close()
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            if enabled:
                root = os.path.join(os.path.dirname(__file__), 'assets', 'duck')
                poses = []
                for name in ('duck-closed.png', 'duck-open.png'):
                    with open(os.path.join(root, name), 'rb') as stream:
                        poses.append(base64.b64encode(stream.read()).decode('ascii'))
                self._send_payload({'effect': 'duck', 'poses': poses})
            else:
                self._send_payload({'effect': 'duck', 'remove': True})
            self.duck_enabled = enabled
            self.duck_speech_id = None

    def duck3d(self, enabled):
        if not enabled:
            self.duck(False)
            return
        from gdo.video.Duck3DSource import Duck3DSource
        source = Duck3DSource(pythonpath=self.duck3d_pythonpath)
        try:
            source.wait_ready()
            self.duck(True)
            with self.lock:
                self.duck_source = source
            threading.Thread(target=self._pump_duck3d, args=(source,), daemon=True,
                             name='video-desktop-duck3d').start()
        except Exception:
            source.close()
            raise

    def _pump_duck3d(self, source):
        while self.duck_source is source and source.process.poll() is None:
            frame = source.snapshot()
            if frame:
                buffer = io.BytesIO()
                frame.save(buffer, format='PNG')
                with self.lock:
                    if self.duck_source is not source or not self.is_running():
                        break
                    try:
                        self._send_payload({'effect': 'duck_frame', 'png': base64.b64encode(buffer.getvalue()).decode('ascii')})
                    except RuntimeError:
                        break
            time.sleep(1 / 15)

    def duck_animation(self, mode):
        if not self.duck_source:
            raise RuntimeError('Enable the live 3D duck first')
        self.duck_source.update(mode=mode)

    def speech_start(self, speech_id, text):
        with self.lock:
            if self.duck_enabled and self.is_running():
                self._send_payload({'effect': 'duck_speech', 'speaking': True, 'text': text[:300]})
                self.duck_speech_id = speech_id
                if self.duck_source:
                    self.duck_source.update(speaking=True)

    def duck_caption(self, text):
        with self.lock:
            if not self.duck_enabled or not self.is_running():
                raise RuntimeError('Enable the duck first')
            self._send_payload({'effect': 'duck_caption', 'text': text})

    def speech_envelope(self, speech_id, levels, step_ms):
        with self.lock:
            if self.duck_source and self.duck_speech_id == speech_id:
                self.duck_source.update(envelope=levels, step_ms=step_ms)

    def speech_end(self, speech_id):
        with self.lock:
            if self.duck_enabled and self.duck_speech_id == speech_id and self.is_running():
                self._send_payload({'effect': 'duck_speech', 'speaking': False, 'text': ''})
                self.duck_speech_id = None
                if self.duck_source:
                    self.duck_source.update(speaking=False)

    def microphone_meter(self, enabled):
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            if self._mic_stop:
                self._mic_stop.set()
                self._mic_wake.set()
                self._mic_stop = None
            if not enabled:
                self._send_payload({'effect': 'mic', 'remove': True})
                return
            stop = threading.Event()
            wake = threading.Event()
            self._mic_stop = stop
            self._mic_wake = wake
            threading.Thread(target=self._pump_microphone, args=(stop, wake), daemon=True,
                             name='video-desktop-mic').start()

    def _pump_microphone(self, stop, wake):
        try:
            from gdo.audio.meter import MicrophoneMeter
        except ImportError:
            with self.lock:
                if self.is_running():
                    self._send_payload({'effect': 'mic', 'status': 'unknown', 'level': 0})
            return
        MicrophoneMeter.subscribe(wake.set)
        wake.set()
        try:
            while not stop.is_set():
                wake.wait()
                wake.clear()
                status, level = MicrophoneMeter.snapshot()
                transcription = MicrophoneMeter.transcription_snapshot()
                text = MicrophoneMeter.transcription_text_snapshot()
                text_updated = MicrophoneMeter.transcription_text_timestamp()
                with self.lock:
                    if stop.is_set() or self._mic_stop is not stop or not self.is_running():
                        return
                    try:
                        self._send_payload({'effect': 'mic', 'status': status, 'level': level,
                                            'transcription': transcription, 'text': text, 'text_updated': text_updated})
                    except RuntimeError:
                        return
        finally:
            MicrophoneMeter.unsubscribe(wake.set)

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

    def close_effects(self, key):
        source = None
        with self.lock:
            if not self.is_running():
                raise RuntimeError('Desktop overlay is not running')
            if key in ('all', 'mic') and self._mic_stop:
                self._mic_stop.set()
                self._mic_wake.set()
                self._mic_stop = None
            if key in ('all', 'duck'):
                self.duck_enabled = False
                self.duck_speech_id = None
                source, self.duck_source = self.duck_source, None
            media = None
            if key in ('all', 'media'):
                media, self.media_layer = self.media_layer, None
            if key in ('all', 'overlay'):
                self.process.stdin.write(b'hide\n')
                self.process.stdin.flush()
                self.enabled = False
            if key != 'overlay':
                self._send_payload({'effect': 'close', 'key': key})
        if media and hasattr(media, 'close'):
            media.close()
        if source:
            source.close()

    def status(self):
        if self.is_running():
            return f'running; desktop overlay={"on" if self.enabled else "off"}'
        if self.process and self.process.returncode:
            return f'stopped (desktop overlay exited with code {self.process.returncode})'
        return 'stopped'
