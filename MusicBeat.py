"""Ephemeral system-output onset detection for the music animation."""
import array
import math
import os
import signal
import subprocess
import threading
import time


class OnsetDetector:
    """Detect low and high frequency transients, not instrument identities."""
    def __init__(self, rate=16000):
        self.low = 0.0
        self.alpha = 1 - math.exp(-2 * math.pi * 180 / rate)
        self.average = [0.0, 0.0]
        self.last = [-1.0, -1.0]
        self.count = 0
        self.kind = 'unknown'
        self.volume = 0.0

    def feed(self, pcm, now):
        samples = array.array('h')
        samples.frombytes(pcm[:len(pcm) // 2 * 2])
        if not samples:
            return False
        low_energy = high_energy = total_energy = 0.0
        for sample in samples:
            value = sample / 32768.0
            total_energy += value * value
            self.low += self.alpha * (value - self.low)
            low_energy += self.low * self.low
            high_energy += (value - self.low) ** 2
        levels = [math.sqrt(low_energy / len(samples)), math.sqrt(high_energy / len(samples))]
        # Roughly a one-second RMS envelope at 20 ms per block; the fixed
        # reference preserves differences between quiet and loud passages.
        rms = math.sqrt(total_energy / len(samples))
        self.volume += .02 * (rms - self.volume)
        hits = []
        for i, level in enumerate(levels):
            threshold = max(.012, self.average[i] * 1.8)
            hits.append(level > threshold and now - self.last[i] >= .095)
            self.average[i] += .08 * (level - self.average[i])
            if hits[-1]:
                self.last[i] = now
        if any(hits):
            self.count += 1
            # Relative band energy is only a rough timbral cue, not an
            # instrument classifier. Mixed hits deliberately fall back.
            if levels[0] > levels[1] * 1.5:
                self.kind = 'bass'
            elif levels[1] > levels[0] * 1.5:
                self.kind = 'snare'
            else:
                self.kind = 'unknown'
            return True
        return False


class MusicBeat:
    def __init__(self, session_user):
        self.session_user = session_user
        self.detector = OnsetDetector()
        self.lock = threading.Lock()
        self.process = None
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name='duck-music-beat')
        self.thread.start()

    def _run(self):
        from gdo.audio.session import audio_session_command
        try:
            sink = subprocess.run(audio_session_command(['pactl', 'get-default-sink'], self.session_user),
                                  capture_output=True, text=True, check=True, timeout=5).stdout.strip()
            if not sink or '\n' in sink or self.closed.is_set():
                return
            command = audio_session_command(['ffmpeg', '-nostdin', '-loglevel', 'error', '-f', 'pulse',
                '-sample_rate', '16000', '-channels', '1', '-fragment_size', '640', '-i', sink + '.monitor',
                '-ac', '1', '-ar', '16000', '-f', 's16le', 'pipe:1'], self.session_user)
            with self.lock:
                if self.closed.is_set():
                    return
                self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                                bufsize=0, start_new_session=True)
                process = self.process
            while not self.closed.is_set():
                data = process.stdout.read(640)
                if not data:
                    break
                with self.lock:
                    self.detector.feed(data, time.monotonic())
        except (OSError, ValueError, subprocess.SubprocessError):
            return
        finally:
            with self.lock:
                process, self.process = self.process, None
            if process:
                if process.poll() is None:
                    self._terminate(process)
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                process.stdout.close()

    @staticmethod
    def _terminate(process):
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    def snapshot(self):
        with self.lock:
            return self.detector.count, min(1.0, self.detector.volume / .12), self.detector.kind

    def close(self):
        self.closed.set()
        with self.lock:
            if self.process and self.process.poll() is None:
                self._terminate(self.process)
        self.thread.join(timeout=7)
