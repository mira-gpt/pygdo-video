import unittest
from unittest.mock import patch

from gdo.video.module_video import module_video


class VideoConfigTest(unittest.TestCase):
    def test_input_settings(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key):
            fields = {field._name: field for field in module_video().gdo_module_config()}
        self.assertEqual(set(fields), {'video_desktop_url', 'video_file_url',
                                      'video_webcam_url', 'video_output_device',
                                      'video_duck_overlay'})
