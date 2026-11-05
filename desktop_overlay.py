"""GTK 3 X11 helper: an image in a transparent click-through desktop window."""

import sys

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


def main(image_path):
    screen = Gdk.Screen.get_default()
    if not screen or not screen.is_composited() or not screen.get_rgba_visual():
        raise RuntimeError('An X11 display with a compositor and RGBA visual is required')
    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 240, 135, True)
    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title('Mira Desktop Overlay')
    window.set_visual(screen.get_rgba_visual())
    window.set_app_paintable(True)
    window.set_decorated(False)
    window.set_keep_above(True)
    window.set_accept_focus(False)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_default_size(240, 135)
    window.stick()

    def draw(widget, context):
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        Gdk.cairo_set_source_pixbuf(context, image, (240 - image.get_width()) / 2,
                                  (135 - image.get_height()) / 2)
        context.paint()
        return False

    def command(stream, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            Gtk.main_quit()
            return False
        line = stream.readline().strip()
        if line == 'hide':
            window.hide()
        elif line == 'show':
            window.show_all()
        return True

    window.connect('draw', draw)
    window.show_all()
    window.move(max(0, screen.get_width() - 250), 10)
    window.get_window().input_shape_combine_region(cairo.Region(), 0, 0)
    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, command)
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1])
