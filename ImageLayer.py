"""Bounded image loading and a reusable, positioned compositor layer."""
import io
import os
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps
from gdo.ui.GDT_CSSLength import GDT_CSSLength


class ImageLayer:
    MAX_BYTES = 4 * 1024 * 1024
    MAX_PIXELS = 16_000_000

    def __init__(self, image, width='25%', height='25%', x='2%', y='2%'):
        self.image = image.convert('RGBA')
        self.width, self.height, self.x, self.y = width, height, x, y
        for length in (width, height, x, y):
            GDT_CSSLength.resolve(length, 100)
        if GDT_CSSLength.resolve(width, 100) <= 0 or GDT_CSSLength.resolve(height, 100) <= 0:
            raise ValueError('Image dimensions must be positive')

    @classmethod
    def read_url(cls, url, max_bytes=None):
        max_bytes = cls.MAX_BYTES if max_bytes is None else max_bytes
        parsed = urlsplit(url)
        if parsed.scheme == 'file' and not parsed.netloc and not parsed.query and not parsed.fragment:
            path = unquote(parsed.path)
            if not os.path.isabs(path):
                raise ValueError('Image file path must be absolute')
            with open(path, 'rb') as stream:
                data = stream.read(max_bytes + 1)
        elif parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username and not parsed.password:
            with urlopen(Request(url, headers={'User-Agent': 'PyGDO-Video/1'}), timeout=8) as response:
                if urlsplit(response.geturl()).scheme not in ('http', 'https'):
                    raise ValueError('Invalid image redirect')
                data = response.read(max_bytes + 1)
        else:
            raise ValueError('Image URL must use file, http or https')
        if len(data) > max_bytes:
            raise ValueError('Media file exceeds the size limit')
        return data

    @classmethod
    def load(cls, url, **kwargs):
        data = cls.read_url(url)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > cls.MAX_PIXELS:
                raise ValueError('Image dimensions are too large')
            image.load()
            return cls(image, **kwargs)

    def draw(self, frame):
        width, height = frame.size
        w, h = self.output_size(width, height)
        x = round(GDT_CSSLength.resolve(self.x, width))
        y = round(GDT_CSSLength.resolve(self.y, height))
        image = ImageOps.contain(self.image, (w, h), Image.Resampling.LANCZOS)
        frame.paste(image, (x, y), image)
        return True

    def output_size(self, width, height):
        w = round(GDT_CSSLength.resolve(self.width, width))
        h = round(GDT_CSSLength.resolve(self.height, height))
        if w < 1 or h < 1 or w > width * 4 or h > height * 4:
            raise ValueError('Image size is outside supported bounds')
        return w, h
