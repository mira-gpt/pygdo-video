import threading
import unittest
from unittest.mock import MagicMock, patch

from gdo.audio.meter import AudioFeatures
from gdo.video.Duck3DSource import Duck3DSource


class DuckMusicTest(unittest.TestCase):
    def test_spell_bats_stay_in_bounds(self):
        from gdo.video.Duck3DWorker import spell_bat_position
        for elapsed in (0, .5, 8, 100):
            for index in range(5):
                x, z = spell_bat_position(elapsed, index, 5)
                self.assertTrue(-.95 <= x <= .95)
                self.assertTrue(1.15 <= z <= 2.15)

    def test_metal_head_pitch_tracks_pulse_and_is_bounded(self):
        from gdo.video.Duck3DWorker import metal_head_pitch
        self.assertEqual(3, metal_head_pitch(0))
        self.assertGreater(metal_head_pitch(.8), metal_head_pitch(.2))
        self.assertEqual(33, metal_head_pitch(2))

    def test_metal_receives_microphone_features(self):
        source = Duck3DSource.__new__(Duck3DSource)
        source.lock = threading.Lock()
        source.frame = None
        source.mode = 'metal'
        source.feature_sent = 0
        source.update = MagicMock()
        with patch('gdo.video.Duck3DSource.time.monotonic', return_value=10), \
                patch('gdo.audio.meter.MicrophoneMeter.features', return_value=AudioFeatures('on', .2, 440)):
            source.snapshot()
        source.update.assert_called_once_with(gain=.2, frequency_hz=440)

    def test_music_bounce_tracks_gain_smoothly(self):
        from gdo.video.Duck3DWorker import music_bounce
        self.assertEqual(0, music_bounce(0, 0))
        pulse = music_bounce(0, .05)
        self.assertGreater(pulse, 0)
        self.assertLess(pulse, 1)
        self.assertGreater(music_bounce(pulse, 0), 0)
        self.assertLess(music_bounce(pulse, 0), pulse)

    def test_notes_have_baseline_and_increase_with_gain(self):
        from gdo.video.Duck3DWorker import music_note_count
        self.assertEqual(2, music_note_count(0))
        self.assertGreater(music_note_count(.01), music_note_count(0))
        self.assertEqual(6, music_note_count(.05))
        self.assertEqual(6, music_note_count(1))
        self.assertEqual(2, music_note_count(-1))

    def test_features_sent_only_for_music_and_throttled(self):
        source = Duck3DSource.__new__(Duck3DSource)
        source.lock = threading.Lock()
        source.frame = None
        source.mode = 'music'
        source.feature_sent = 0
        source.update = MagicMock()
        with patch('gdo.video.Duck3DSource.time.monotonic', return_value=10), \
                patch('gdo.audio.meter.MicrophoneMeter.features', return_value=AudioFeatures('on', .2, 440)):
            source.snapshot()
            source.snapshot()
        source.update.assert_called_once_with(gain=.2, frequency_hz=440)
