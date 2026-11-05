import unittest
from unittest.mock import MagicMock

from PIL import Image

from gdo.video.LayerStack import LayerStack
from gdo.video.VideoConnector import VideoConnector


class EffectLayerTest(unittest.TestCase):
    def test_keyed_layers_stack_update_reorder_and_remove(self):
        layers = LayerStack()
        layers.put('duck', 'duck1')
        layers.put('starwars', 'crawl')
        layers.put('duck', 'duck2')
        self.assertEqual(layers.ordered(), [('duck', 'duck2'), ('starwars', 'crawl')])
        layers.put('duck', 'duck3', z=4)
        self.assertEqual(layers.ordered(), [('starwars', 'crawl'), ('duck', 'duck3')])
        self.assertTrue(layers.remove('duck'))
        layers.put('duck', 'duck4')
        self.assertEqual(layers.ordered(), [('starwars', 'crawl'), ('duck', 'duck4')])

    def test_plugins_use_worker_layer_stack(self):
        worker = VideoConnector()
        worker.worker = MagicMock()
        worker.worker.is_alive.return_value = True
        first, second = MagicMock(), MagicMock()
        worker.put_effect('duck', first)
        worker.put_effect('starwars', second)
        frame = Image.new('RGB', (1, 1))
        for key, effect in worker.effects.ordered():
            effect.draw(frame)
        first.draw.assert_called_once_with(frame)
        second.draw.assert_called_once_with(frame)
        self.assertTrue(worker.remove_effect('duck'))
        self.assertEqual(worker.effects.ordered(), [('starwars', second)])
