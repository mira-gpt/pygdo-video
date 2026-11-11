import unittest
from datetime import datetime, timedelta, timezone

from gdo.video.VideoTimer import VideoTimer, parse_target


class VideoTimerTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 11, 8, 0, tzinfo=timezone.utc)

    def test_time_means_today(self):
        self.assertEqual(self.now.replace(hour=8, minute=45), parse_target('8:45', self.now))
        with self.assertRaises(ValueError):
            parse_target('7:00', self.now)

    def test_timer_repeats_and_expires(self):
        timer = VideoTimer()
        timer.set(self.now + timedelta(minutes=10), 'WeChall News')
        self.assertEqual('WeChall News — Noch 10m 0s', timer.tick(self.now, 100, 300))
        self.assertIsNone(timer.tick(self.now + timedelta(minutes=1), 160, 300))
        self.assertEqual('WeChall News — Noch 5m 0s', timer.tick(self.now + timedelta(minutes=5), 400, 300))
        self.assertIsNone(timer.tick(self.now + timedelta(minutes=10), 700, 300))
        self.assertIsNone(timer.target)

    def test_replacement(self):
        timer = VideoTimer()
        timer.set(self.now + timedelta(hours=1), 'First')
        timer.tick(self.now, 100, 300)
        timer.set(self.now + timedelta(hours=2), 'Second')
        self.assertEqual('Second — Noch 2h 0m 0s', timer.tick(self.now, 101, 300))

    def test_countdown_includes_seconds(self):
        timer = VideoTimer()
        timer.set(self.now + timedelta(minutes=23, seconds=4), 'WeChall News')
        self.assertEqual('WeChall News — Noch 23m 4s', timer.tick(self.now, 1, 300))

    def test_past_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_target('2026-11-10T08:00:00+00:00', self.now)
