import unittest

from gdo.video.Duck3DWorker import transition_weight


class DuckTransitionTest(unittest.TestCase):
    def test_smooth_transition_is_clamped(self):
        self.assertEqual(transition_weight(-1), 0)
        self.assertEqual(transition_weight(0), 0)
        self.assertAlmostEqual(transition_weight(.35), .5)
        self.assertEqual(transition_weight(.7), 1)
        self.assertEqual(transition_weight(2), 1)
