import unittest
from unittest.mock import MagicMock, patch

from gdo.video.connector.Video import Video
from gdo.video.module_video import module_video


class VideoConnectorLifecycleTest(unittest.IsolatedAsyncioTestCase):
    async def test_install_creates_one_video_server(self):
        module = module_video()
        with patch('gdo.video.module_video.GDO_Server.get_by_connector', side_effect=[None, object()]), \
             patch('gdo.video.module_video.GDO_Server.blank') as blank:
            await module.gdo_install()
            await module.gdo_install()
        blank.assert_called_once_with({'serv_name': 'Video', 'serv_connector': 'video'})
        blank.return_value.insert.assert_called_once()

    async def test_disabled_outputs_do_not_start_compositor(self):
        module = MagicMock()
        module.get_config_value.return_value = 'off'
        with patch.object(module_video, 'instance', return_value=module):
            connector = Video()
            self.assertTrue(await connector.gdo_connect())
        module.start_compositor.assert_not_called()


if __name__ == '__main__':
    unittest.main()
