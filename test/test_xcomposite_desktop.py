import unittest

from PIL import Image

from gdo.video.XCompositeDesktop import compose_windows


class CompositeDesktopTest(unittest.TestCase):
    def test_stacking_opacity_and_clipping(self):
        bottom = Image.new('RGBA', (4, 4), (255, 0, 0, 255))
        top = Image.new('RGBA', (4, 4), (0, 0, 255, 255))
        image = compose_windows((4, 4), [(bottom, -1, 0, 1), (top, 2, 0, .5)])
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(image.getpixel((2, 0)), (127, 0, 128))
        self.assertEqual(image.getpixel((3, 0)), (0, 0, 128))

    def test_background_is_preserved(self):
        background = Image.new('RGB', (2, 2), 'green')
        self.assertEqual(compose_windows((2, 2), [], background).getpixel((0, 0)), (0, 128, 0))
