import unittest
from unittest.mock import patch

from gdo.video.module_video import module_video


class VideoConfigTest(unittest.TestCase):
    def test_input_settings(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key):
            fields = {field._name: field for field in module_video().gdo_module_config()}
        self.assertEqual(set(fields), {'video_mode', 'video_desktop_url', 'video_bg_image_url', 'video_overlay_image_url', 'video_file_url',
                                      'video_webcam_url', 'video_output_device',
                                      'video_duck_overlay', 'video_output_preview', 'video_live'})
        self.assertEqual(fields['video_mode'].get_initial(), 'off')
        self.assertEqual(set(fields['video_mode'].init_choices()), {'off', 'composite', 'desktop_overlays'})
        self.assertTrue(all(field.has_tooltip() for field in fields.values()))

    def test_overlay_mode_starts_overlay_not_compositor(self):
        module = module_video()
        with patch.object(module, 'get_config_value', return_value='desktop_overlays'), \
             patch.object(module, 'get_config_val', return_value='/image.png'), \
             patch('gdo.video.module_video.DesktopOverlay') as overlay, \
             patch.object(module.connector, 'start') as compositor:
            module.start_compositor()
        compositor.assert_not_called()
        overlay.return_value.start.assert_called_once_with('/image.png')
