"""Follow only new assistant commentary in one explicitly configured log."""
import json
import os
import re
import threading
import textwrap
from collections import deque

from gdo.base.Thread import Thread
from gdo.video.CommentaryTicker import CommentaryTicker

MAX_LINE = 1024 * 1024
LIVE_MODES = frozenset(('work', 'show', 'discuss', 'cohost'))
SPEECH_URL = re.compile(
    r'(?i)(?<![\w@])(?:(?:[a-z][a-z0-9+.-]*://|mailto:)[^\s<>\[\]()]+'
    r'|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}'
    r'(?::\d{1,5})?(?:[/?#][^\s<>\[\]()]*)?)'
)
SPEECH_BOLD = re.compile(r'(?<!\*)\*\*([^\s*](?:[^*]*?[^\s*])?)\*\*(?!\*)')
SPEECH_ITALIC = re.compile(r'(?<!\*)\*([^\s*](?:[^*]*?[^\s*])?)\*(?!\*)')


def speech_filter(text, url_phrase, smile_phrase='smile', language='en'):
    """Prepare commentary for speech without changing the visible text."""
    def replace_url(match):
        url = match.group(0)
        suffix = url[len(url.rstrip('.,!?;:')):]
        return url_phrase + suffix
    text = SPEECH_BOLD.sub(r'\1', text)
    text = SPEECH_ITALIC.sub(r'\1', text)
    text = SPEECH_URL.sub(replace_url, text)
    text = re.sub(r'\bpygdo\b', 'PyGDO', text)
    if language == 'de':
        text = re.sub(r'\bdog\b', 'Dock', text, flags=re.IGNORECASE)
    return re.sub(r'\s*:\)\s*', lambda _: f' {smile_phrase} ', text)


def speech_sentences(text):
    """Group sentences into bounded speech-sized chunks."""
    chunk = ''
    for sentence in re.split(r'(?<=[!?])(?=[^!?]|$)|(?<=\.)(?=\s|$)', text):
        for part in textwrap.wrap(sentence.strip(), width=200):
            if chunk and len(chunk) + 1 + len(part) > 200:
                yield chunk
                chunk = ''
            chunk = f'{chunk} {part}' if chunk else part
    if chunk:
        yield chunk


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
        self.audio_enabled = False
        self.audio_url_phrase = 'a link'
        self.audio_smile_phrase = 'smile'
        self.audio_language = 'en'
        self.speech_queue = deque(maxlen=16)
        self.stop_event = threading.Event()
        self.ready = threading.Event()
        self.name = 'video-commentary-follower'

    def set_mode(self, mode):
        with self.mode_lock:
            self.mode = mode
            if mode not in LIVE_MODES:
                CommentaryTicker.clear()
                self.speech_queue.clear()

    def set_audio(self, enabled, url_phrase='a link', smile_phrase='smile', language='en'):
        with self.mode_lock:
            self.audio_enabled = bool(enabled)
            self.audio_url_phrase = url_phrase
            self.audio_smile_phrase = smile_phrase
            self.audio_language = language
            if not self.audio_enabled:
                self.speech_queue.clear()

    def next_speech(self):
        with self.mode_lock:
            if self.audio_enabled and self.mode in LIVE_MODES and self.speech_queue:
                return self.speech_queue.popleft()
            return None

    def announce(self, text):
        """Queue an opted-in announcement through the existing ticker and speech path."""
        with self.mode_lock:
            if not self.audio_enabled or self.mode not in LIVE_MODES or self.stop_event.is_set():
                return False
            for part in textwrap.wrap(text, width=300):
                CommentaryTicker.set(part)
            self.speech_queue.extend(speech_sentences(speech_filter(
                text, self.audio_url_phrase, self.audio_smile_phrase, self.audio_language)))
            return True

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
                                            if self.audio_enabled:
                                                self.speech_queue.extend(speech_sentences(speech_filter(text, self.audio_url_phrase, self.audio_smile_phrase, self.audio_language)))
                                pending, oversized = b'', False
            except OSError:
                self.stop_event.wait(2)
