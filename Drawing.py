"""Persistent live drawing layer made of bounded line segments."""
from PIL import ImageDraw
from gdo.video.DrawingProtocol import validate_line


class Drawing:
    MAX_LINES = 2000

    def __init__(self):
        self.lines = []

    def add(self, *line):
        if len(self.lines) >= self.MAX_LINES:
            raise ValueError('Drawing has reached its line limit')
        self.lines.append(validate_line(*line))

    def draw(self, frame):
        width, height = frame.size
        drawer = ImageDraw.Draw(frame)
        for x1, y1, x2, y2, color, stroke_width in self.lines:
            drawer.line((round(x1 * width / 100), round(y1 * height / 100),
                         round(x2 * width / 100), round(y2 * height / 100)),
                        fill=color, width=max(1, round(stroke_width * min(width, height) / 100)))
        return True
