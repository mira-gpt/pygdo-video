"""Experimental X11 scene reconstruction without a self-captured overlay.

This deliberately does not redirect windows: an existing compositor must do
that. It approximates its scene and does not reproduce compositor shadows.
"""

from PIL import Image


def compose_windows(size, windows, background=None):
    """Compose already captured RGBA windows in bottom-to-top order."""
    frame = Image.new('RGBA', size, (0, 0, 0, 255))
    if background is not None:
        frame.alpha_composite(background.convert('RGBA'), (0, 0))
    for image, x, y, opacity in windows:
        image = image.convert('RGBA')
        if opacity < 1:
            image.putalpha(image.getchannel('A').point(lambda value: round(value * opacity)))
        frame.alpha_composite(image, (x, y))
    return frame.convert('RGB')


class XCompositeDesktop:
    """Capture visible root children via XComposite, excluding our window."""

    def __init__(self, geometry, exclude_xid, display_name=None):
        from Xlib import display
        self.display = display.Display(display_name)
        if not self.display.has_extension('Composite'):
            self.display.close()
            raise RuntimeError('XComposite extension is unavailable')
        self.root = self.display.screen().root
        self.geometry = geometry
        self.exclude_xid = int(exclude_xid)
        self.opacity_atom = self.display.intern_atom('_NET_WM_WINDOW_OPACITY')

    def close(self):
        self.display.close()

    def _contains_excluded(self, window, depth=0):
        if window.id == self.exclude_xid:
            return True
        if depth >= 6:
            return False
        try:
            return any(self._contains_excluded(child, depth + 1) for child in window.query_tree().children)
        except Exception:
            return False

    def capture(self):
        from Xlib import X, error
        width, height, origin_x, origin_y = self.geometry
        windows = []
        for window in self.root.query_tree().children:
            pixmap = None
            try:
                if self._contains_excluded(window):
                    continue
                attrs = window.get_attributes()
                if attrs.map_state != X.IsViewable or attrs.win_class == X.InputOnly:
                    continue
                geom = window.get_geometry()
                coords = self.root.translate_coords(window, 0, 0)
                x, y = coords.x - origin_x, coords.y - origin_y
                if x >= width or y >= height or x + geom.width <= 0 or y + geom.height <= 0:
                    continue
                pixmap = window.composite_name_window_pixmap()
                data = pixmap.get_image(0, 0, geom.width, geom.height, X.ZPixmap, 0xffffffff)
                if data is None:
                    continue
                # X11 on the supported desktop uses little-endian BGRX/BGRA.
                mode = 'BGRA' if geom.depth == 32 else 'BGRX'
                image = Image.frombytes('RGBA', (geom.width, geom.height), data.data, 'raw', mode)
                opacity = window.get_full_property(self.opacity_atom, X.AnyPropertyType)
                alpha = min(1.0, int(opacity.value[0]) / 0xffffffff) if opacity is not None and len(opacity.value) else 1.0
                windows.append((image, x, y, alpha))
            except (error.XError, ValueError, AttributeError, IndexError):
                continue
            finally:
                if pixmap is not None:
                    pixmap.free()
        self.display.sync()
        return compose_windows((width, height), windows)
