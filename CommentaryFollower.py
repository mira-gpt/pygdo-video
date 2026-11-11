"""Follow only new assistant commentary in one explicitly configured log."""
import json
import os
import threading
import textwrap

from gdo.base.Thread import Thread
from gdo.video.CommentaryTicker import CommentaryTicker

MAX_LINE = 1024 * 1024
LIVE_MODES = frozenset(('work', 'show', 'discuss', 'cohost'))


def commentary(line):
    try:
        event = json.loads(line)
        payload = event.get('payload', {})
        if event.get('type') != 'response_item' or payload.get('type') != 'message' or payload.get('role') != 'assistant' or payload.get('phase') not in ('commentary', 'final_answer'):
            return None
        parts = payload.get('content', [])
        if not isinstance(parts, list):
            return None
        text = ' '.join(part.get('text', '') for part in parts if isinstance(part, dict) and part.get('type') == 'output_text' and isinstance(part.get('text'), str))
        return ' '.join(text.split()) or None
    except (ValueError, TypeError, AttributeError):
        return None


class CommentaryFollower(Thread):
    def __init__(self, path, mode='off'):
        super().__init__()
        self.path = path
        self.mode = mode
        self.mode_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.name = 'video-commentary-follower'

    def set_mode(self, mode):
        with self.mode_lock:
            self.mode = mode
            if mode not in LIVE_MODES:
                CommentaryTicker.clear()

    def stop(self):
        self.set_mode('off')
        self.stop_event.set()

    def run(self):
        super().run()
        while not self.stop_event.is_set():
            try:
                with open(self.path, 'rb') as stream:
                    stream.seek(0, os.SEEK_END)
                    self.ready.set()
                    pending, oversized = b'', False
                    while not self.stop_event.is_set():
                        chunk = stream.read(65536)
                        if not chunk:
                            current = os.stat(self.path)
                            if current.st_ino != os.fstat(stream.fileno()).st_ino or current.st_size < stream.tell():
                                break  # Reopen at the new end; never replay history.
                            self.stop_event.wait(.25)
                            continue
                        for part in chunk.splitlines(keepends=True):
                            if not oversized:
                                pending += part
                                if len(pending) > MAX_LINE:
                                    pending, oversized = b'', True
                            if part.endswith(b'\n'):
                                if not oversized and (text := commentary(pending)):
                                    with self.mode_lock:
                                        if self.mode in LIVE_MODES and not self.stop_event.is_set():
                                            for part in textwrap.wrap(text, width=300):
                                                CommentaryTicker.set(part)
                                pending, oversized = b'', False
            except OSError:
                self.stop_event.wait(2)
