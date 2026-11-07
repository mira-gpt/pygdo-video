"""Display the local Dog microphone listener's level, not system-wide capture."""
import time
from PIL import Image, ImageDraw
from gdo.video.TranscriptFade import transcript_alpha


class MicrophoneLevel:
    def __init__(self, liveshow=False):
        self.liveshow = liveshow

    def draw(self, frame):
        try:
            from gdo.audio.meter import MicrophoneMeter
            status, level = MicrophoneMeter.snapshot()
            transcription = MicrophoneMeter.transcription_snapshot()
            language = MicrophoneMeter.transcription_language()
            text = MicrophoneMeter.transcription_text_snapshot()
            updated = MicrophoneMeter.transcription_text_timestamp()
        except (ImportError, RuntimeError):
            status, level = 'unknown', 0.0
            transcription = 'unknown'
            language = ''
            text = ''
            updated = 0
        width, height = frame.size
        left, top = max(0, width - 182), max(0, height - 34)
        right = min(width - 1, left + 170)
        draw = ImageDraw.Draw(frame)
        draw.rectangle((left, top, right, min(height - 1, top + 24)), fill=(16, 16, 16),
                       outline=(255, 35, 35) if self.liveshow else (220, 220, 220), width=2 if self.liveshow else 1)
        placeholder = f'STT {language}' if language else 'STT ?'
        label = (text or placeholder) if transcription == 'on' else {'off': '----', 'starting': 'starting...', 'error': 'STT error'}.get(transcription, 'STT ?')
        alpha = transcript_alpha(time.monotonic(), updated) if transcription == 'on' and text else 1.0
        if alpha == 0:
            label, alpha = placeholder, 1.0
        label = label.replace('\n', ' ').replace('\r', ' ').replace('\x00', '')
        text_width = max(1, right - left - 8)
        surface = Image.new('RGBA', (text_width, 13))
        text_draw = ImageDraw.Draw(surface)
        length = text_draw.textlength(label)
        offset = int((time.monotonic() * 30) % (length + 40)) if length > text_width else 0
        text_draw.text((-offset, 0), label, fill=(255, 255, 255, round(255 * alpha)))
        frame.paste(surface, (left + 4, top + 2), surface)
        if status == 'on':
            bar_left, bar_right = left + 4, right - 4
            bar_width = max(0, int((bar_right - bar_left) * min(1.0, level * 100)))
            if bar_width:
                draw.rectangle((bar_left, top + 17, bar_left + bar_width, top + 21), fill=(60, 225, 80))
        return True
