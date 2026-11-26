import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gdo.video.AsciiIBDES import HEIGHT, WIDTH, encode_video
from gdo.video.method.al_encode import al_encode
from gdo.base.Application import Application
from gdo.base.Render import Mode


class AsciiIBDESTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg tools unavailable')
    def test_real_short_video(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / 'synthetic.mp4', Path(directory) / 'synthetic.ibdes'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i',
                            'color=white:size=80x48:rate=2:duration=2',
                            '-c:v', 'mpeg4', str(src)], check=True, timeout=20)
            self.assertEqual(2, encode_video(src, dst))
            self.assertEqual(3, len(dst.read_text().splitlines()))

    def test_encodes_frames_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / 'movie.mp4', Path(directory) / 'movie.ibdes'
            src.touch()
            frames = bytes([0]) * (WIDTH * HEIGHT) + bytes([255]) * (WIDTH * HEIGHT)
            with patch('gdo.video.AsciiIBDES.subprocess.run', side_effect=[
                    SimpleNamespace(stdout=b'2.0'), SimpleNamespace(stdout=frames)]):
                self.assertEqual(2, encode_video(src, dst))
            lines = dst.read_text().splitlines()
            self.assertEqual(0o600, os.stat(dst).st_mode & 0o777)
            self.assertEqual('$video.meta ', lines[0][:12])
            first, second = (json.loads(line.removeprefix('$video ')) for line in lines[1:])
            self.assertEqual((0, 1000), (first['ms'], second['ms']))
            self.assertEqual(' ' * WIDTH, first['rows'][0])
            self.assertEqual('@' * WIDTH, second['rows'][0])
            with self.assertRaises(FileExistsError):
                encode_video(src, dst)

    def test_rejects_relative_and_non_mp4_paths(self):
        with self.assertRaises(ValueError):
            encode_video('movie.mp4', '/tmp/movie.ibdes')
        self.assertEqual('video.al.encode', al_encode.gdo_trigger())
        Application.mode(Mode.render_cli)
        self.assertEqual('owner', al_encode().gdo_user_permission())
        self.assertEqual('bash', al_encode().gdo_connectors())

    def test_four_hour_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            src, dst = Path(directory) / 'movie.mp4', Path(directory) / 'movie.ibdes'
            src.touch()
            with patch('gdo.video.AsciiIBDES.subprocess.run', side_effect=[
                    SimpleNamespace(stdout=b'14400'),
                    SimpleNamespace(stdout=bytes(WIDTH * HEIGHT))]):
                self.assertEqual(1, encode_video(src, dst))
            other = Path(directory) / 'too_long.ibdes'
            with patch('gdo.video.AsciiIBDES.subprocess.run', return_value=SimpleNamespace(stdout=b'14400.1')):
                with self.assertRaisesRegex(ValueError, '14400'):
                    encode_video(src, other)
            self.assertFalse(other.exists())
