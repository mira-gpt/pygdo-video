"""Live duck source as a composite-frame layer."""
import textwrap
import time

from PIL import ImageDraw, ImageOps

from gdo.video.Duck3DSource import Duck3DSource
from gdo.video.DuckLayer import DuckLayer


class Duck3DLayer(DuckLayer):
    def __init__(self, source=None):
        super().__init__()
        self.source = source or Duck3DSource()

    def animation(self, mode):
        self.source.update(mode=mode)

    def speech_start(self, speech_id, text):
        super().speech_start(speech_id, text)
        self.source.update(speaking=True)

    def speech_envelope(self, levels, step_ms):
        self.source.update(envelope=levels, step_ms=step_ms)

    def speech_end(self, speech_id):
        if self.speech_id == speech_id:
            super().speech_end(speech_id)
            self.source.update(speaking=False)

    def draw(self, frame):
        image = self.source.snapshot()
        if image is None:
            return super().draw(frame)
        width, height = frame.size
        side = max(1, round(min(width, height) * .42))
        image = ImageOps.contain(image, (side, side))
        frame.paste(image, (max(0, width - side - 10), max(0, height - side - 40)), image)
        caption = self.text if self.speech_id else self.caption_text if time.monotonic() < self.caption_until else ''
        if caption:
            draw = ImageDraw.Draw(frame)
            lines = textwrap.wrap(caption, max(12, width // 10))[:4]
            draw.rectangle((10, 10, max(11, width - 10), 20 + 14 * len(lines)), fill=(20, 20, 30))
            draw.multiline_text((15, 15), '\n'.join(lines), fill='white', spacing=3)
        return True

    def close(self):
        self.source.close()
