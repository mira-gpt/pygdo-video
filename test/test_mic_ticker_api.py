import unittest
from unittest.mock import MagicMock, patch

from gdo.base.Application import Application
from gdo.video.method.mic_ticker import queue_ticker
from gdo.video.StarWarsIPC import decode_text


class MicTickerApiTest(unittest.TestCase):
    def test_queue_uses_common_ipc(self):
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.mic_ticker.IPC.send_to_dog') as send:
            queue_ticker('Hello')
        name, args = send.call_args.args
        self.assertEqual('video.ipc_mic_ticker', name)
        self.assertEqual('Hello', decode_text(args[0]))

    def test_defers_in_transaction(self):
        db = MagicMock()
        db.is_in_transaction.return_value = True
        with patch.object(Application, 'db', return_value=db), \
                patch.object(Application, 'defer_after_commit') as defer, \
                patch('gdo.video.method.mic_ticker.IPC.send_to_dog') as send:
            queue_ticker('Hello')
        send.assert_not_called()
        self.assertEqual('video.ipc_mic_ticker', defer.call_args.args[1])
