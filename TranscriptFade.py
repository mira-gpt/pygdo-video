"""Visibility of a transcript after the latest final text arrived."""


def transcript_alpha(now, updated):
    if not updated:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (now - updated - 10.0)))
