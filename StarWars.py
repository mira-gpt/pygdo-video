"""A bounded, timed, Star Wars-inspired scrolling text layer."""

import textwrap
import time

from PIL import Image, ImageDraw, ImageFont


class StarWars:
    MAX_LENGTH = 4096
    SPEED = 36.0

    def __init__(self, text, now=None):
        if not isinstance(text, str) or not text.strip() or len(text) > self.MAX_LENGTH:
            raise ValueError(f'Text must contain 1 to {self.MAX_LENGTH} characters')
        self.lines = []
        for line in text.splitlines():
            self.lines.extend(textwrap.wrap(line, width=36, break_long_words=True) or [''])
        self.started = time.monotonic() if now is None else now

    def draw(self, frame, now=None):
        now = time.monotonic() if now is None else now
        width, height = frame.size
        elapsed = max(0, now - self.started)
        scroll = elapsed * self.SPEED
        if scroll > height + (len(self.lines) + 2) * 28:
            return False
        draw = ImageDraw.Draw(frame)
        for i, line in enumerate(self.lines):
            y = height - scroll + i * 28
            if not -40 <= y < height:
                continue
            size = max(10, int(12 + 15 * max(0, y) / height))
            try:
                font = ImageFont.truetype('DejaVuSans-Bold.ttf', size)
            except OSError:
                font = ImageFont.load_default()
            draw.text((width / 2, y), line, fill=(255, 220, 45), font=font,
                      anchor='ma', stroke_width=1, stroke_fill=(0, 0, 0))
        return True
