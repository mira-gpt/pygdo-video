"""Audience-facing commentary panel, independent of the microphone meter."""
import time
from PIL import Image, ImageDraw, ImageFont
from gdo.video.CommentaryTicker import CommentaryTicker
from gdo.video.TickerLayout import ticker_bounds, next_message_x, COMMENTARY_SPEED, commentary_speed
from gdo.video.MicTicker import TickerScroll


class ThoughtsLayer:
    def __init__(self, live_mode='off'):
        self.live_mode = live_mode
        self.text = ''
        self.started = 0.0
        self.scroll = TickerScroll(COMMENTARY_SPEED)
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 10)
        except OSError:
            self.font = ImageFont.load_default()

    def draw(self, frame):
        width, height = frame.size
        left, _ = ticker_bounds(width)
        right, top = max(12, left - 8), max(0, height - 34)
        available = max(0, right - 20)
        if not available:
            return True
        text, sequence = CommentaryTicker.snapshot() if self.live_mode in ('work', 'show', 'discuss', 'cohost') else ('', None)
        text = text or 'Mira: ...'
        now = time.monotonic()
        if text != self.text:
            self.text, self.started = text, now
        draw = ImageDraw.Draw(frame)
        draw.rectangle((12, top, right, min(height - 1, top + 24)), fill=(16, 16, 16))
        surface = Image.new('RGBA', (available, 13))
        painter = ImageDraw.Draw(surface)
        length = painter.textlength(text, font=self.font)
        self.scroll.speed = commentary_speed(CommentaryTicker.pending_count()) if sequence is not None else COMMENTARY_SPEED
        self.scroll.min_duration = 6.0 * COMMENTARY_SPEED / self.scroll.speed
        offset, done = self.scroll.frame(sequence, now, length) if sequence is not None else (0, False)
        offset = int(offset)
        painter.text((-offset, 0), text, font=self.font, fill=(255, 255, 255, 255))
        if sequence is not None and (next_text := CommentaryTicker.peek()):
            separator = ' || '
            separator_width = painter.textlength(separator, font=self.font)
            x = next_message_x(available, length, offset, self.scroll.elapsed, separator_width)
            painter.text((int(x - separator_width), 0), separator, font=self.font, fill=(255, 255, 255, 255))
            painter.text((int(x), 0), next_text, font=self.font, fill=(255, 255, 255, 255))
        frame.paste(surface, (16, top + 2), surface)
        if done:
            CommentaryTicker.finish(sequence)
        return True
