from gdo.base.Method import Method
from gdo.message.GDT_Bold import GDT_Bold
from gdo.message.GDT_Glyph import GDT_Glyph
from gdo.message.GDT_Italic import GDT_Italic
from gdo.message.GDT_Span import GDT_Span
from gdo.mira.GDT_MiraMood import GDT_MiraMood
from gdo.mira.module_mira import module_mira


class duckmoods(Method):
    @classmethod
    def gdo_trig(cls):
        return 'duck.moods'

    def gdo_execute(self):
        current = module_mira.instance().cfg_mira_mood()
        base = tuple(GDT_MiraMood().init_choices())
        events = ('lol', 'shrug', 'cry', 'ouch', 'hello', 'rolleye', 'barf', 'plz')
        output = GDT_Span().add_field(GDT_Glyph('Duck moods: '))
        for index, key in enumerate((*base, *events)):
            if index:
                output.add_field(GDT_Glyph(', '))
            item = GDT_Glyph(key)
            if key in base:
                item = GDT_Italic().add_field(item)
            if key == current:
                item = GDT_Bold().add_field(item)
            output.add_field(item)
        return output
