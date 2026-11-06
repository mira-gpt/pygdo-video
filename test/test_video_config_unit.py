import unittest
from unittest.mock import patch

from gdo.video.module_video import module_video


class VideoConfigTest(unittest.TestCase):
    def test_audio_is_an_optional_friendency(self):
        self.assertIn('audio', module_video().gdo_friendencies())

    def test_input_settings(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key):
            fields = {field._name: field for field in module_video().gdo_module_config()}
        self.assertEqual(set(fields), {'video_mode', 'video_desktop_url', 'video_bg_image_url', 'video_overlay_image_url', 'video_file_url',
                                      'video_webcam_url', 'video_output_device',
                                      'video_duck_overlay', 'video_duck3d_pythonpath', 'video_output_preview', 'video_preview_w', 'video_preview_h', 'video_live'})
        self.assertEqual(fields['video_mode'].get_initial(), 'off')
        self.assertEqual(fields['video_preview_w'].get_initial(), '320')
        self.assertEqual(fields['video_preview_h'].get_initial(), '180')
        self.assertEqual(set(fields['video_mode'].init_choices()), {'off', 'virtualwebcam', 'screensharing'})
        self.assertTrue(all(field.has_tooltip() for field in fields.values()))

    def test_screensharing_uses_full_desktop_overlay(self):
        module = module_video()
        with patch.object(module, 'get_config_value', return_value='screensharing'), \
             patch.object(module, 'get_config_val', return_value='/image.png'), \
             patch('gdo.video.module_video.DesktopOverlay') as overlay:
            module.start_compositor()
        overlay.assert_called_once_with(screensharing=True)
        overlay.return_value.start.assert_called_once_with('/image.png')

    def test_screensharing_does_not_use_composite_background(self):
        module = module_video()
        with patch.object(module, 'get_config_value', return_value='screensharing'), \
             patch.object(module, 'get_config_val', return_value='/overlay.png') as config, \
             patch('gdo.video.module_video.DesktopOverlay') as overlay:
            module.start_compositor()
        config.assert_any_call('video_overlay_image_url')
        self.assertNotIn('video_bg_image_url', [call.args[0] for call in config.call_args_list])
        overlay.return_value.start.assert_called_once_with('/overlay.png')
        with self.assertRaises(ValueError):
            from gdo.video.DesktopOverlay import DesktopOverlay
            DesktopOverlay().set_layer('bg_image', True)
