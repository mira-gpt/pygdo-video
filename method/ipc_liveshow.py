from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.core.GDT_Bool import GDT_Bool


class ipc_liveshow(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_Bool('enabled').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                mira = ModuleLoader.instance().get_module('mira')
                if not mira:
                    raise ValueError('Mira module is required for liveshow mode')
                enabled = bool(self.param_value('enabled'))
                previous = bool(mira.get_config_value('mira_quacking'))
                await mira.save_config_val('mira_quacking', '1' if enabled else '0', force=True)
                for event in ('video.ipc_duck3d', 'video.ipc_mic'):
                    try:
                        await IPC.execute_dog_event(event, ['1' if enabled else '0'])
                    except (ValueError, RuntimeError, OSError, AttributeError) as error:
                        Logger.warning(f'Live show overlay {event} failed: {error}')
                if enabled != previous:
                    notice = ('Live show mode is on: the desktop may be streamed, and messages in this channel may be visible to viewers.'
                              if enabled else 'Live show mode is off. This notice does not independently confirm that streaming has stopped.')
                    await IPC.execute_dog_event('chat.shout', [notice])
            except (ValueError, RuntimeError, OSError, AttributeError) as error:
                Logger.warning(f'Live show mode failed: {error}')
        return self.empty()
