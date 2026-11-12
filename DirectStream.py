"""Explicit, shared HLS capture of the screensharing desktop and audio."""
import atexit
import json
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path

from gdo.video.Recording import Recording, audio_session_command

RUN_NAME = re.compile(r'run-[a-zA-Z0-9_-]+\Z')
ASSET_NAME = re.compile(r'(?:index\.m3u8|segment_\d{8}\.ts)\Z')


def process_start(pid):
    try:
        # The command name may contain spaces and parentheses.
        fields = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] == 'Z':
            return None
        return fields[19]
    except (OSError, ValueError, IndexError):
        return None


def active_asset(root, name):
    if not isinstance(name, str) or not ASSET_NAME.fullmatch(name):
        return None
    root = Path(root)
    try:
        info = json.loads((root / 'active.json').read_text(encoding='utf-8'))
        run = info['run']
        if (not isinstance(run, str) or not RUN_NAME.fullmatch(run)
                or not info['start'] or process_start(info['pid']) != info['start']):
            return None
        directory = root / run
        path = directory / name
        if directory.is_symlink() or path.is_symlink() or not path.is_file():
            return None
        return path
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None


class DirectStream:
    def __init__(self, root, web_root='/'):
        self.root = Path(root)
        self.web_root = web_root or '/'
        self.process = None
        self.directory = None
        self.lock = threading.RLock()
        atexit.register(self.stop)

    def active(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None

    @staticmethod
    def command(display, sink, source, directory, web_root='/'):
        if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
            raise ValueError('Configure a local X11 display first')
        if not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*', web_root or ''):
            raise ValueError('Invalid web root for direct stream')
        return ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                '-f', 'x11grab', '-framerate', '10', '-i', display,
                '-f', 'pulse', '-i', sink + '.monitor', '-f', 'pulse', '-i', source,
                '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=longest:normalize=0:weights=0.5 0.5[a]',
                '-map', '0:v:0', '-map', '[a]', '-vf', 'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-tune', 'zerolatency', '-pix_fmt', 'yuv420p',
                '-g', '20', '-keyint_min', '20', '-sc_threshold', '0', '-b:v', '700k',
                '-c:a', 'aac', '-b:a', '96k', '-f', 'hls', '-hls_time', '2', '-hls_list_size', '5',
                '-hls_flags', 'delete_segments+temp_file+independent_segments',
                '-hls_base_url', web_root + 'video.stream_asset.html?_asset=',
                '-hls_segment_filename', str(directory / 'segment_%08d.ts'), str(directory / 'index.m3u8')]

    def start(self, display, session_user):
        with self.lock:
            if self.active():
                raise RuntimeError('Direct stream is already running')
            self.stop()
            sink = Recording.pulse_default('sink', session_user)
            source = Recording.pulse_default('source', session_user)
            self.root.mkdir(mode=0o770, parents=True, exist_ok=True)
            if self.root.is_symlink():
                raise RuntimeError('Stream directory must not be a symlink')
            self.directory = Path(tempfile.mkdtemp(prefix='run-', dir=self.root))
            self.directory.chmod(0o770)
            wrapper = Path(__file__).with_name('recording_encoder.py')
            try:
                command = self.command(display, sink, source, self.directory, self.web_root)
                self.process = subprocess.Popen(audio_session_command(['python3', str(wrapper), *command], session_user),
                                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL, umask=0o027)
                start = process_start(self.process.pid)
                if not start:
                    raise RuntimeError('Could not identify stream process')
                marker = self.root / ('marker-' + self.directory.name)
                marker.write_text(json.dumps({'run': self.directory.name, 'pid': self.process.pid, 'start': start}), encoding='utf-8')
                marker.replace(self.root / 'active.json')
            except Exception:
                self.stop()
                raise

    def stop(self):
        with self.lock:
            process, directory = self.process, self.directory
            marker = self.root / 'active.json'
            try:
                data = json.loads(marker.read_text(encoding='utf-8'))
                if directory is not None and data.get('run') == directory.name:
                    marker.unlink(missing_ok=True)
            except (OSError, ValueError, TypeError):
                pass
            if process and process.poll() is None:
                try:
                    process.stdin.write(b'q\n')
                    process.stdin.flush()
                    process.wait(timeout=15)
                except (OSError, ValueError, subprocess.TimeoutExpired):
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            if process and process.stdin:
                process.stdin.close()
            self.process = None
            self.directory = None
            if directory and directory.parent == self.root and RUN_NAME.fullmatch(directory.name) and not directory.is_symlink():
                for path in directory.iterdir():
                    if not path.is_symlink() and (ASSET_NAME.fullmatch(path.name) or re.fullmatch(r'(?:index\.m3u8|segment_\d{8}\.ts)\.tmp', path.name)):
                        path.unlink(missing_ok=True)
                directory.rmdir()
            return process is not None
