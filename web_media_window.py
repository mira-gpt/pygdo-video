"""Interactive WebKit desktop media window, isolated from browser profiles."""
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import GLib, Gtk, WebKit2

from WebMedia import document_for, validate_url


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
        progress = min(1.0, (time.monotonic() - started) / (1.2 if transition == 'throw' else .8))
        eased = 1 - (1 - progress) ** 3
        if transition == 'throw':
            window.move(round(x - (width + x) * (1 - eased)), y)
        else:
            window.move(x, y)
            window.set_opacity(eased)
        return progress < 1
    GLib.timeout_add(16, animate)
    Gtk.main()


if __name__ == '__main__':
    main(sys.argv[1], *(int(value) for value in sys.argv[2:6]), sys.argv[6])
