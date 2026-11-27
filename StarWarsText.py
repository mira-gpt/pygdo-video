import gi

gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo


def draw_line(context, text, y):
    layout = PangoCairo.create_layout(context)
    layout.set_font_description(Pango.FontDescription(f'Sans Bold {max(10, int(12 + 15 * max(0, y) / 360))}px'))
    layout.set_width(640 * Pango.SCALE)
    layout.set_alignment(Pango.Alignment.CENTER)
    layout.set_text(text, -1)
    context.move_to(0, y)
    PangoCairo.show_layout(context, layout)
    return layout.get_unknown_glyphs_count()
