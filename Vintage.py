"""Animated film wear drawn as a keyed compositor layer."""
import random
import time

from PIL import ImageDraw, ImageEnhance


class Vintage:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.scratches = []
        self.last_update = 0.0

    def draw(self, frame, now=None):
        now = time.monotonic() if now is None else now
        width, height = frame.size
        if now - self.last_update >= 0.08:
            self.last_update = now
            self.scratches = [s for s in self.scratches if s[4] > now]
            if self.rng.random() < 0.65:
                x = self.rng.randrange(width)
                y = self.rng.randrange(height)
                length = self.rng.randint(max(1, height // 12), max(1, height * 3 // 4))
                self.scratches.append((x, y, min(height, y + length),
                                       self.rng.randint(120, 230), now + self.rng.uniform(.08, .7)))
            self.scratches = self.scratches[-12:]
        if self.rng.random() < 0.13:
            frame.paste(ImageEnhance.Brightness(frame).enhance(self.rng.uniform(.78, .96)))
        draw = ImageDraw.Draw(frame)
        for x, y1, y2, brightness, expiry in self.scratches:
            draw.line((x, y1, x + self.rng.choice((-1, 0, 0, 1)), y2),
                      fill=(brightness, brightness, int(brightness * .88)), width=1)
        return True
