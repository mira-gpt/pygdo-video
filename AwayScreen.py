"""Timed translations and a lightly shaded away screen."""
import time
import textwrap

from PIL import Image, ImageDraw, ImageFont

HEADER = 'The person you have trolled is currently not available'


class AwayScreen:
    def __init__(self, messages, cycle, now=None):
        if (not isinstance(messages, list) or not messages or len(messages) > 256 or
                any(not isinstance(text, str) or not text.strip() or len(text) > 300 for text in messages)):
            raise ValueError('Invalid away messages')
        if isinstance(cycle, bool) or not isinstance(cycle, (int, float)) or not .2 <= cycle <= 300:
            raise ValueError('Invalid away cycle time')
        self.messages = messages
        self.cycle = cycle
        self.started = time.monotonic() if now is None else now

    def current(self, now=None):
        now = time.monotonic() if now is None else now
        return self.messages[int(max(0, now - self.started) / self.cycle) % len(self.messages)]

    def draw(self, frame, now=None):
        shade = Image.new('RGBA', frame.size, (0, 0, 0, 72))
        frame.paste(shade, (0, 0), shade)
        draw = ImageDraw.Draw(frame)
        width, height = frame.size
        try:
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', max(14, width // 30))
            header_font = ImageFont.truetype('DejaVuSans-Bold.ttf', max(10, width // 47))
        except OSError:
            font = header_font = ImageFont.load_default()
        draw.text((width / 2, 16), HEADER, font=header_font, anchor='ma', fill='white', stroke_width=2, stroke_fill='black')
        message = '\n'.join(textwrap.wrap(self.current(now), width=34, break_long_words=True))
        draw.multiline_text((width / 2, height / 2), message, font=font, anchor='mm',
                            align='center', fill='white', stroke_width=2, stroke_fill='black')
        return True
