"""Magnify the X11 pointer position within the composited desktop frame."""
import ctypes
import ctypes.util
import math

from PIL import Image, ImageDraw


class X11Pointer:
    def __init__(self, display):
        self.display = display
        library = ctypes.util.find_library('X11')
        if not library:
            raise RuntimeError('X11 library not available')
        self.x = ctypes.CDLL(library)
        p, i, u, ul = ctypes.c_void_p, ctypes.c_int, ctypes.c_uint, ctypes.c_ulong
        self.x.XOpenDisplay.argtypes, self.x.XOpenDisplay.restype = [ctypes.c_char_p], p
        self.x.XCloseDisplay.argtypes = [p]
        self.x.XDefaultScreen.argtypes, self.x.XDefaultScreen.restype = [p], i
        self.x.XRootWindow.argtypes, self.x.XRootWindow.restype = [p, i], ul
        self.x.XDisplayWidth.argtypes, self.x.XDisplayWidth.restype = [p, i], i
        self.x.XDisplayHeight.argtypes, self.x.XDisplayHeight.restype = [p, i], i
        self.x.XQueryPointer.argtypes = [p, ul, ctypes.POINTER(ul), ctypes.POINTER(ul),
                                        ctypes.POINTER(i), ctypes.POINTER(i), ctypes.POINTER(i),
                                        ctypes.POINTER(i), ctypes.POINTER(u)]
        self.x.XQueryPointer.restype = i

    def position(self):
        d = self.x.XOpenDisplay(self.display.encode())
        if not d:
            return None
        try:
            s = self.x.XDefaultScreen(d)
            root, child = ctypes.c_ulong(), ctypes.c_ulong()
            rx, ry, wx, wy, mask = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_uint()
            if not self.x.XQueryPointer(d, self.x.XRootWindow(d, s), ctypes.byref(root), ctypes.byref(child),
                                        ctypes.byref(rx), ctypes.byref(ry), ctypes.byref(wx), ctypes.byref(wy), ctypes.byref(mask)):
                return None
            return rx.value, ry.value, self.x.XDisplayWidth(d, s), self.x.XDisplayHeight(d, s)
        finally:
            self.x.XCloseDisplay(d)


class Magnify:
    def __init__(self, pointer, zoom=2.0, radius=90):
        if not math.isfinite(zoom) or not 1.1 <= zoom <= 8 or not 16 <= radius <= 240:
            raise ValueError('Zoom must be 1.1–8 and radius 16–240 pixels')
        self.pointer, self.zoom, self.radius = pointer, zoom, radius

    def draw(self, frame):
        pos = self.pointer.position()
        if not pos:
            return True
        x, y, sw, sh = pos
        if sw <= 0 or sh <= 0:
            return True
        width, height = frame.size
        scale = min(width / sw, height / sh)
        cx = round((width - sw * scale) / 2 + x * scale)
        cy = round((height - sh * scale) / 2 + y * scale)
        r = self.radius
        source_radius = r / self.zoom
        crop = frame.crop((round(cx - source_radius), round(cy - source_radius),
                           round(cx + source_radius), round(cy + source_radius)))
        if not crop.width or not crop.height:
            return True
        enlarged = crop.resize((r * 2, r * 2), Image.Resampling.LANCZOS)
        mask = Image.new('L', (r * 2, r * 2))
        ImageDraw.Draw(mask).ellipse((0, 0, r * 2 - 1, r * 2 - 1), fill=255)
        frame.paste(enlarged, (cx - r, cy - r), mask)
        ImageDraw.Draw(frame).ellipse((cx - r, cy - r, cx + r - 1, cy + r - 1), outline='white', width=2)
        return True
