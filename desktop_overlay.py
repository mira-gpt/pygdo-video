"""GTK 3 X11 helper: an image in a transparent click-through desktop window."""

import sys
import base64
import json
import math
import os
import random
import textwrap
import time

import cairo
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Pango, PangoCairo
from LayerStack import LayerStack, PERSISTENT_LAYERS
from DrawingProtocol import validate_line
from MediaTransition import media_transition
from CRTOff import crt_state
from TranscriptFade import transcript_alpha
from MicWarning import MicWarning
from MicTicker import TickerScroll
from TickerLayout import ticker_bounds, next_message_x, COMMENTARY_SPEED
from AwayScreen import AwayScreen, HEADER


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
    show_state = {'liveshow': False, 'ticker_ack': None, 'ticker_scroll': TickerScroll(), 'thoughts_scroll': TickerScroll(COMMENTARY_SPEED), 'thoughts_ack': None}

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
            if key == 'live_indicator':
                context.save()
                context.select_font_face('Sans', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
                context.set_font_size(16)
                context.move_to(10, 25)
                context.text_path(layer['mode'])
                context.set_source_rgb(1, 1, 1)
                context.set_line_width(2)
                context.stroke_preserve()
                context.set_source_rgb(*( (0.86, 0, 0) if layer['active'] else (0, 0, 0) ))
                context.fill()
                context.restore()
                continue
            if key == 'away':
                context.set_source_rgba(0, 0, 0, .28)
                context.rectangle(0, 0, 640, 360)
                context.fill()
                for text, font, centered in ((HEADER, 'Sans Bold 13px', False),
                                             (layer.current(), 'Sans Bold 24px', True)):
                    layout = PangoCairo.create_layout(context)
                    layout.set_font_description(Pango.FontDescription(font))
                    layout.set_width(600 * Pango.SCALE)
                    layout.set_height(150 * Pango.SCALE)
                    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                    layout.set_ellipsize(Pango.EllipsizeMode.END)
                    layout.set_alignment(Pango.Alignment.CENTER)
                    layout.set_text(text, -1)
                    _, text_height = layout.get_pixel_size()
                    y = (360 - text_height) / 2 if centered else 18
                    context.move_to(20, y)
                    PangoCairo.layout_path(context, layout)
                    context.set_source_rgba(0, 0, 0, .95)
                    context.set_line_width(3)
                    context.stroke_preserve()
                    context.set_source_rgb(1, 1, 1)
                    context.fill()
                continue
            if key == 'crt_off':
                state = crt_state(time.monotonic() - layer['start'], layer['duration'])
                if state:
                    sx, sy, brightness = state
                    context.set_source_rgb(0, 0, 0)
                    context.rectangle(0, 0, 640, 360)
                    context.fill()
                    context.set_source_rgb(brightness, brightness, brightness)
                    w, h = max(2, 640 * sx), max(2, 360 * sy)
                    context.rectangle((640 - w) / 2, (360 - h) / 2, w, h)
                    context.fill()
                continue
            if key == 'zap':
                for y in range(0, 360, 6):
                    for x in range(0, 640, 6):
                        shade = random.random()
                        context.set_source_rgb(shade, shade, shade)
                        context.rectangle(x, y, 6, 6)
                        context.fill()
                continue
            if key == 'duck':
                context.save()
                pixbuf = layer.get('frame') or (layer['open'] if layer['speaking'] and int(time.monotonic() * 6) % 2 else layer['closed'])
                # Move the duck down by 32 physical screen pixels, even when
                # the overlay is scaled from its 640x360 logical canvas.
                duck_x = 245 if os.environ.get('MIRA_DUCK_POSITION') == 'center' else 480
                Gdk.cairo_set_source_pixbuf(context, pixbuf, duck_x, 165 + 32 * 360 / effect_height)
                context.paint()
                caption = layer['text'] if layer['speaking'] else layer.get('caption', '') if time.monotonic() < layer.get('caption_until', 0) else ''
                if caption:
                    layout = PangoCairo.create_layout(context)
                    layout.set_font_description(Pango.FontDescription('Sans Bold 15px'))
                    layout.set_width(608 * Pango.SCALE)
                    layout.set_height(-4)
                    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                    layout.set_ellipsize(Pango.EllipsizeMode.END)
                    layout.set_text(caption, -1)
                    _, text_height = layout.get_pixel_size()
                    context.set_source_rgba(.05, .05, .08, .9)
                    context.rectangle(10, 10, 620, 12 + text_height)
                    context.fill()
                    context.set_source_rgb(1, 1, 1)
                    context.move_to(16, 16)
                    PangoCairo.show_layout(context, layout)
                context.restore()
                continue
            if key == 'thoughts':
                mic_left, _ = ticker_bounds(640)
                commentary = layer.get('text') or 'Mira: ...'
                now = time.monotonic()
                sequence = layer.get('sequence')
                context.set_source_rgba(.06, .06, .06, .9)
                context.rectangle(12, 326, mic_left - 20, 24)
                context.fill()
                context.save()
                context.rectangle(16, 327, mic_left - 28, 20)
                context.clip()
                layout = PangoCairo.create_layout(context)
                layout.set_font_description(Pango.FontDescription('Sans 10px'))
                layout.set_text(commentary, -1)
                commentary_width, _ = layout.get_pixel_size()
                offset, done = show_state['thoughts_scroll'].frame(sequence, now, commentary_width) if sequence is not None else (0, False)
                context.move_to(16 - offset, 330)
                context.set_source_rgb(1, 1, 1)
                PangoCairo.show_layout(context, layout)
                next_text = layer.get('next', '')
                if sequence is not None and next_text:
                    separator = PangoCairo.create_layout(context)
                    separator.set_font_description(Pango.FontDescription('Sans 10px'))
                    separator.set_text(' || ', -1)
                    separator_width, _ = separator.get_pixel_size()
                    x = next_message_x(mic_left - 28, commentary_width, offset, show_state['thoughts_scroll'].elapsed, separator_width)
                    context.move_to(16 + x - separator_width, 330)
                    PangoCairo.show_layout(context, separator)
                    following = PangoCairo.create_layout(context)
                    following.set_font_description(Pango.FontDescription('Sans 10px'))
                    following.set_text(next_text, -1)
                    context.move_to(16 + x, 330)
                    PangoCairo.show_layout(context, following)
                context.restore()
                if done and show_state['thoughts_ack'] != sequence:
                    show_state['thoughts_ack'] = sequence
                    print(json.dumps({'event': 'thoughts_finished', 'sequence': sequence}), flush=True)
                continue
            if key == 'mic':
                if layer['status'] == 'on' and time.monotonic() - layer['updated'] > 2:
                    layer['status'] = 'unknown'
                context.set_source_rgba(.06, .06, .06, .9)
                mic_left, mic_right = ticker_bounds(640)
                mic_width = mic_right - mic_left
                text_left, text_width_available = mic_left + 4, mic_width - 8
                context.rectangle(mic_left, 326, mic_width, 24)
                context.fill()
                if show_state['liveshow']:
                    context.set_source_rgb(1, .12, .12)
                    context.set_line_width(2)
                    context.rectangle(mic_left + 1, 327, mic_width - 2, 22)
                    context.stroke()
                context.set_source_rgb(1, 1, 1)
                context.set_font_size(10)
                state = layer.get('transcription')
                language = layer.get('language', '')
                placeholder = f'STT {language}' if language else 'STT ?'
                label = (layer.get('text') or placeholder) if state == 'on' else {'off': '----', 'starting': 'starting...', 'error': 'STT error'}.get(state, 'STT ?')
                alpha = transcript_alpha(time.monotonic(), layer.get('text_updated', 0)) if state == 'on' and layer.get('text') else 1.0
                if alpha == 0:
                    label, alpha = placeholder, 1.0
                ticker = layer.get('ticker', '')
                if ticker:
                    label, alpha = ticker, 1.0
                warning = layer['warning'].update(layer['status'], layer['level'], time.monotonic(), layer['warning_texts'])
                if warning and not ticker:
                    label, alpha = warning, 1.0
                label = label.replace('\n', ' ').replace('\r', ' ').replace('\x00', '')
                context.save()
                context.rectangle(text_left, 327, text_width_available, 13)
                context.clip()
                layout = PangoCairo.create_layout(context)
                layout.set_font_description(Pango.FontDescription('Sans 10px'))
                layout.set_text(label, -1)
                text_width, _ = layout.get_pixel_size()
                now = time.monotonic()
                ticker_done = False
                if ticker:
                    offset, ticker_done = show_state['ticker_scroll'].frame(layer['ticker_started'], now, text_width)
                else:
                    offset = (now * 30) % (text_width + 40) if text_width > text_width_available else 0
                context.move_to(text_left - offset, 327)
                context.set_source_rgba(1, 1, 1, alpha)
                PangoCairo.show_layout(context, layout)
                context.restore()
                if ticker and show_state['ticker_ack'] != layer['ticker_started'] and ticker_done:
                    show_state['ticker_ack'] = layer['ticker_started']
                    print(json.dumps({'event': 'ticker_finished', 'started': layer['ticker_started']}), flush=True)
                if layer['status'] == 'on':
                    context.set_source_rgb(.24, .88, .31)
                    context.rectangle(text_left, 342, text_width_available * min(1.0, layer['level'] * 100), 5)
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
                pixbuf = layer['pixbuf']
                x, y, angle, alpha = media_transition(layer.get('transition'), time.monotonic() - layer['start'], effect_width, layer['x'], layer['y'])
                context.translate(x + pixbuf.get_width() / 2, y + pixbuf.get_height() / 2)
                context.rotate(-math.radians(angle))
                Gdk.cairo_set_source_pixbuf(context, pixbuf, -pixbuf.get_width() / 2, -pixbuf.get_height() / 2)
                context.paint_with_alpha(alpha)
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
            if key == 'crt_off':
                if crt_state(time.monotonic() - layer['start'], layer['duration']) is None:
                    layers.remove(key)
                continue
            if key == 'zap':
                if time.monotonic() >= layer['end']:
                    layers.remove(key)
                continue
            if key in PERSISTENT_LAYERS:
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
                elif request.get('effect') == 'zap' and isinstance(request.get('duration'), (int, float)) and .05 <= request['duration'] <= 30:
                    layers.put('zap', {'end': time.monotonic() + request['duration']}, z=10000)
                elif request.get('effect') == 'crt_off' and isinstance(request.get('duration'), (int, float)) and 0 <= request['duration'] <= 60:
                    layers.put('crt_off', {'start': time.monotonic(), 'duration': request['duration']}, z=10001)
                elif request.get('effect') == 'away':
                    layers.put('away', AwayScreen(request.get('messages'), request.get('cycle')), z=9000)
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
                elif request.get('effect') == 'liveshow' and isinstance(request.get('enabled'), bool):
                    show_state['liveshow'] = request['enabled']
                elif request.get('effect') == 'live_indicator' and request.get('mode') in ('off', 'work', 'show', 'discuss', 'cohost') and isinstance(request.get('active'), bool):
                    layers.put('live_indicator', {'mode': request['mode'], 'active': request['active']}, z=8000)
                elif request.get('effect') == 'thoughts':
                    if request.get('remove') is True:
                        layers.remove('thoughts')
                    else:
                        text = request.get('text', '')
                        sequence = request.get('sequence')
                        next_text = request.get('next', '')
                        layers.put('thoughts', {'text': text if isinstance(text, str) else '', 'sequence': sequence if type(sequence) is int else None,
                                                'next': next_text if isinstance(next_text, str) else ''})
                elif request.get('effect') == 'mic':
                    if request.get('remove') is True:
                        layers.remove('mic')
                    elif request.get('status') in ('on', 'off', 'unknown') and isinstance(request.get('level'), (float, int)):
                        previous = layers.get('mic') or {}
                        texts = request.get('warning_texts', [])
                        if not isinstance(texts, list) or not all(isinstance(item, str) for item in texts):
                            texts = []
                        layers.put('mic', {'status': request['status'], 'level': max(0.0, min(1.0, request['level'])),
                                           'warning': previous.get('warning', MicWarning()), 'warning_texts': texts,
                                           'ticker': request.get('ticker', '') if isinstance(request.get('ticker', ''), str) else '',
                                           'ticker_started': request.get('ticker_started', 0) if isinstance(request.get('ticker_started', 0), (int, float)) else 0,
                                           'transcription': request.get('transcription', 'unknown'),
                                           'language': request.get('language', '') if isinstance(request.get('language', ''), str) else '',
                                           'text': request.get('text', '') if isinstance(request.get('text', ''), str) else '',
                                           'text_updated': request.get('text_updated', 0) if isinstance(request.get('text_updated', 0), (int, float)) else 0,
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
                    elif key == 'presentation':
                        for name, _ in layers.ordered():
                            if name not in ('duck', 'mic'):
                                layers.remove(name)
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
        previous = layers.get('image')
        reset = request.get('transition_start') is True or not previous
        transition = request.get('transition')
        if transition not in (None, 'fade', 'throw'):
            raise ValueError('Invalid media transition')
        layers.put('image', {'pixbuf': pixbuf, 'x': x, 'y': y,
                             'transition': transition if reset else previous['transition'],
                             'start': time.monotonic() if reset else previous['start']})

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
