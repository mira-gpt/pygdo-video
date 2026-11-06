from gdo.video.method.shrug import shrug


class cry(shrug):
    animation = 'cry'
    speech_method = 'video.ipc_duckcry'

    @classmethod
    def gdo_trig(cls):
        return 'duck.cry'
