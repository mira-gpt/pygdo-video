import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.CRTOff import CRTOff, crt_state
from gdo.video.method.off import off


class CRTOffTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_shutdown_black_hold_and_startup(self):
        self.assertEqual((.01, .01, 0.0), crt_state(2.0, 2.0))
        self.assertEqual((.01, .01, 0.0), crt_state(3.5, 2.0))
        self.assertGreater(crt_state(4.3, 2.0)[1], .01)
        self.assertIsNone(crt_state(4.5, 2.0))
        effect = CRTOff(2)
        frame = Image.new('RGB', (100, 80), 'red')
        self.assertTrue(effect.draw(frame, effect.start + 2))
        self.assertEqual((0, 0, 0), frame.getpixel((10, 10)))
        self.assertFalse(effect.draw(frame, effect.start + 4.5))

    def test_command_queues_duration(self):
        method = off()
        method.param_value = MagicMock(return_value=2.0)
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), patch('gdo.video.method.off.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_off', ['2.0'])
        self.assertEqual(2.0, method.gdo_parameters()[0].to_value('2s'))
