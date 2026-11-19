import os
import unittest

from gdo.base.Application import Application
from gdo.base.ModuleLoader import ModuleLoader
from gdo.video.module_video import module_video
from gdotest.TestUtil import reinstall_module, GDOTestCase, WebPlug, install_module


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

if __name__ == '__main__':
    unittest.main()
