import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.screenshot import capture_screenshot, screenshot


class ScreenshotTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_admin_trigger_and_atomic_unique_file(self):
        command = screenshot()
        self.assertEqual('admin', command.gdo_user_permission())
        self.assertEqual('cheese', command.gdo_trig())
        png = b'\x89PNG\r\n\x1a\nexample'
        with tempfile.TemporaryDirectory() as directory, \
                patch('gdo.video.method.screenshot.subprocess.run', return_value=MagicMock(stdout=png)):
            name = capture_screenshot(':0.0', directory)
            self.assertEqual(png, (Path(directory) / name).read_bytes())
            self.assertEqual(0o644, (Path(directory) / name).stat().st_mode & 0o777)

    def test_capture_failure_does_not_create_file(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('gdo.video.method.screenshot.subprocess.run', side_effect=subprocess.TimeoutExpired('ffmpeg', 15)):
            with self.assertRaises(subprocess.TimeoutExpired):
                capture_screenshot(':0', directory)
            self.assertEqual([], list(Path(directory).iterdir()))

    async def test_response_only_after_capture(self):
        command = screenshot()
        command.reply = MagicMock(return_value='done')
        video = MagicMock()
        video.get_config_val.return_value = ':0.0'
        with patch('gdo.video.method.screenshot.module_video.instance', return_value=video), \
             patch('gdo.video.method.screenshot.capture_screenshot', return_value='cheese-test.png'), \
             patch.object(Application, 'file_path', return_value='/tmp'), \
             patch.object(Application, 'domain', return_value='example.org'), \
             patch.object(Application, 'web_root', return_value='/'), \
             patch.object(Application, 'config', return_value='1'):
            self.assertEqual('done', await command.gdo_execute())
        command.reply.assert_called_once_with('video_screenshot_public', ('https://example.org/gdo/mira/public/cheese-test.png',))
