"""Display the local Dog microphone listener's level, not system-wide capture."""
from PIL import ImageDraw


class MicrophoneLevel:
    def draw(self, frame):
        try:
            from gdo.audio.meter import MicrophoneMeter
            status, level = MicrophoneMeter.snapshot()
        except (ImportError, RuntimeError):
            status, level = 'unknown', 0.0
        width, height = frame.size
        left, top = 12, max(0, height - 44)
        right = min(width - 1, left + 150)
        draw = ImageDraw.Draw(frame)
        draw.rectangle((left, top, right, min(height - 1, top + 32)), fill=(16, 16, 16), outline=(220, 220, 220))
        label = {'on': 'MIC ON', 'off': 'MIC OFF', 'unknown': 'MIC UNKNOWN'}.get(status, 'MIC UNKNOWN')
        draw.text((left + 4, top + 2), label, fill=(255, 255, 255))
        if status == 'on':
            bar_left, bar_right = left + 4, right - 4
            bar_width = max(0, int((bar_right - bar_left) * min(1.0, level * 100)))
            if bar_width:
                draw.rectangle((bar_left, top + 19, bar_left + bar_width, top + 27), fill=(60, 225, 80))
        return True
