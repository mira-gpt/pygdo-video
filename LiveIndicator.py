"""Small live-mode indicator; never starts microphone capture."""
from PIL import ImageDraw, ImageFont


class LiveIndicator:
    def __init__(self, mode='off'):
        self.mode = mode
        try:
            self.font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        except OSError:
            self.font = ImageFont.load_default()

    def draw(self, frame):
        try:
            from gdo.audio.meter import MicrophoneMeter
            status, level = MicrophoneMeter.snapshot()
        except (ImportError, RuntimeError):
            status, level = 'unknown', 0
        color = (220, 0, 0) if status == 'on' and level > 0 else (0, 0, 0)
        ImageDraw.Draw(frame).text((10, 10), self.mode, font=self.font, fill=color,
                                   stroke_width=1, stroke_fill=(255, 255, 255))
        return True
