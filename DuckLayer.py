"""Lightweight rendered poses of the 3D duck, with spoken captions."""
import textwrap
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from gdo.video.DuckStatus import volume_label


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
        self.mic_language = ''
        self.speech_volume = None

    def draw_mic_language(self, frame):
        labels = [label for label in (self.mic_language.upper(), volume_label(self.speech_volume)) if label]
        if not labels:
            return
        draw = ImageDraw.Draw(frame)
        try:
            font = ImageFont.truetype('DejaVuSans-Bold.ttf', 9)
        except OSError:
            font = ImageFont.load_default()
        for index, text in enumerate(labels):
            box = draw.textbbox((0, 0), text, font=font, stroke_width=1)
            x = max(0, frame.width - (box[2] - box[0]) - 14)
            y = max(0, frame.height - 14 - (len(labels) - index) * 11)
            draw.text((x, y), text, font=font, fill='white', stroke_width=1, stroke_fill='black')

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
        frame.paste(image, (max(0, width - side - 10), max(0, height - side - 8)), image)
        self.draw_mic_language(frame)
        caption = self.text if speaking else self.caption_text if time.monotonic() < self.caption_until else ''
        if caption:
            draw = ImageDraw.Draw(frame)
            lines = textwrap.wrap(caption, max(12, width // 10))[:4]
            draw.rectangle((10, 10, max(11, width - 10), 20 + 14 * len(lines)), fill=(20, 20, 30))
            draw.multiline_text((15, 15), '\n'.join(lines), fill='white', spacing=3)
        return True
