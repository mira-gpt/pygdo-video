"""Lightweight rendered poses of the 3D duck, with spoken captions."""
import textwrap
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps


class DuckLayer:
    def __init__(self):
        root = Path(__file__).resolve().parent / 'assets' / 'duck'
        with Image.open(root / 'duck-closed.png') as image:
            self.closed = image.convert('RGBA')
        with Image.open(root / 'duck-open.png') as image:
            self.opened = image.convert('RGBA')
        self.speech_id = None
        self.text = ''
        self.caption_text = ''
        self.caption_until = 0
        self._scaled = {}

    def caption(self, text):
        self.caption_text = text
        self.caption_until = time.monotonic() + 8

    def speech_start(self, speech_id, text):
        self.speech_id = speech_id
        self.text = text[:300]

    def speech_end(self, speech_id):
        if self.speech_id == speech_id:
            self.speech_id = None
            self.text = ''

    def draw(self, frame):
        width, height = frame.size
        side = max(1, round(min(width, height) * .42))
        speaking = self.speech_id is not None
        image = self.opened if speaking and int(time.monotonic() * 6) % 2 else self.closed
        key = (side, image is self.opened)
        if key not in self._scaled:
            self._scaled = {k: v for k, v in self._scaled.items() if k[0] == side}
            self._scaled[key] = ImageOps.contain(image, (side, side), Image.Resampling.LANCZOS)
        image = self._scaled[key]
        frame.paste(image, (max(0, width - side - 10), max(0, height - side - 10)), image)
        caption = self.text if speaking else self.caption_text if time.monotonic() < self.caption_until else ''
        if caption:
            draw = ImageDraw.Draw(frame)
            lines = textwrap.wrap(caption, max(12, width // 10))[:4]
            draw.rectangle((10, 10, max(11, width - 10), 20 + 14 * len(lines)), fill=(20, 20, 30))
            draw.multiline_text((15, 15), '\n'.join(lines), fill='white', spacing=3)
        return True
