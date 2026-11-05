"""Validation for externally addressed effect-layer keys."""
import re


def effect_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,31}', value):
        raise ValueError('Effect key must contain lowercase letters, digits, underscores or hyphens')
    return value
