"""Track sustained exact-zero input without mistaking stale data for mute."""

ZERO_DELAY = 3.0
LANGUAGE_SECONDS = 4.0


def warning_texts():
    from gdo.audio.language import LANGUAGES
    from gdo.base.Trans import Trans
    return [Trans.tiso2(iso, 'video_mic_no_gain') for iso in LANGUAGES]


class MicWarning:
    def __init__(self):
        self.zero_since = None

    def update(self, status, level, now, texts):
        if status != 'on' or level != 0:
            self.zero_since = None
            return None
        if self.zero_since is None:
            self.zero_since = now
        elapsed = now - self.zero_since
        if elapsed < ZERO_DELAY or not texts:
            return None
        return texts[int((elapsed - ZERO_DELAY) // LANGUAGE_SECONDS) % len(texts)]
