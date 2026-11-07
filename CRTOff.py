"""Temporary CRT shutdown effect; does not stop the video source."""
import time

def crt_state(elapsed, hold=2.0):
    if elapsed < 0:
        elapsed = 0
    if elapsed >= 1.5 + hold + 1.0:
        return None
    if elapsed < .55:
        return 1.0, max(.01, 1 - elapsed / .55), 1.0
    if elapsed < 1.0:
        return max(.01, 1 - (elapsed - .55) / .45), .01, 1.0
    if elapsed < 1.5:
        return .01, .01, max(0, 1 - (elapsed - 1.0) / .5)
    if elapsed < 1.5 + hold:
        return .01, .01, 0.0
    power_on = elapsed - 1.5 - hold
    if power_on < .25:
        return .01, .01, power_on / .25
    if power_on < .65:
        return min(1, .01 + (power_on - .25) / .4), .01, 1.0
    return 1.0, min(1, .01 + (power_on - .65) / .35), 1.0


class CRTOff:
    def __init__(self, hold=2.0):
        self.start = time.monotonic()
        self.hold = hold

    def draw(self, frame, now=None):
        state = crt_state((time.monotonic() if now is None else now) - self.start, self.hold)
        if state is None:
            return False
        width, height = frame.size
        sx, sy, brightness = state
        frame.paste((0, 0, 0), (0, 0, width, height))
        from PIL import ImageDraw
        draw = ImageDraw.Draw(frame)
        w, h = max(2, int(width * sx)), max(2, int(height * sy))
        color = int(255 * brightness)
        draw.rectangle(((width - w) // 2, (height - h) // 2, (width + w) // 2, (height + h) // 2), fill=(color, color, color))
        return True
