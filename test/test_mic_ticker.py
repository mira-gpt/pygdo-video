import unittest
from collections import deque
from unittest.mock import MagicMock

from gdo.video.MicTicker import MicTicker, TickerScroll, ticker_finished, ticker_offset


class MicTickerTest(unittest.TestCase):
    def setUp(self):
        MicTicker._queue = deque()
        MicTicker._current = None
        MicTicker._started = 0

    def tearDown(self):
        MicTicker._queue.clear()
        MicTicker._current = None
        MicTicker._started = 0

    def test_fifo_waits_for_renderer_and_ignores_stale_acknowledgements(self):
        MicTicker.enqueue('first')
        MicTicker.enqueue('second')
        self.assertEqual(('first', 10), MicTicker.snapshot(10))
        self.assertEqual('first', MicTicker.snapshot(15)[0])
        self.assertEqual('first', MicTicker.snapshot(100)[0])
        self.assertFalse(MicTicker.finish(9))
        self.assertTrue(MicTicker.finish(10))
        self.assertEqual(('second', 101), MicTicker.snapshot(101))
        self.assertFalse(MicTicker.finish(10))
        self.assertTrue(MicTicker.finish(101))
        self.assertEqual('', MicTicker.snapshot(102)[0])

    def test_real_rendered_width_controls_completion(self):
        self.assertEqual(0, ticker_offset(10, 12))
        self.assertFalse(ticker_finished(10, 16, 180))
        self.assertTrue(ticker_finished(10, 18, 180))
        self.assertFalse(ticker_finished(10, 16, 700))
        self.assertTrue(ticker_finished(10, 36, 700))

    def test_render_pause_does_not_skip_unseen_text(self):
        scroll = TickerScroll()
        self.assertEqual((0, False), scroll.frame(10, 10, 200))
        self.assertEqual((0, False), scroll.frame(10, 100, 200))
        for i in range(1, 45):
            offset, finished = scroll.frame(10, 100 + i * .2, 200)
        self.assertTrue(finished)
        self.assertGreaterEqual(offset, 200)
        self.assertEqual((0, False), scroll.frame(11, 110, 200))

    def test_invalid_and_bounded(self):
        for text in ('', ' ', 'bad\ntext', 'a' * 301):
            with self.assertRaises(ValueError):
                MicTicker.enqueue(text)
        for _ in range(MicTicker.MAX_PENDING):
            MicTicker.enqueue('ok')
        with self.assertRaises(ValueError):
            MicTicker.enqueue('one too many')

    def test_desktop_ack_advances_only_matching_item(self):
        from gdo.video.DesktopOverlay import DesktopOverlay
        MicTicker.enqueue('one')
        MicTicker.enqueue('two')
        self.assertEqual(('one', 10), MicTicker.snapshot(10))
        process = MagicMock()
        process.stdout = [b'not json\n', b'{"event":"ticker_finished","started":9}\n',
                          b'{"event":"ticker_finished","started":10}\n']
        DesktopOverlay()._read_overlay_events(process)
        self.assertEqual(('two', 11), MicTicker.snapshot(11))
