import asyncio
import subprocess

from gdo.base.Method import Method
from gdo.core.GDT_String import GDT_String
from gdo.video.AsciiIBDES import encode_video


class al_encode(Method):
    @classmethod
    def gdo_trigger(cls):
        return 'video.al.encode'

    def gdo_user_permission(self):
        return 'owner'

    def gdo_needs_authentication(self):
        return True

    def gdo_connectors(self):
        return 'bash'

    def gdo_transactional(self):
        return False

    def gdo_parameters(self):
        return [GDT_String('source').not_null().positional(),
                GDT_String('output').not_null().positional()]

    async def gdo_execute(self):
        try:
            count = await asyncio.to_thread(encode_video, self.param_val('source'), self.param_val('output'))
            return self.reply('video_al_encoded', (count,))
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            return self.err('video_error', (str(error),))
