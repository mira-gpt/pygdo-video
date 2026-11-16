import subprocess
import unittest
from unittest.mock import patch

from gdo.video.Monitor import monitor_geometry, capture_input
from gdo.video.DirectStream import DirectStream
from gdo.video.Recording import Recording
from gdo.video.VideoConnector import VideoConnector


class MonitorTest(unittest.TestCase):
    @patch('gdo.video.Monitor.subprocess.run')
    def test_selection_and_missing_monitor(self, run):
        run.return_value.stdout = ('Monitors: 2\n'
            ' 0: +HDMI-A-0 1920/476x1080/267+1920+0 HDMI-A-0\n'
            ' 1: +DisplayPort-0 1920/598x1080/336+0+0 DisplayPort-0\n')
        self.assertEqual((1920, 1080, 1920, 0), monitor_geometry(':0.0', 1))
        self.assertEqual((1920, 1080, 0, 0), monitor_geometry(':0.0', 2))
        with self.assertRaises(ValueError):
            monitor_geometry(':0.0', 3)
        with self.assertRaises(ValueError):
            monitor_geometry(':0.0', 0)

    def test_capture_commands_use_selected_rectangle(self):
        geometry = (1920, 1080, 1920, 0)
        expected = ['-video_size', '1920x1080', '-i', ':0.0+1920,0']
        self.assertEqual(expected, capture_input(':0.0', geometry))
        commands = [VideoConnector.desktop_command(':0.0', geometry),
                    DirectStream.command(':0.0', 'sink', 'source', __import__('pathlib').Path('/tmp'), '/', geometry)]
        with patch('gdo.video.Recording.audio_session_command', side_effect=lambda command, user: command):
            commands.append(Recording.command(':0.0', 'sink', 'source', None, '/tmp/test.mkv', geometry))
        for command in commands:
            i = command.index('-video_size')
            self.assertEqual(expected, command[i:i+4])

    def test_negative_coordinates_fail_closed(self):
        with self.assertRaises(ValueError):
            capture_input(':0', (1920, 1080, -1920, 0))
