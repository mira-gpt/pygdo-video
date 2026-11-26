"""Experimental, bounded offline video-to-ASCII event encoder."""
import json
import os
import subprocess
import tempfile
from pathlib import Path

WIDTH, HEIGHT, FPS, MAX_SECONDS = 80, 45, 1, 14400
CHARS = b' .:-=+*#%@'
LUT = bytes(CHARS[value * (len(CHARS) - 1) // 255] for value in range(256))


def encode_video(source, destination):
    source, destination = Path(source), Path(destination)
    if not source.is_absolute() or not destination.is_absolute():
        raise ValueError('Source and output must be absolute paths')
    if source.suffix.lower() != '.mp4' or not source.is_file():
        raise ValueError('Source must be an existing MP4 file')
    if destination.suffix.lower() != '.ibdes':
        raise ValueError('Output must have an .ibdes extension')
    if os.path.lexists(destination):
        raise FileExistsError('Output already exists')
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(source)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=30)
    duration = float(probe.stdout.strip())
    if not 0 < duration <= MAX_SECONDS:
        raise ValueError(f'Video duration must be between 0 and {MAX_SECONDS} seconds')
    result = subprocess.run(
        ['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe', '-i', str(source), '-map', '0:v:0',
         '-vf', f'fps={FPS},scale={WIDTH}:{HEIGHT}', '-pix_fmt', 'gray',
         '-f', 'rawvideo', 'pipe:1'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, timeout=900)
    data = result.stdout
    size = WIDTH * HEIGHT
    if not data or len(data) % size or len(data) // size > MAX_SECONDS * FPS + 1:
        raise ValueError('Video decoding returned invalid or excessive frames')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent,
                                         prefix='.ascii-encode-', delete=False) as out:
            temporary = out.name
            out.write('$video.meta ' + json.dumps({'version': 1, 'width': WIDTH, 'height': HEIGHT,
                                                    'fps': FPS}, separators=(',', ':')) + '\n')
            for index in range(len(data) // size):
                frame = data[index * size:(index + 1) * size].translate(LUT)
                rows = [frame[y * WIDTH:(y + 1) * WIDTH].decode('ascii') for y in range(HEIGHT)]
                out.write('$video ' + json.dumps({'ms': index * 1000 // FPS, 'rows': rows},
                                                  separators=(',', ':')) + '\n')
        # Link without replacing an existing destination, including symlinks.
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            os.unlink(temporary)
    return len(data) // size
