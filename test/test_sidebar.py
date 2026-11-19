import unittest
from unittest.mock import MagicMock, patch

from gdo.video.module_video import module_video


class VideoSidebarTest(unittest.TestCase):
    def test_sidebar_keeps_stream_without_overview(self):
        module = module_video()
        page = MagicMock()
        link = MagicMock()
        link.href.return_value = link
        link.text.return_value = link
        link.attr.return_value = link
        with patch.object(module_video, 'href', side_effect=lambda method: '/' + method), \
             patch('gdo.video.module_video.GDT_Link', return_value=link):
            module.gdo_init_sidebar(page)
        page._left_bar.add_field.assert_called_once_with(link)
        link.href.assert_called_once_with('/stream')
        link.attr.assert_called_once_with('data-video-stream-status', '/stream_status')


if __name__ == '__main__':
    unittest.main()
