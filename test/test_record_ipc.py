import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.ipc_record import ipc_record
from gdo.video.method.record import record


class RecordIpcTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    async def test_external_client_queues_action_without_claiming_recording(self):
        method = record()
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock(return_value='requested')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch('gdo.video.method.record.is_running_dog_process', return_value=False), \
             patch.object(Application, 'db', return_value=db), \
             patch('gdo.video.method.record.IPC.send_to_dog') as send:
            self.assertEqual('requested', await method.gdo_execute())
        send.assert_called_once_with('video.ipc_record', ['start'])
        method.reply.assert_called_once_with('video_record_queued', ('start',))

    async def test_ipc_executes_only_in_owning_dog(self):
        method = ipc_record()
        method.param_val = MagicMock(return_value='stop')
        method.empty = MagicMock()
        result = MagicMock()
        result.render.return_value = 'Recording stopped'
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.record.is_running_dog_process', return_value=True), \
             patch('gdo.video.method.ipc_record.IPC.execute_dog_event', new_callable=AsyncMock, return_value=result) as execute, \
             patch('gdo.video.method.ipc_record.Logger.message'):
            await method.gdo_execute()
        execute.assert_awaited_once_with('video.record', ['--enabled=0'])

    async def test_ipc_does_not_requeue_outside_dog(self):
        method = ipc_record()
        method.empty = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.record.is_running_dog_process', return_value=False), \
             patch('gdo.video.method.ipc_record.IPC.execute_dog_event', new_callable=AsyncMock) as execute, \
             patch('gdo.video.method.ipc_record.Logger.warning'):
            await method.gdo_execute()
        execute.assert_not_awaited()
