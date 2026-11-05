"""Timed ASCII transformation of the current composite frame."""
import time

from PIL import Image, ImageDraw, ImageFont


class AsciiArt:
    CHARACTERS = ' .:-=+*#%@'

    def __init__(self, duration, now=None):
        if not 0 < duration <= 300:
            raise ValueError('Duration must be greater than zero and at most 5 minutes')
        self.deadline = (time.monotonic() if now is None else now) + duration
        try:
            self.font = ImageFont.truetype('DejaVuSansMono.ttf', 10)
        except OSError:
            self.font = ImageFont.load_default()

    def draw(self, frame, now=None):
        if (time.monotonic() if now is None else now) >= self.deadline:
            return False
        width, height = frame.size
        columns, rows = max(1, width // 8), max(1, height // 14)
        pixels = frame.convert('L').resize((columns, rows), Image.Resampling.BILINEAR)
        frame.paste((0, 0, 0), (0, 0, width, height))
        draw = ImageDraw.Draw(frame)
        for y in range(rows):
            for x in range(columns):
                value = pixels.getpixel((x, y))
                char = self.CHARACTERS[value * (len(self.CHARACTERS) - 1) // 255]
                if char != ' ':
                    draw.text((x * width / columns, y * height / rows), char,
                              font=self.font, fill=(220, 240, 220))
        return True
