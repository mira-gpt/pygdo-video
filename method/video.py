from gdo.core.ModuleCommandList import ModuleCommandList


class video(ModuleCommandList):
    @classmethod
    def gdo_trigger(cls):
        return 'video'
