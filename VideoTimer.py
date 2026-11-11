from datetime import datetime
import math
import re


def parse_target(value, now=None):
    now = now or datetime.now().astimezone()
    if re.fullmatch(r'\d{1,2}:\d{2}', value):
        hour, minute = map(int, value.split(':'))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    else:
        target = datetime.fromisoformat(value)
        if target.tzinfo is None:
            target = target.astimezone()
    if target <= now:
        raise ValueError('Timer date must be in the future')
    return target


class VideoTimer:
    def __init__(self):
        self.target = None
        self.text = ''
        self.next_announcement = 0.0

    def set(self, target, text):
        self.target, self.text = target, text
        self.next_announcement = 0.0

    def tick(self, now, monotonic, frequency):
        if not self.target:
            return None
        remaining = math.ceil((self.target - now).total_seconds())
        if remaining <= 0:
            self.target = None
            return None
        if monotonic < self.next_announcement:
            return None
        self.next_announcement = monotonic + frequency
        hours, seconds = divmod(remaining, 3600)
        minutes, seconds = divmod(seconds, 60)
        duration = f'{hours}h {minutes}m {seconds}s' if hours else f'{minutes}m {seconds}s'
        return f'{self.text} — Noch {duration}'
