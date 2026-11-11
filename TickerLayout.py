"""Shared bottom-right ticker geometry for both video renderers."""

GOLDEN_SMALL = (3 - 5 ** 0.5) / 2


def ticker_bounds(width):
    """Leave the larger golden-ratio section to the left of the ticker."""
    right = max(0, width - 12)
    return max(0, right - round(width * GOLDEN_SMALL)), right


def next_message_x(width, current_width, offset, elapsed, separator_width):
    """Quickly catch up from the right, never overlapping the current text."""
    moving_in = width - max(0.0, elapsed - 2.0) * 120.0
    after_current = current_width - offset + separator_width
    return max(0.0, after_current, moving_in)
