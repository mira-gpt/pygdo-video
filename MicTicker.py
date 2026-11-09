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
            if cls._current and now - cls._started >= max(6.0, (len(cls._current) * 12 + 202) / 30):
                cls._current = None
            if cls._current is None and cls._queue:
                cls._current = cls._queue.popleft()
                cls._started = now
            return cls._current or '', cls._started
