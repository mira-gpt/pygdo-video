import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.youtube import youtube


class YouTubeSetupTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)
        self.method = youtube()
        self.method.param_val = MagicMock(return_value='start')
        self.method.reply = MagicMock()
        self.method.err = MagicMock()
        self.module = MagicMock()
        self.module.get_config_val.return_value = '/dev/video2'
        self.module.connector.is_running.side_effect = [False, True]

    def test_start_prepares_video_before_sender(self):
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.youtube.module_video.instance', return_value=self.module), \
             patch('gdo.video.method.youtube.VideoConnector.validate_output'), \
             patch('gdo.video.method.youtube.VideoConnector.virtual_camera_allowed', return_value=True):
            self.method.gdo_execute()
        self.module.youtube_sender.preflight.assert_called_once()
        self.module.start_compositor.assert_called_once_with(mode_override='screensharing', live_override=True)
        self.module.youtube_sender.start.assert_called_once()

    def test_failure_rolls_back_worker_started_here(self):
        self.module.youtube_sender.start.side_effect = RuntimeError('failed')
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.youtube.module_video.instance', return_value=self.module), \
             patch('gdo.video.method.youtube.VideoConnector.validate_output'), \
             patch('gdo.video.method.youtube.VideoConnector.virtual_camera_allowed', return_value=True):
            self.method.gdo_execute()
        self.module.connector.stop.assert_called_once()
        self.method.err.assert_called_once()

    def test_mismatched_device_does_not_start(self):
        self.module.get_config_val.return_value = '/dev/video4'
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.youtube.module_video.instance', return_value=self.module):
            self.method.gdo_execute()
        self.module.start_compositor.assert_not_called()
        self.module.youtube_sender.start.assert_not_called()
