"""Validation shared by compositor and GTK drawing backends."""
import math
import re


def validate_line(x1, y1, x2, y2, color, width):
    points = tuple(float(value) for value in (x1, y1, x2, y2))
    width = float(width)
    if not all(math.isfinite(value) and 0 <= value <= 100 for value in points):
        raise ValueError('Coordinates must be percentages between 0 and 100')
    if not math.isfinite(width) or not .1 <= width <= 10:
        raise ValueError('Line width must be between 0.1 and 10 percent')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Color must be #RRGGBB')
    return (*points, color, width)
