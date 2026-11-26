import unittest
from unittest.mock import MagicMock

from gdo.ui.IconUTF8 import IconUTF8
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.module_video import module_video


class StreamSidebarIconTest(unittest.TestCase):
    def test_tv_icon_is_available_and_used(self):
        Application.mode(Mode.render_cli)
        module = module_video()
        module.get_config_value = MagicMock(return_value=True)
        module.href = MagicMock(return_value='/stream')
        page = MagicMock()
        module.gdo_init_sidebar(page)
        link = page._left_bar.add_field.call_args.args[0]
        self.assertEqual('tv', link._icon_name)
        self.assertEqual('📺', IconUTF8.MAP()['tv'])
