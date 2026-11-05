import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.VideoConnector import VideoConnector
from gdo.video.method.ipc_preview import ipc_preview
from gdo.video.method.preview import preview


class PreviewTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_worker_requires_running_compositor(self):
        worker = VideoConnector()
        with self.assertRaises(RuntimeError):
            worker.restart_preview()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        worker.restart_preview()
        self.assertTrue(worker.preview_restart.is_set())

    def test_command_and_handler(self):
        command = preview()
        command.reply = MagicMock(return_value='queued')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.preview.IPC.send_to_dog') as send:
            self.assertEqual('queued', command.gdo_execute())
        send.assert_called_once_with('video.ipc_preview', [])
        handler = ipc_preview()
        handler.empty = MagicMock()
        module = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_preview.module_video.instance', return_value=module):
            handler.gdo_execute()
        module.connector.restart_preview.assert_called_once_with()
