"""Bounded FIFO for audience-facing commentary."""
import threading
from collections import deque


class CommentaryTicker:
    _lock = threading.Lock()
    _queue = deque(maxlen=64)
    _current = None
    _sequence = 0

    @classmethod
    def set(cls, text):
        if not isinstance(text, str) or not text.strip() or len(text) > 300 or any(c in text for c in '\r\n\x00'):
            raise ValueError('Invalid commentary')
        with cls._lock:
            cls._sequence += 1
            cls._queue.append((text, cls._sequence))

    @classmethod
    def clear(cls):
        with cls._lock:
            cls._queue.clear()
            cls._current = None

    @classmethod
    def snapshot(cls):
        with cls._lock:
            if cls._current is None and cls._queue:
                cls._current = cls._queue.popleft()
            return cls._current or ('', None)

    @classmethod
    def peek(cls):
        with cls._lock:
            return cls._queue[0][0] if cls._current is not None and cls._queue else ''

    @classmethod
    def finish(cls, sequence):
        with cls._lock:
            if cls._current is None or cls._current[1] != sequence:
                return False
            cls._current = None
            return True
