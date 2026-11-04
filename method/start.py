from gdo.base.Method import Method


class start(Method):
    def gdo_user_permission(self):
        return 'owner'

    async def gdo_execute(self):
        # The old single-source renderer cannot safely consume a multi-source
        # configuration. Keep capture disabled until composition is designed.
        return self.err('video_composition_pending')
