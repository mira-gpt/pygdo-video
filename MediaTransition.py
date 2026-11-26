"""Time-based entrance geometry shared by media output backends."""
import math


def media_transition(kind, elapsed, canvas_width, x, y):
    duration = .8 if kind == 'fade' else (2.0 if kind == 'cyclone' else 1.2)
    progress = min(1.0, max(0.0, elapsed / duration))
    eased = 1 - (1 - progress) ** 3
    if kind == 'cyclone':
        radius = min(canvas_width * .4, 500) * (1 - eased)
        angle = 4 * math.pi * progress
        return x + radius * math.cos(angle), y + radius * math.sin(angle), 0.0, 1.0
    if kind == 'throw':
        return x - (canvas_width + x) * (1 - eased), y - 80 * math.sin(math.pi * progress) * (1 - progress), 900 * (1 - eased), 1.0
    return x, y, 0.0, eased if kind == 'fade' else 1.0
