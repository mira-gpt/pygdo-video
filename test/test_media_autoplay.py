import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.video.method.ipc_media import ipc_media
from gdo.video.method.media import media


class MediaAutoplayTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_default_is_off(self):
        with patch('gdo.ui.WithIcon.t', side_effect=lambda key: key):
            fields = {field.get_name(): field for field in media().gdo_parameters()}
        self.assertEqual('0', fields['autoplay'].get_initial())

    async def test_flag_reaches_desktop_window(self):
        command = ipc_media()
        values = {'url': 'https://example.org/video.mp4', 'width': '25%',
                  'height': '25%', 'x': '2%', 'y': '2%', 'transition': 'fade'}
        command.param_val = MagicMock(side_effect=values.get)
        command.param_value = MagicMock(return_value=True)
        command.empty = MagicMock(return_value=None)
        connector = DesktopOverlay()
        connector.show_web_media = MagicMock()
        module = MagicMock()
        module.connector = connector
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_media.module_video.instance', return_value=module):
            await command.gdo_execute()
        self.assertTrue(connector.show_web_media.call_args.kwargs['autoplay'])
