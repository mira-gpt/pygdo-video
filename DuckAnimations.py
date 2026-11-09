"""Compatibility view of the shared animation metadata."""

from gdo.mira.GDT_MiraMood import ANIMATIONS

BASE_DEFAULTS = {key: data['base'] for key, data in ANIMATIONS.items()}
