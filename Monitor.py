"""X11 monitor selection shared by overlay and desktop capture."""
import re
import subprocess


def monitor_geometry(display, number):
    if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
        raise ValueError('Configure a local X11 display first')
    result = subprocess.run(['xrandr', '--display', display, '--listmonitors'],
                            capture_output=True, text=True, timeout=5, check=True)
    monitors = []
    for line in result.stdout.splitlines():
        match = re.match(r'^\s*\d+:\s+\S+\s+(\d+)(?:/\d+)?x(\d+)(?:/\d+)?([+-]\d+)([+-]\d+)', line)
        if match:
            monitors.append(tuple(map(int, match.groups())))
    try:
        index = int(number) - 1
        if index < 0:
            raise IndexError
        return monitors[index]
    except (ValueError, TypeError, IndexError):
        raise ValueError(f'Monitor {number} is not available on {display}') from None


def capture_input(display, geometry):
    if not re.fullmatch(r':[0-9]+(?:\.[0-9]+)?', display or ''):
        raise ValueError('Configure a local X11 display first')
    if geometry is None:
        return ['-i', display]
    width, height, x, y = geometry
    if width <= 0 or height <= 0 or x < 0 or y < 0:
        raise ValueError('Unsupported X11 monitor geometry')
    return ['-video_size', f'{width}x{height}', '-i', f'{display}+{x},{y}']
