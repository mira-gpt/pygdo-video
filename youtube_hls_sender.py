"""Experimental YouTube HLS sender; secrets stay out of process arguments.

Run with --self-test for an offline synthetic video/audio encoding check.
Live mode reads the private HLS URL from /home/mira/data/youtube-streaming.nf0.
"""
import http.client
import fcntl
import os
import re
import secrets
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit


def validate_url(value):
    value = value.strip()
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or parsed.hostname != 'a.upload.youtube.com'
            or parsed.username or parsed.password or parsed.fragment
            or parsed.path != '/http_upload_hls' or not parsed.query.endswith('file=')
            or 'cid=' not in parsed.query):
        raise ValueError('Invalid primary YouTube HLS URL')
    return parsed


def command(directory, prefix, synthetic=False):
    video = (['-f', 'lavfi', '-i', 'testsrc=size=640x360:rate=15'] if synthetic else
             ['-f', 'v4l2', '-framerate', '15', '-video_size', '640x360', '-i', '/dev/video2'])
    if synthetic:
        session, audio = [], ['-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                              '-map', '1:a:0']
    else:
        session = ['sudo', '-n', '-u', 'gizmore', '--', 'env', 'XDG_RUNTIME_DIR=/run/user/1000']
        audio = ['-f', 'pulse', '-i', 'alsa_output.pci-0000_04_00.6.analog-stereo.monitor',
                 '-f', 'pulse', '-i', 'alsa_input.usb-SteelSeries_Arctis_Nova_7-00.mono-fallback',
                 '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=longest:normalize=0:weights=0.5 0.5[a]',
                 '-map', '[a]']
    return [*session, 'ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', *video,
            *audio, '-map', '0:v:0', '-c:v', 'libx264', '-preset', 'veryfast',
            '-pix_fmt', 'yuv420p', '-g', '15', '-keyint_min', '15', '-sc_threshold', '0',
            '-flags', '+cgop', '-c:a', 'aac', '-b:a', '128k', '-shortest',
            '-f', 'hls', '-hls_time', '1', '-hls_list_size', '3', '-hls_delete_threshold', '15',
            '-hls_flags', 'delete_segments+temp_file',
            '-hls_segment_filename', str(directory / (prefix + '_%06d.ts')),
            str(directory / 'stream.m3u8')]


def validate_playlist(data, prefix):
    text = data.decode('utf8')
    if not text.startswith('#EXTM3U\n'):
        raise ValueError('Invalid HLS playlist')
    names = [line.strip() for line in text.splitlines() if line and not line.startswith('#')]
    if not names or len(names) > 3 or any(not re.fullmatch(re.escape(prefix) + r'_\d{6}\.ts', name) for name in names):
        raise ValueError('Invalid HLS segment names')
    return names


def main():
    synthetic = sys.argv[1:] == ['--self-test']
    if sys.argv[1:] and not synthetic:
        raise SystemExit('Use no argument for live mode, or --self-test')
    parsed = None
    lock = None
    if not synthetic:
        lock = open('/home/mira/data/youtube_hls_sender.lock', 'a')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit('Another HLS sender is already running')
        secret = Path('/home/mira/data/youtube-streaming.nf0')
        if secret.stat().st_mode & 0o077:
            raise SystemExit('HLS URL file must be private (mode 600)')
        url = next((line.split(':', 1)[1].strip() for line in secret.read_text(encoding='utf8').splitlines()
                    if line.lower().startswith('url:')), '')
        parsed = validate_url(url)
    done = False
    def stop(*_):
        nonlocal done
        done = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    prefix = 'seg_' + secrets.token_hex(8)
    with tempfile.TemporaryDirectory(prefix='mira-hls-') as temp:
        directory = Path(temp)
        if not synthetic:
            # The authorized desktop session user runs the capture process;
            # both users share the private gizmore group.
            os.chmod(directory, 0o770)
        process = subprocess.Popen(command(directory, prefix, synthetic), stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
        connection = None
        sent = set()
        last_playlist = b''
        start = time.monotonic()
        try:
            if parsed:
                connection = http.client.HTTPSConnection(parsed.hostname, parsed.port or 443, timeout=10)
            while not done and time.monotonic() - start < (15 if synthetic else 3600):
                if process.poll() is not None:
                    raise RuntimeError('Encoder exited unexpectedly')
                playlist = directory / 'stream.m3u8'
                if playlist.exists():
                    data = playlist.read_bytes()
                    names = validate_playlist(data, prefix)
                    if synthetic:
                        print('Offline HLS encoding succeeded:', len(names), 'segment(s)', flush=True)
                        return
                    if data != last_playlist:
                        try:
                            pending = [(name, (directory / name).read_bytes()) for name in names if name not in sent]
                        except FileNotFoundError:
                            # The playlist advanced while being read; retry the latest snapshot.
                            time.sleep(.2)
                            continue
                        def upload(name, content, content_type):
                            connection.request('PUT', parsed.path + '?' + parsed.query + name, body=content,
                                               headers={'Content-Type': content_type,
                                                        'User-Agent': 'Mira/PyGDO-HLS/0.1'})
                            response = connection.getresponse()
                            response.read()
                            if response.status not in (200, 202):
                                raise RuntimeError('YouTube rejected HLS upload (HTTP %d)' % response.status)
                        upload('stream.m3u8', data, 'application/vnd.apple.mpegurl')
                        for name, content in pending:
                            upload(name, content, 'video/mp2t')
                            sent.add(name)
                        last_playlist = data
                        sent.intersection_update(names)
                        print('HLS playlist and segments acknowledged', flush=True)
                time.sleep(.2)
            if synthetic:
                raise RuntimeError('No local HLS segments produced')
        finally:
            if connection:
                connection.close()
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as error:
        # Never print URLs or exception details which can contain credentials.
        print('HLS sender failed:', type(error).__name__, flush=True)
        raise SystemExit(1)
