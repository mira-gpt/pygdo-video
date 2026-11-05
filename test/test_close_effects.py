import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.close import close
from gdo.video.method.ipc_close import ipc_close


class CloseEffectsTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_named_and_all_leave_sources_and_close_resources(self):
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        worker.enabled = {'desktop': True, 'bg_image': True}
        media, other = MagicMock(), MagicMock()
        worker.effects.put('media', media)
        worker.effects.put('vintage', other)
        worker.close_effects('media')
        media.close.assert_called_once()
        self.assertEqual([key for key, _ in worker.effects.ordered()], ['vintage'])
        worker.close_effects('all')
        self.assertEqual(worker.effects.ordered(), [])
        self.assertEqual(worker.enabled, {'desktop': True, 'bg_image': True})

    def test_public_command_and_dog_handler(self):
        command = close()
        command.param_val = MagicMock(return_value='media')
        command.param_value = MagicMock(return_value=False)
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.close.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_close', ['media'])
        command.param_val.return_value = None
        command.param_value.return_value = True
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.close.IPC.send_to_dog') as send:
            self.assertEqual(command.gdo_execute(), 'queued')
        send.assert_called_once_with('video.ipc_close', ['all'])
        handler = ipc_close()
        handler.param_val = MagicMock(return_value='all')
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_close.module_video.instance', return_value=module):
            handler.gdo_execute()
        module.connector.close_effects.assert_called_once_with('all')
