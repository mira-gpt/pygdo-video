import subprocess
import unittest
from unittest.mock import MagicMock, patch

from gdo.video.YouTubeSender import YouTubeSender


class YouTubeSenderTest(unittest.TestCase):
    def test_lifecycle_and_duplicate_start(self):
        sender = YouTubeSender('/synthetic/sender.py')
        process = MagicMock()
        process.poll.return_value = None
        with patch('pathlib.Path.is_file', return_value=True), patch('subprocess.Popen', return_value=process) as popen:
            sender.start()
            self.assertEqual('running', sender.status())
            with self.assertRaises(RuntimeError):
                sender.start()
            self.assertEqual(1, popen.call_count)
            self.assertTrue(sender.stop())
            process.terminate.assert_called_once()
            process.poll.return_value = 0
            self.assertEqual('exited (0)', sender.status())

    def test_stop_escalates_if_process_does_not_exit(self):
        sender = YouTubeSender()
        sender.process = MagicMock()
        sender.process.poll.return_value = None
        sender.process.wait.side_effect = [subprocess.TimeoutExpired('sender', 8), 0]
        self.assertTrue(sender.stop())
        sender.process.kill.assert_called_once()
        sender.process.poll.return_value = 0
