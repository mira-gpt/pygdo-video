"""Interactive WebKit desktop media window, isolated from browser profiles."""
import sys
import time
import math

import cairo

import gi
gi.require_foreign('cairo')
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import GLib, Gtk, WebKit2

from WebMedia import document_for, validate_url
from MediaTransition import media_transition


def main(url, x, y, width, height, transition):
    validate_url(url)
    window = Gtk.Window(title='PyGDO Media')
    window.set_default_size(width, height)
    window.set_keep_above(True)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    window.add(box)
    header = Gtk.HeaderBar(title='Media — drag to move')
    header.set_show_close_button(True)
    window.set_titlebar(header)
    window.move(x, y)
    context = WebKit2.WebContext.new_ephemeral()
    view = WebKit2.WebView.new_with_context(context)
    settings = view.get_settings()
    settings.set_allow_file_access_from_file_urls(False)
    settings.set_allow_universal_access_from_file_urls(False)
    settings.set_media_playback_requires_user_gesture(True)
    def deny_permission(_view, request):
        request.deny()
        return True
    view.connect('permission-request', deny_permission)
    def decide_policy(_view, decision, kind):
        if kind == WebKit2.PolicyDecisionType.NAVIGATION_ACTION:
            uri = decision.get_navigation_action().get_request().get_uri()
            if uri and uri.startswith('file:') and not url.startswith('file:'):
                decision.ignore()
                return True
        if kind == WebKit2.PolicyDecisionType.NEW_WINDOW_ACTION:
            decision.ignore()
            return True
        return False
    view.connect('decide-policy', decide_policy)
    box.pack_start(view, True, True, 0)
    window.connect('destroy', Gtk.main_quit)
    if transition == 'cyclone':
        window.set_opacity(0)
        state = {'started': False, 'done': False, 'preview': None}

        def finish():
            if state['done']:
                return False
            state['done'] = True
            if state['preview']:
                state['preview'].destroy()
            window.set_opacity(1)
            window.present()
            return False

        def got_snapshot(webview, result, _data):
            if state['done']:
                return
            try:
                snapshot = webview.get_snapshot_finish(result)
                if snapshot is None:
                    finish()
                    return
            except Exception:
                finish()
                return
            screen = window.get_screen()
            visual = screen.get_rgba_visual()
            if not visual or not screen.is_composited():
                finish()
                return
            sw, sh = snapshot.get_width(), snapshot.get_height()
            side = math.ceil(math.hypot(sw, sh))
            preview = Gtk.Window(type=Gtk.WindowType.POPUP)
            state['preview'] = preview
            preview.set_visual(visual)
            preview.set_app_paintable(True)
            preview.set_keep_above(True)
            preview.set_default_size(side, side)
            preview.move(round(x + sw / 2 - side / 2), round(y + sh / 2 - side / 2))
            started = time.monotonic()

            def draw(_widget, cr):
                cr.set_operator(cairo.OPERATOR_SOURCE)
                cr.set_source_rgba(0, 0, 0, 0)
                cr.paint()
                cr.set_operator(cairo.OPERATOR_OVER)
                progress = min(1.0, (time.monotonic() - started) / 2.0)
                eased = 1 - (1 - progress) ** 3
                cr.translate(side / 2, side / 2)
                cr.rotate((1 - eased) * math.pi * 4)
                cr.set_source_surface(snapshot, -sw / 2, -sh / 2)
                cr.paint()
                return False

            preview.connect('draw', draw)
            preview.show_all()
            def tick():
                if time.monotonic() - started >= 2:
                    return finish()
                preview.queue_draw()
                return True
            GLib.timeout_add(16, tick)

        def on_load(webview, event):
            if event == WebKit2.LoadEvent.FINISHED and not state['started']:
                state['started'] = True
                webview.get_snapshot(WebKit2.SnapshotRegion.VISIBLE,
                                     WebKit2.SnapshotOptions.TRANSPARENT_BACKGROUND,
                                     None, got_snapshot, None)
        view.connect('load-changed', on_load)
        GLib.timeout_add_seconds(12, finish)

    document = document_for(url)
    if document is None:
        view.load_uri(url)
    else:
        view.load_html(document, None)
    window.show_all()
    started = time.monotonic()
    if transition == 'fade':
        window.set_opacity(0)
    def animate():
        elapsed = time.monotonic() - started
        progress = min(1.0, elapsed / (2.0 if transition == 'cyclone' else (1.2 if transition == 'throw' else .8)))
        eased = 1 - (1 - progress) ** 3
        if transition == 'cyclone':
            px, py, _, _ = media_transition('cyclone', elapsed, width, x, y)
            window.move(round(px), round(py))
        elif transition == 'throw':
            window.move(round(x - (width + x) * (1 - eased)), y)
        else:
            window.move(x, y)
            window.set_opacity(eased)
        return progress < 1
    if transition != 'cyclone':
        GLib.timeout_add(16, animate)
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1], *(int(value) for value in sys.argv[2:6]), sys.argv[6])
