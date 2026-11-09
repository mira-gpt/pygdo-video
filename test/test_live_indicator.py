import unittest
from unittest.mock import patch

from PIL import Image
from gdo.video.LiveIndicator import LiveIndicator


class LiveIndicatorTest(unittest.TestCase):
    def test_indicator_is_red_only_for_active_gain(self):
        for status, level, expected in [('on', .1, (220, 0, 0)), ('on', 0, (0, 0, 0)),
                                        ('unknown', .5, (0, 0, 0))]:
            frame = Image.new('RGB', (160, 60), (180, 180, 180))
            with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=(status, level)):
                self.assertTrue(LiveIndicator('discuss').draw(frame))
            self.assertIn(expected, set(frame.getdata()))
