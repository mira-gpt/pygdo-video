import unittest
from unittest.mock import Mock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.video import video


class VideoCommandsTest(unittest.TestCase):
    def test_listing_only_includes_allowed_visible_video_commands(self):
        Application.mode(Mode.render_cli)
        commands = []
        for trigger, module_name, allowed, hidden in (
                ('video.zap', 'video', True, False),
                ('video.secret', 'video', False, False),
                ('video.ipc', 'video', True, True),
                ('audio.mic', 'audio', True, False),
                ('video', 'video', True, False)):
            command = Mock()
            command.gdo_module.return_value.get_name = module_name
            command.gdo_trigger.return_value = trigger
            command.has_permission.return_value = allowed
            command.gdo_method_hidden.return_value = hidden
            command.allows_connector.return_value = True
            commands.append(command)
        loader = Mock()
        loader._methods = {str(i): (lambda command=command: command) for i, command in enumerate(commands)}
        method = video()
        method._env_user = Mock()
        with patch('gdo.core.ModuleCommandList.ModuleLoader.instance', return_value=loader):
            text = method.gdo_execute().render(Mode.render_cli)
        self.assertIn('video.zap', text)
        self.assertNotIn('video.secret', text)
        self.assertNotIn('video.ipc', text)
        self.assertNotIn('audio.mic', text)
