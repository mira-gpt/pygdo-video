import unittest
from unittest.mock import MagicMock, patch

from gdo.video.DesktopOverlay import DesktopOverlay


class DualOutputTest(unittest.TestCase):
    def test_captures_overlay_without_adding_effects_twice(self):
        overlay = DesktopOverlay(screensharing=True)
        overlay.is_running = MagicMock(return_value=True)
        with patch('gdo.video.DesktopOverlay.VideoConnector') as connector:
            overlay.start_virtual_output(':0.0', '/dev/video2')
        connector.return_value.start.assert_called_once_with(':0.0', None, False, True, '/dev/video2')
        self.assertIs(overlay.virtual_output, connector.return_value)

    def test_missing_display_does_not_start_output(self):
        overlay = DesktopOverlay(screensharing=True)
        overlay.is_running = MagicMock(return_value=True)
        with patch('gdo.video.DesktopOverlay.VideoConnector') as connector:
            with self.assertRaises(ValueError):
                overlay.start_virtual_output(None, '/dev/video2')
        connector.assert_not_called()

    def test_stop_also_stops_virtual_camera(self):
        overlay = DesktopOverlay(screensharing=True)
        overlay.virtual_output = MagicMock()
        output = overlay.virtual_output
        overlay.stop()
        output.stop.assert_called_once()
        self.assertIsNone(overlay.virtual_output)
