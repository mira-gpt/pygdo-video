"""Brief full-frame television static for the video compositor."""
import time

import numpy as np
from PIL import Image


class TVStatic:
    def __init__(self, duration=.666):
        self.end = time.monotonic() + duration
        self.rng = np.random.default_rng()

    def draw(self, frame, now=None):
        now = time.monotonic() if now is None else now
        if now >= self.end:
            return False
        width, height = frame.size
        noise = self.rng.integers(0, 256, (max(1, height // 3), max(1, width // 3)), dtype=np.uint8)
        image = Image.fromarray(noise, mode='L').resize((width, height), Image.Resampling.NEAREST)
        frame.paste(image.convert(frame.mode))
        return True
