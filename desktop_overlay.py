"""GTK 3 X11 helper: an image in a transparent click-through desktop window."""

import sys
import json
import random
import textwrap
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
from LayerStack import LayerStack


def main(image_path, screensharing=False):
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

    effect = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    effect.set_title('Mira Starwars Effect')
    effect.set_visual(screen.get_rgba_visual())
    effect.set_app_paintable(True)
    effect.set_decorated(False)
    effect.set_keep_above(True)
    effect.set_accept_focus(False)
    effect.set_skip_taskbar_hint(True)
    effect.set_skip_pager_hint(True)
    effect_width = screen.get_width() if screensharing else 640
    effect_height = screen.get_height() if screensharing else 360
    effect.set_default_size(effect_width, effect_height)
    effect.stick()
    layers = LayerStack()

    def draw_effect(widget, context):
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.set_source_rgba(0, 0, 0, 0)
        context.paint()
        context.set_operator(cairo.OPERATOR_OVER)
        # Render in the same logical coordinate system at any desktop size.
        context.scale(effect_width / 640, effect_height / 360)
        context.set_source_rgb(1, .86, .18)
        context.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        for key, layer in layers.ordered():
            if key == 'vintage':
                if random.random() < .15:
                    context.set_source_rgba(0, 0, 0, random.uniform(.02, .12))
                    context.rectangle(0, 0, 640, 360)
                    context.fill()
                for x, y1, y2, alpha, expiry in layer['scratches']:
                    context.set_source_rgba(1, 1, .85, alpha)
                    context.set_line_width(random.choice((.4, .6, 1)))
                    context.move_to(x, y1)
                    context.line_to(x + random.uniform(-1, 1), y2)
                    context.stroke()
                continue
            context.set_source_rgb(1, .86, .18)
            scroll = (time.monotonic() - layer['start']) * 36
            for i, line in enumerate(layer['lines']):
                y = 360 - scroll + i * 28
                if not -40 <= y < 360:
                    continue
                context.set_font_size(max(10, 12 + 15 * max(0, y) / 360))
                extents = context.text_extents(line)
                context.move_to((640 - extents.width) / 2, y)
                context.show_text(line)
        return False

    def tick_effect():
        if not effect.get_visible():
            return False
        for key, layer in layers.ordered():
            if key == 'vintage':
                now = time.monotonic()
                layer['scratches'] = [item for item in layer['scratches'] if item[4] > now]
                if random.random() < .3:
                    y = random.uniform(0, 360)
                    layer['scratches'].append((random.uniform(0, 640), y, min(360, y + random.uniform(30, 250)),
                                               random.uniform(.15, .65), now + random.uniform(.08, .7)))
                layer['scratches'] = layer['scratches'][-12:]
                continue
            if (time.monotonic() - layer['start']) * 36 > 360 + (len(layer['lines']) + 2) * 28:
                layers.remove(key)
        if not layers.ordered():
            effect.hide()
            return False
        effect.queue_draw()
        return True

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
        else:
            try:
                request = json.loads(line)
                text = request.get('text', '')
                if request.get('effect') == 'starwars' and isinstance(text, str) and text.strip() and len(text) <= 4096:
                    lines = [part for item in text.splitlines() for part in (textwrap.wrap(item, 36) or [''])]
                    layers.put('starwars', {'lines': lines, 'start': time.monotonic()})
                elif request.get('effect') == 'vintage' and isinstance(request.get('enabled'), bool):
                    if request['enabled']:
                        layers.put('vintage', {'scratches': []})
                    else:
                        layers.remove('vintage')
                else:
                    return True
                if layers.ordered():
                    already_visible = effect.get_visible()
                    effect.show_all()
                    effect.move(0 if screensharing else max(0, (screen.get_width() - 640) // 2),
                                0 if screensharing else max(0, (screen.get_height() - 360) // 2))
                    effect.get_window().input_shape_combine_region(cairo.Region(), 0, 0)
                    if not already_visible:
                        GLib.timeout_add(33, tick_effect)
                else:
                    effect.hide()
            except (ValueError, AttributeError, TypeError):
                pass
        return True

    window.connect('draw', draw)
    effect.connect('draw', draw_effect)
    window.show_all()
    window.move(max(0, screen.get_width() - 250), 10)
    window.get_window().input_shape_combine_region(cairo.Region(), 0, 0)
    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, command)
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == 'screensharing')
