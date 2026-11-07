import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.duckevent import duckevent
from gdo.video.method.off import off
from gdo.video.method.zap import zap


class AnimationReplyTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_queue_replies_depend_on_dog_mode(self):
        db = MagicMock()
        db.is_in_transaction.return_value = False
        for cls, parameter, value, expected in (
            (off, 'param_value', 2, 'video_off_queued'),
            (zap, 'param_value', .5, 'video_zap_queued'),
            (duckevent, 'param_val', 'lol', 'video_duckevent_queued'),
        ):
            for dog in (True, False):
                with self.subTest(method=cls.__name__, dog=dog):
                    method = cls()
                    setattr(method, parameter, MagicMock(return_value=value))
                    method.empty = MagicMock(return_value='')
                    method.reply = MagicMock(return_value='queued')
                    with patch.object(Application, 'IS_DOG', dog), \
                            patch.object(Application, 'db', return_value=db), \
                            patch('gdo.base.IPC.IPC.send_to_dog') as send:
                        result = method.gdo_execute()
                    self.assertEqual('' if dog else 'queued', result)
                    send.assert_called_once()
                    if dog:
                        method.reply.assert_not_called()
                    else:
                        method.reply.assert_called_once_with(expected)

    def test_queue_failure_is_not_silenced(self):
        method = zap()
        method.param_value = MagicMock(return_value=.5)
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'IS_DOG', True), \
                patch.object(Application, 'db', return_value=db), \
                patch('gdo.base.IPC.IPC.send_to_dog', side_effect=RuntimeError('failure')):
            with self.assertRaisesRegex(RuntimeError, 'failure'):
                method.gdo_execute()
