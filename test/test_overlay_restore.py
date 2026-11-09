import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.ipc_mic import ipc_mic
from gdo.video.method.ipc_duck3d import ipc_duck3d
from gdo.video.module_video import module_video


class OverlayRestoreTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_overlay_choices_are_persisted(self):
        module = MagicMock()
        module.save_config_val = AsyncMock()
        for cls, key in ((ipc_mic, 'video_mic_overlay'), (ipc_duck3d, 'video_duck3d_overlay')):
            handler = cls()
            handler.param_value = MagicMock(return_value=False)
            handler.empty = MagicMock()
            with patch.object(Application, 'IS_DOG', True), patch('gdo.video.module_video.module_video.instance', return_value=module):
                await handler.gdo_execute()
            module.save_config_val.assert_awaited_with(key, '0')

    def test_start_restores_only_selected_overlays(self):
        module = module_video()
        module.connector = MagicMock()
        module.get_config_value = MagicMock(side_effect=lambda key: key == 'video_mic_overlay')
        module.restore_overlays()
        module.connector.microphone_meter.assert_called_once_with(True)
        module.connector.duck3d.assert_not_called()

    def test_cohost_indicator_is_accepted(self):
        from gdo.video.DesktopOverlay import DesktopOverlay
        overlay = DesktopOverlay()
        overlay.live_indicator('cohost')
        self.assertEqual('cohost', overlay.live_mode)
