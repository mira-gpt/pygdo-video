import subprocess
from pathlib import Path

from gdotest.TestUtil import GDOTestCase


class StarWarsArabicTest(GDOTestCase):
    def test_pango_renders_arabic_without_missing_glyphs(self):
        video = Path(__file__).resolve().parents[1]
        script = ("import sys; sys.path.insert(0, sys.argv[1]); import cairo; "
                  "from StarWarsText import draw_line; "
                  "surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 640, 360); "
                  "missing = draw_line(cairo.Context(surface), 'المرشد أهلاً يا إنسان', 100); "
                  "surface.flush(); assert missing == 0; assert any(surface.get_data())")
        result = subprocess.run(['/usr/bin/python3', '-c', script, str(video)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
