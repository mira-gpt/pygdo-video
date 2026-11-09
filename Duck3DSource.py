"""Manage one isolated 3D duck renderer and its latest transparent frame."""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image


class Duck3DSource:
    SIZE = 256
    FRAME_BYTES = SIZE * SIZE * 4

    def __init__(self, env=None, pythonpath=None):
        self.lock = threading.Lock()
        self.frame = None
        self.mode = 'idle'
        self.feature_sent = 0.0
        if pythonpath:
            env = dict(os.environ if env is None else env)
            env['PYTHONPATH'] = pythonpath + os.pathsep + env.get('PYTHONPATH', '')
        self.process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name('Duck3DWorker.py'))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, bufsize=0)
        self.reader = threading.Thread(target=self._read_frames, daemon=True, name='duck-3d-frames')
        self.reader.start()

    def _read_frames(self):
        try:
            while True:
                data = bytearray()
                while len(data) < self.FRAME_BYTES:
                    chunk = os.read(self.process.stdout.fileno(), self.FRAME_BYTES - len(data))
                    if not chunk:
                        return
                    data.extend(chunk)
                image = Image.frombytes('RGBA', (self.SIZE, self.SIZE), bytes(data))
                image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                with self.lock:
                    self.frame = image
        except (OSError, ValueError):
            return

    def update(self, **state):
        if 'mode' in state and state['mode'] not in ('idle', 'quacking', 'lol', 'shrug', 'sad', 'cry', 'ouch', 'hello', 'rolleye', 'high', 'music', 'tipsy', 'drunk', 'barf', 'embarrassed', 'plz', 'teacher', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news', 'pirate', 'ghost', 'work', 'bday', 'hah', 'angry', 'inlove', 'trip', 'tired'):
            raise ValueError('Unknown duck animation')
        try:
            with self.lock:
                self.process.stdin.write((json.dumps(state) + '\n').encode())
                if 'mode' in state:
                    self.mode = state['mode']
        except (OSError, ValueError) as error:
            raise RuntimeError('Duck renderer is not running') from error

    def snapshot(self):
        now = time.monotonic()
        if self.mode in ('music', 'metal') and now - self.feature_sent >= .1:
            from gdo.audio.meter import MicrophoneMeter
            features = MicrophoneMeter.features(now)
            self.update(gain=features.gain, frequency_hz=features.frequency_hz)
            self.feature_sent = now
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def wait_ready(self, timeout=5):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.snapshot() is not None:
                return
            if self.process.poll() is not None:
                raise RuntimeError('3D duck renderer failed; check optional dependencies and display')
            time.sleep(.05)
        raise RuntimeError('3D duck renderer did not produce a frame')

    def close(self):
        if self.process.poll() is None:
            try:
                self.update(stop=True)
                self.process.wait(timeout=2)
            except (RuntimeError, subprocess.TimeoutExpired):
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
        self.reader.join(timeout=2)
        self.process.stdin.close()
        self.process.stdout.close()
