from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.message.GDT_PRE import GDT_PRE
from gdo.video.WebMedia import youtube_embed_code


class yt_embed(Method):
    @classmethod
    def gdo_trigger(cls):
        return 'video.yt.embed'

    def gdo_parameters(self):
        return [GDT_String('url').not_null().maxlen(768).positional()]

    def gdo_execute(self):
        try:
            code = youtube_embed_code(self.param_val('url'))
        except ValueError as error:
            return self.err('video_error', (str(error),))
        return GDT_PRE().add_field(GDT_String().val(code))
