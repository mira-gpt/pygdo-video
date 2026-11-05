from gdo.base.Method import Method
from gdo.core.GDT_RestOfText import GDT_RestOfText
from gdo.video.module_video import module_video


class starwars(Method):
    def gdo_user_permission(self):
        return 'owner'

    def gdo_parameters(self):
        return [GDT_RestOfText('text').not_null().tooltip('tt_video_starwars_text')]

    def gdo_execute(self):
        try:
            module_video.instance().connector.starwars(self.param_value('text'))
        except (ValueError, RuntimeError, OSError) as exc:
            return self.err('video_error', (str(exc),))
        return self.reply('video_starwars_started')
