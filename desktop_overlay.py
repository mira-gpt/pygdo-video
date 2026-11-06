"""GTK 3 X11 helper: an image in a transparent click-through desktop window."""

import sys
import base64
import json
import os
import random
import textwrap
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
from LayerStack import LayerStack
from DrawingProtocol import validate_line


def main(image_path, screensharing=False, window_suffix=''):
    screen = Gdk.Screen.get_default()
    if not screen or not screen.is_composited() or not screen.get_rgba_visual():
        raise RuntimeError('An X11 display with a compositor and RGBA visual is required')
    image = GdkPixbuf.Pixbuf.new_from_file_at_scale(image_path, 240, 135, True)
    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title('Mira Desktop Overlay' + window_suffix)
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
    effect.set_title('Mira Starwars Effect' + window_suffix)
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
            if key == 'duck':
                context.save()
                pixbuf = layer.get('frame') or (layer['open'] if layer['speaking'] and int(time.monotonic() * 6) % 2 else layer['closed'])
                # Move the duck down by 32 physical screen pixels, even when
                # the overlay is scaled from its 640x360 logical canvas.
                Gdk.cairo_set_source_pixbuf(context, pixbuf, 480, 165 + 32 * 360 / effect_height)
                context.paint()
                caption = layer['text'] if layer['speaking'] else layer.get('caption', '') if time.monotonic() < layer.get('caption_until', 0) else ''
                if caption:
                    lines = textwrap.wrap(caption, 65)[:4]
                    context.set_source_rgba(.05, .05, .08, .9)
                    context.rectangle(10, 10, 620, 18 + len(lines) * 19)
                    context.fill()
                    context.set_source_rgb(1, 1, 1)
                    context.set_font_size(15)
                    for i, line in enumerate(lines):
                        context.move_to(16, 28 + i * 19)
                        context.show_text(line)
                context.restore()
                continue
            if key == 'mic':
                if layer['status'] == 'on' and time.monotonic() - layer['updated'] > 2:
                    layer['status'] = 'unknown'
                context.set_source_rgba(.06, .06, .06, .9)
                context.rectangle(458, 326, 170, 24)
                context.fill()
                context.set_source_rgb(1, 1, 1)
                context.set_font_size(10)
                state = layer.get('transcription')
                label = (layer.get('text') or '...') if state == 'on' else {'off': '----', 'starting': 'starting...', 'error': 'STT error'}.get(state, 'STT ?')
                label = label.replace('\n', ' ').replace('\r', ' ').replace('\x00', '')
                context.save()
                context.rectangle(462, 327, 162, 13)
                context.clip()
                text_width = context.text_extents(label).width
                offset = (time.monotonic() * 30) % (text_width + 40) if text_width > 162 else 0
                context.move_to(462 - offset, 337)
                context.show_text(label)
                context.restore()
                if layer['status'] == 'on':
                    context.set_source_rgb(.24, .88, .31)
                    context.rectangle(462, 342, 162 * min(1.0, layer['level'] * 100), 5)
                    context.fill()
                continue
            if key == 'drawing':
                for x1, y1, x2, y2, color, stroke_width in layer['lines']:
                    context.set_source_rgb(*(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)))
                    context.set_line_width(max(1, stroke_width * 360 / 100))
                    context.move_to(x1 * 640 / 100, y1 * 360 / 100)
                    context.line_to(x2 * 640 / 100, y2 * 360 / 100)
                    context.stroke()
                continue
            if key == 'image':
                context.save()
                context.scale(640 / effect_width, 360 / effect_height)
                Gdk.cairo_set_source_pixbuf(context, layer['pixbuf'], layer['x'], layer['y'])
                context.paint()
                context.restore()
                continue
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
            if key in ('image', 'drawing', 'mic', 'duck'):
                continue
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

    def process_line(line):
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
                elif request.get('effect') == 'image':
                    if request.get('remove') is True:
                        layers.remove('image')
                    else:
                        install_image(request)
                elif request.get('effect') == 'drawing':
                    if request.get('clear') is True:
                        layers.remove('drawing')
                    else:
                        line = validate_line(*request['line'])
                        drawing = layers.get('drawing') or {'lines': []}
                        if len(drawing['lines']) < 2000:
                            drawing['lines'].append(line)
                            layers.put('drawing', drawing)
                elif request.get('effect') == 'mic':
                    if request.get('remove') is True:
                        layers.remove('mic')
                    elif request.get('status') in ('on', 'off', 'unknown') and isinstance(request.get('level'), (float, int)):
                        layers.put('mic', {'status': request['status'], 'level': max(0.0, min(1.0, request['level'])),
                                           'transcription': request.get('transcription', 'unknown'),
                                           'text': request.get('text', '') if isinstance(request.get('text', ''), str) else '',
                                           'updated': time.monotonic()})
                elif request.get('effect') == 'duck':
                    if request.get('remove') is True:
                        layers.remove('duck')
                    else:
                        poses = request['poses']
                        if not isinstance(poses, list) or len(poses) != 2:
                            return True
                        images = []
                        for pose in poses:
                            loader = GdkPixbuf.PixbufLoader.new_with_type('png')
                            loader.write(base64.b64decode(pose, validate=True))
                            loader.close()
                            images.append(loader.get_pixbuf().scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR))
                        layers.put('duck', {'closed': images[0], 'open': images[1], 'speaking': False, 'text': ''})
                elif request.get('effect') == 'duck_speech':
                    duck = layers.get('duck')
                    if duck and isinstance(request.get('speaking'), bool) and isinstance(text, str):
                        duck['speaking'], duck['text'] = request['speaking'], text[:300]
                elif request.get('effect') == 'duck_caption':
                    duck = layers.get('duck')
                    caption = request.get('text')
                    if duck and isinstance(caption, str):
                        duck['caption'], duck['caption_until'] = caption, time.monotonic() + 8
                elif request.get('effect') == 'duck_frame':
                    duck = layers.get('duck')
                    if duck and isinstance(request.get('png'), str):
                        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
                        loader.write(base64.b64decode(request['png'], validate=True))
                        loader.close()
                        duck['frame'] = loader.get_pixbuf().scale_simple(150, 150, GdkPixbuf.InterpType.BILINEAR)
                elif request.get('effect') == 'close':
                    key = request.get('key')
                    if key == 'all':
                        layers.clear()
                    elif isinstance(key, str):
                        layers.remove('image' if key == 'media' else key)
                    else:
                        return True
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
            except (ValueError, AttributeError, TypeError, KeyError, GLib.Error):
                pass
        return True

    pending = bytearray()

    def command(stream, condition):
        if condition & (GLib.IO_HUP | GLib.IO_ERR):
            Gtk.main_quit()
            return False
        chunk = os.read(sys.stdin.fileno(), 65536)
        if not chunk:
            Gtk.main_quit()
            return False
        pending.extend(chunk)
        while b'\n' in pending:
            line, _, rest = pending.partition(b'\n')
            pending[:] = rest
            try:
                process_line(line.decode('utf-8').strip())
            except UnicodeDecodeError:
                continue
        return True

    def install_image(request):
        def resolve(value, reference):
            if value.endswith('%'):
                return round(float(value[:-1]) * reference / 100)
            if value.lower().endswith('px'):
                return round(float(value[:-2]))
            raise ValueError('Invalid CSS length')
        w = resolve(request['width'], effect_width)
        h = resolve(request['height'], effect_height)
        x = resolve(request['x'], effect_width)
        y = resolve(request['y'], effect_height)
        if not 0 < w <= effect_width * 4 or not 0 < h <= effect_height * 4:
            raise ValueError('Invalid image dimensions')
        loader = GdkPixbuf.PixbufLoader.new_with_type('png')
        loader.write(base64.b64decode(request['png'], validate=True))
        loader.close()
        pixbuf = loader.get_pixbuf()
        scale = min(w / pixbuf.get_width(), h / pixbuf.get_height())
        pixbuf = pixbuf.scale_simple(max(1, round(pixbuf.get_width() * scale)),
                                     max(1, round(pixbuf.get_height() * scale)),
                                     GdkPixbuf.InterpType.BILINEAR)
        layers.put('image', {'pixbuf': pixbuf, 'x': x, 'y': y})

    window.connect('draw', draw)
    effect.connect('draw', draw_effect)
    window.show_all()
    window.move(max(0, screen.get_width() - 250), 10)
    window.get_window().input_shape_combine_region(cairo.Region(), 0, 0)
    GLib.io_add_watch(sys.stdin, GLib.IO_IN | GLib.IO_HUP | GLib.IO_ERR, command)
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1], len(sys.argv) > 2 and sys.argv[2] == 'screensharing',
         sys.argv[3] if len(sys.argv) > 3 else '')
