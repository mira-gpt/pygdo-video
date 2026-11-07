import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.TVStatic import TVStatic
from gdo.video.method.zap import zap
from gdo.video.method.ipc_zap import ipc_zap


class ZapTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_static_is_temporary_and_changes_frame(self):
        effect = TVStatic()
        frame = Image.new('RGB', (96, 64))
        self.assertTrue(effect.draw(frame, effect.end - .5))
        self.assertGreater(len(set(frame.getdata())), 10)
        self.assertFalse(effect.draw(frame, effect.end))

    def test_command_queues(self):
        method = zap()
        method.reply = MagicMock()
        method.param_value = MagicMock(return_value=None)
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.zap.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_zap', ['0.666'])

    def test_duration_field_accepts_seconds_and_milliseconds(self):
        field = zap().gdo_parameters()[0]
        self.assertAlmostEqual(.666, field.to_value('666ms'))
        self.assertEqual(12, field.to_value('12s'))

    async def test_ipc_uses_configured_audio_sink(self):
        connector = MagicMock()
        module = MagicMock()
        module.cfg_output_device.return_value = 'test_sink'
        process = MagicMock()
        process.wait = AsyncMock(return_value=0)
        method = ipc_zap()
        method.param_value = MagicMock(return_value=1.25)
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_zap.module_video.instance', return_value=MagicMock(connector=connector)), \
                patch('gdo.video.method.ipc_zap.module_audio.instance', return_value=module), \
                patch('gdo.video.method.ipc_zap.asyncio.create_subprocess_exec', new=AsyncMock(return_value=process)) as spawn:
            await method.gdo_execute()
        connector.zap.assert_called_once_with(1.25)
        self.assertIn('test_sink', spawn.call_args.args)
        self.assertIn('anoisesrc=color=white:amplitude=0.08:duration=1.25', spawn.call_args.args)
