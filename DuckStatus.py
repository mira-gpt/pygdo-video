"""Small, backend-independent status labels for the duck."""


def volume_label(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ''
    if not 0 <= number <= 100:
        return ''
    return f'{number:g}%'
