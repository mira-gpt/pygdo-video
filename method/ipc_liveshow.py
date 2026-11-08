from gdo.base.Application import Application
from gdo.base.Logger import Logger
from gdo.base.IPC import IPC
from gdo.base.Method import Method
from gdo.base.ModuleLoader import ModuleLoader
from gdo.mira.GDT_MiraLiveMode import GDT_MiraLiveMode


class ipc_liveshow(Method):
    @classmethod
    def gdo_trigger(cls):
        return ''

    def gdo_parameters(self):
        return [GDT_MiraLiveMode('mode').not_null().positional()]

    async def gdo_execute(self):
        if Application.IS_DOG:
            try:
                mira = ModuleLoader.instance().get_module('mira')
                if not mira:
                    raise ValueError('Mira module is required for liveshow mode')
                mode = self.param_val('mode')
                if mode not in GDT_MiraLiveMode.MODES:
                    raise ValueError('Invalid live mode')
                enabled = mode == 'show'
                previous = mira.cfg_mira_livemode() == 'show'
                await mira.save_config_val('mira_livemode', mode, force=True)
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
