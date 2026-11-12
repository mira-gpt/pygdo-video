"""Explicit local desktop recording; never starts streaming or a virtual camera."""
import atexit
import os
import pwd
import re
import subprocess
import threading
from datetime import datetime
from pathlib import Path

def audio_session_command(command, session_user):
    from gdo.audio.session import audio_session_command as session_command
    return session_command(command, session_user)


class Recording:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else None
        self.process = None
        self.path = None
        self.lock = threading.RLock()
        atexit.register(self.stop)

    def active(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    @staticmethod
    def pulse_default(kind, session_user):
        result = subprocess.run(audio_session_command(['pactl', 'get-default-' + kind], session_user),
                                capture_output=True, text=True, timeout=5, check=True)
        value = result.stdout.strip()
        if not value or '\n' in value or (kind == 'source' and value.endswith('.monitor')):
            raise ValueError('No suitable default audio ' + kind)
        return value

    @staticmethod
    def command(display, sink, source, session_user, path):
        if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
            raise ValueError('Configure a local X11 display first')
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                   '-f', 'x11grab', '-framerate', '15', '-i', display,
                   '-f', 'pulse', '-i', sink + '.monitor', '-f', 'pulse', '-i', source,
                   '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=longest:normalize=0:weights=0.5 0.5[a]',
                   '-map', '0:v:0', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast',
                   '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-f', 'matroska', '-y', str(path)]
        wrapper = Path(__file__).with_name('recording_encoder.py')
        return audio_session_command(['python3', str(wrapper), *command], session_user)

    def start(self, display, session_user):
        with self.lock:
            if self.active():
                raise RuntimeError('Recording is already running')
            self.stop()
            sink = self.pulse_default('sink', session_user)
            source = self.pulse_default('source', session_user)
            account = pwd.getpwnam(session_user) if session_user else pwd.getpwuid(os.getuid())
            directory = self.directory or Path(account.pw_dir) / 'Videos' / 'Mira'
            subprocess.run(audio_session_command(['mkdir', '-p', '-m', '700', str(directory)], session_user),
                           check=True, timeout=5)
            status = subprocess.run(audio_session_command(['stat', '-c', '%u %a', str(directory)], session_user),
                                    check=True, capture_output=True, text=True, timeout=5)
            owner, permissions = status.stdout.strip().split()
            if int(owner) != account.pw_uid or int(permissions, 8) & 0o077:
                raise RuntimeError('Recording directory must belong to the audio user and be private (mode 700)')
            name = datetime.now().strftime('%Y%m%d_%H%M%S_recording.mkv')
            self.path = directory / name
            reserve = 'import os,sys; fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600); os.close(fd)'
            subprocess.run(audio_session_command(['python3', '-c', reserve, str(self.path)], session_user),
                           check=True, timeout=5)
            command = self.command(display, sink, source, session_user, self.path)
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL, umask=0o077)
            return self.path

    def stop(self):
        with self.lock:
            process = self.process
            if process is None:
                return False
            if process.poll() is None:
                try:
                    process.stdin.write(b'q\n')
                    process.stdin.flush()
                    process.wait(timeout=15)
                except (BrokenPipeError, OSError, ValueError, subprocess.TimeoutExpired):
                    try:
                        process.terminate()
                    except OSError as error:
                        raise RuntimeError('Could not stop recording; it may still be running') from error
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        try:
                            process.kill()
                            process.wait(timeout=5)
                        except (OSError, subprocess.TimeoutExpired) as error:
                            raise RuntimeError('Could not stop recording; it may still be running') from error
            self.process = None
            if process.stdin:
                process.stdin.close()
            if process.returncode:
                raise RuntimeError(f'Recording encoder exited with status {process.returncode}; file may be incomplete')
            return True
