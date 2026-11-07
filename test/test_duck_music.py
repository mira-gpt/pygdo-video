import threading
import unittest
from unittest.mock import MagicMock, patch

from gdo.audio.meter import AudioFeatures
from gdo.video.Duck3DSource import Duck3DSource


class DuckMusicTest(unittest.TestCase):
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
