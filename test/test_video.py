import os
import unittest

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdo.video.module_video import module_video
from gdotest.TestUtil import cli_plug, reinstall_module, cli_gizmore, GDOTestCase, WebPlug, install_module, web_plug


class module_video_Test(GDOTestCase):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.init(os.path.dirname(__file__ + "/../../../../"))
        loader = ModuleLoader.instance()
        install_module('video')
        loader.load_modules_db(True)
        WebPlug.COOKIES = {}
        Application.init_cli()
        loader.init_modules(True, True)
        loader.init_cli()

    def test_00_reinstall(self):
        reinstall_module('video')
        self.assertIs(type(module_video.instance()), module_video, "Cannot re-install module video.")

    def test_03_overview_cli(self):
        giz =  cli_gizmore()
        out = cli_plug(giz, "$video.overview")
        self.assertIsNotNone(out, '$video.overview does not work.')

    def test_02_overview_web(self):
        giz =  cli_gizmore()
        out = web_plug("video.overview.html")
        self.assertIsNotNone(out, 'video.overview.html does not work.')


if __name__ == '__main__':
    unittest.main()
