import unittest
from collections import deque

from gdo.video.MicTicker import MicTicker


class MicTickerTest(unittest.TestCase):
    def setUp(self):
        MicTicker._queue = deque()
        MicTicker._current = None
        MicTicker._started = 0

    def tearDown(self):
        MicTicker._queue.clear()
        MicTicker._current = None
        MicTicker._started = 0

    def test_fifo_and_expiry(self):
        MicTicker.enqueue('first')
        MicTicker.enqueue('second')
        self.assertEqual(('first', 10), MicTicker.snapshot(10))
        self.assertEqual('first', MicTicker.snapshot(15)[0])
        self.assertEqual(('second', 19), MicTicker.snapshot(19))
        self.assertEqual('', MicTicker.snapshot(100)[0])

    def test_invalid_and_bounded(self):
        for text in ('', ' ', 'bad\ntext', 'a' * 301):
            with self.assertRaises(ValueError):
                MicTicker.enqueue(text)
        for _ in range(MicTicker.MAX_PENDING):
            MicTicker.enqueue('ok')
        with self.assertRaises(ValueError):
            MicTicker.enqueue('one too many')
