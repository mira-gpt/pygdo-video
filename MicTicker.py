"""Bounded, process-local FIFO shared by microphone overlay producers."""
import threading
import time
from collections import deque


class MicTicker:
    _lock = threading.Lock()
    _queue = deque()
    _current = None
    _started = 0.0
    MAX_PENDING = 64

    @classmethod
    def enqueue(cls, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 300 or any(c in text for c in '\r\n\x00'):
            raise ValueError('Invalid ticker text')
        with cls._lock:
            if len(cls._queue) >= cls.MAX_PENDING:
                raise ValueError('Ticker queue is full')
            cls._queue.append(text)

    @classmethod
    def snapshot(cls, now=None):
        now = time.monotonic() if now is None else now
        with cls._lock:
            if cls._current is None and cls._queue:
                cls._current = cls._queue.popleft()
                cls._started = now
            return cls._current or '', cls._started

    @classmethod
    def finish(cls, started):
        """Advance only on a renderer acknowledgement for the current item."""
        with cls._lock:
            if cls._current is None or started != cls._started:
                return False
            cls._current = None
            return True


def ticker_offset(started, now):
    """Give readers two seconds before moving left at 30 pixels/second."""
    return max(0.0, now - started - 2.0) * 30.0


def ticker_finished(started, now, rendered_width):
    return now - started >= 6.0 and ticker_offset(started, now) >= rendered_width


class TickerScroll:
    """Count rendered time, not time spent with a stopped/hidden renderer."""
    def __init__(self):
        self.started = None
        self.last_frame = None
        self.elapsed = 0.0

    def frame(self, started, now, rendered_width):
        if started != self.started:
            self.started, self.last_frame, self.elapsed = started, now, 0.0
        else:
            delta = max(0.0, now - self.last_frame)
            # A gap means rendering stopped; do not skip an unseen section.
            if delta <= .5:
                self.elapsed += delta
            self.last_frame = now
        return ticker_offset(0, self.elapsed), ticker_finished(0, self.elapsed, rendered_width)
