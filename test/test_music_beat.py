import array
import math
import unittest
from unittest.mock import MagicMock, patch

from gdo.video.MusicBeat import OnsetDetector


def tone(frequency, amplitude, length=320):
    return array.array('h', (round(amplitude * 32767 * math.sin(2 * math.pi * frequency * i / 16000))
                             for i in range(length))).tobytes()


class MusicBeatTest(unittest.TestCase):
    def test_silence_and_bass_snare_like_transients(self):
        detector = OnsetDetector()
        self.assertFalse(detector.feed(bytes(640), 0))
        self.assertTrue(detector.feed(tone(80, .7), 1))
        self.assertEqual('bass', detector.kind)
        self.assertFalse(detector.feed(tone(80, .7), 1.02))
        for i in range(50):
            detector.feed(bytes(640), 1.1 + i * .02)
        self.assertTrue(detector.feed(tone(2200, .7), 2.2))
        self.assertEqual('snare', detector.kind)
        self.assertEqual(2, detector.count)

    def test_low_noise_does_not_trigger(self):
        detector = OnsetDetector()
        for i in range(50):
            self.assertFalse(detector.feed(tone(1000, .001), i * .02))

    def test_source_forwards_classified_beat(self):
        from gdo.video.Duck3DSource import Duck3DSource
        import threading
        source = Duck3DSource.__new__(Duck3DSource)
        source.lock = threading.Lock()
        source.frame = None
        source.mode = 'music'
        source.feature_sent = 0
        source.music_beat = MagicMock()
        source.music_beat.snapshot.return_value = (3, .4, 'snare')
        source.update = MagicMock()
        with patch('gdo.video.Duck3DSource.time.monotonic', return_value=10):
            source.snapshot()
        source.update.assert_called_once_with(beat=3, music_volume=.4, beat_kind='snare')

    def test_volume_is_smoothed_and_tracks_overall_loudness(self):
        quiet, loud = OnsetDetector(), OnsetDetector()
        for i in range(150):
            quiet.feed(tone(1000, .05), i * .02)
            loud.feed(tone(1000, .4), i * .02)
        self.assertGreater(loud.volume, quiet.volume * 5)
        initial = loud.volume
        loud.feed(bytes(640), 3.1)
        self.assertGreater(loud.volume, initial * .95)
        for i in range(300):
            loud.feed(bytes(640), 3.2 + i * .02)
        self.assertLess(loud.volume, initial * .01)

    def test_monitor_starts_only_for_music_and_stops_on_mode_change(self):
        from gdo.video.Duck3DSource import Duck3DSource
        source = Duck3DSource.__new__(Duck3DSource)
        import threading
        source.lock = threading.Lock()
        source.process = MagicMock()
        source.mode = 'idle'
        source.music_beat = None
        audio = MagicMock()
        audio.get_config_val.return_value = 'desktop-user'
        with patch('gdo.audio.module_audio.module_audio.instance', return_value=audio), \
                patch('gdo.video.MusicBeat.MusicBeat') as beat:
            source.update(mode='music')
            beat.assert_called_once_with('desktop-user')
            source.update(mode='idle')
            beat.return_value.close.assert_called_once()
            self.assertIsNone(source.music_beat)
