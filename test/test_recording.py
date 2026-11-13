import subprocess
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gdo.video.LiveIndicator import indicator_text
from gdo.video.Recording import Recording


class RecordingTest(unittest.TestCase):
    def test_indicator_alternates_only_while_recording(self):
        self.assertEqual('cohost', indicator_text('cohost', False, 3))
        self.assertEqual('Mira', indicator_text('cohost', False, 3, 'Mira'))
        self.assertEqual('● REC', indicator_text('show', True, 2, 'Gizmore'))
        self.assertEqual('cohost', indicator_text('cohost', True, 0))
        self.assertEqual('● REC', indicator_text('cohost', True, 2))
        self.assertEqual('cohost', indicator_text('cohost', True, 4))

    def test_command_captures_two_audio_sources_without_network(self):
        command = Recording.command(':0.0', 'speakers', 'microphone', None, '/tmp/example.mkv')
        self.assertIn('speakers.monitor', command)
        self.assertIn('microphone', command)
        self.assertIn('[1:a][2:a]amix=inputs=2:duration=longest:normalize=0:weights=0.5 0.5[a]', command)
        self.assertEqual('/tmp/example.mkv', command[-1])
        with self.assertRaises(ValueError):
            Recording.command('remote:0', 'speakers', 'microphone', None, '/tmp/example.mkv')

    def test_private_recording_lifecycle_and_duplicate_start(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = Recording(Path(directory) / 'recordings')
            process = MagicMock()
            process.poll.return_value = None
            process.returncode = 0
            original_popen = subprocess.Popen
            def start_process(command, *args, **kwargs):
                if command[0] == 'python3' and 'recording_encoder.py' in command[1]:
                    return process
                return original_popen(command, *args, **kwargs)
            with patch.object(recorder, 'pulse_default', side_effect=['speakers', 'microphone']), \
                    patch.object(recorder, 'remux') as remux, \
                    patch('gdo.video.Recording.subprocess.Popen', side_effect=start_process):
                path = recorder.start(':0.0', None)
                self.assertTrue(path.is_file())
                self.assertEqual(0o600, path.stat().st_mode & 0o777)
                self.assertEqual(0o700, path.parent.stat().st_mode & 0o777)
                with self.assertRaises(RuntimeError):
                    recorder.start(':0.0', None)
                self.assertTrue(recorder.stop())
                remux.assert_called_once()
                process.stdin.write.assert_called_once_with(b'q\n')
                self.assertFalse(recorder.active())
                self.assertFalse(recorder.stop())

    def test_bad_encoder_exit_is_not_reported_as_saved(self):
        recorder = Recording()
        process = MagicMock()
        process.poll.return_value = 1
        process.returncode = 1
        recorder.process = process
        with self.assertRaisesRegex(RuntimeError, 'incomplete'):
            recorder.stop()

    def test_failed_stop_keeps_running_process_visible(self):
        recorder = Recording()
        process = MagicMock()
        process.poll.return_value = None
        process.stdin.write.side_effect = BrokenPipeError()
        process.terminate.side_effect = PermissionError()
        recorder.process = process
        with self.assertRaisesRegex(RuntimeError, 'still be running'):
            recorder.stop()
        self.assertTrue(recorder.active())
        recorder.process = None

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_synthetic_recording_can_be_finalized(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = Recording(Path(directory) / 'recordings')
            command = ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                       '-re', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=5',
                       '-f', 'lavfi', '-i', 'sine=frequency=440',
                       '-f', 'lavfi', '-i', 'sine=frequency=880',
                       '-filter_complex', '[1:a][2:a]amix=inputs=2:duration=longest:normalize=0:weights=0.5 0.5[a]',
                       '-map', '0:v:0', '-map', '[a]',
                       '-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p',
                       '-c:a', 'aac', '-f', 'matroska']
            with patch.object(recorder, 'pulse_default', side_effect=['output', 'mic']), \
                    patch.object(recorder, 'command', side_effect=lambda *args: command + ['-y', str(args[-1])]):
                path = recorder.start(':0.0', None)
                try:
                    time.sleep(1.5)
                finally:
                    recorder.stop()
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type',
                                     '-of', 'csv=p=0', str(path)], capture_output=True, text=True, check=True)
            self.assertIn('video', result.stdout)
            self.assertIn('audio', result.stdout)
            mp4 = path.with_suffix('.mp4')
            self.assertTrue(mp4.is_file())
            self.assertEqual(0o600, mp4.stat().st_mode & 0o777)
            result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_name',
                                     '-of', 'csv=p=0', str(mp4)], capture_output=True, text=True, check=True)
            self.assertIn('h264', result.stdout)
            self.assertIn('aac', result.stdout)
            self.assertTrue(path.is_file())

    def test_remux_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = Recording()
            recorder.path = Path(directory) / 'recording.mkv'
            recorder.path.write_bytes(b'original')
            with self.assertRaisesRegex(RuntimeError, 'original recording retained'):
                recorder.remux()
            self.assertEqual(b'original', recorder.path.read_bytes())
            self.assertFalse(recorder.path.with_suffix('.mp4').exists())
            self.assertEqual([recorder.path], list(Path(directory).iterdir()))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_encoder_stops_if_control_pipe_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.mkv'
            wrapper = Path(__file__).resolve().parents[1] / 'recording_encoder.py'
            command = ['python3', str(wrapper), 'ffmpeg', '-hide_banner', '-loglevel', 'error',
                       '-re', '-f', 'lavfi', '-i', 'testsrc2=size=160x90:rate=5',
                       '-c:v', 'libx264', '-threads', '1', '-pix_fmt', 'yuv420p', str(path)]
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            try:
                time.sleep(1.5)
                process.stdin.close()
                self.assertEqual(0, process.wait(timeout=15))
                subprocess.run(['ffprobe', '-v', 'error', str(path)], check=True)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    unittest.main()
