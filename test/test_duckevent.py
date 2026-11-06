import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.duckevent import duckevent
from gdo.video.method.shrug import shrug
from gdo.video.method.ipc_duckevent import ipc_duckevent
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class DuckEventTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_public_method_normalizes_and_queues(self):
        method = duckevent()
        method.param_val = MagicMock(return_value='LOL')
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckevent.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['lol'])

    def test_shrug_queues_temporary_event(self):
        method = shrug()
        method.param_val = MagicMock(return_value=None)
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.shrug.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['shrug'])

    def test_shrug_speech_preserves_text_and_language(self):
        method = shrug()
        method.param_val = MagicMock(side_effect=lambda key: {'text': 'Oh nein, ein Test!', 'lang': 'de'}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.shrug.IPC.send_to_dog') as send:
            method.gdo_execute()
        name, args = send.call_args.args
        self.assertEqual(name, 'video.ipc_duckshrug')
        self.assertEqual(decode_text(args[0]), 'Oh nein, ein Test!')
        self.assertEqual(args[1], 'de')

    async def test_replacement_cancels_old_timer_and_restores_latest_mood(self):
        module = module_video()
        connector = MagicMock()
        module.connector = connector
        mira = MagicMock()
        mira.cfg_mira_mood.return_value = 'quacking'
        loader = MagicMock()
        loader.get_module.return_value = mira
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=loader):
            module.duck_event('lol', duration=.04)
            await asyncio.sleep(.01)
            module.duck_event('idle', duration=.08)
            field = MagicMock()
            field.get_val.return_value = 'quacking'
            await module.on_mira_mood_changed(mira, field)
            await asyncio.sleep(.05)
            self.assertEqual(['lol', 'idle'], [c.args[0] for c in connector.duck_animation.call_args_list])
            await asyncio.sleep(.06)
        self.assertEqual(['lol', 'idle', 'quacking'], [c.args[0] for c in connector.duck_animation.call_args_list])

    async def test_old_event_does_not_change_replaced_connector(self):
        module = module_video()
        old = MagicMock()
        module.connector = old
        module.duck_event('lol', duration=.01)
        module.connector = MagicMock()
        await asyncio.sleep(.04)
        old.duck_animation.assert_called_once_with('lol')

    async def test_lol_event_changes_sad_base(self):
        method = ipc_duckevent()
        method.param_val = MagicMock(return_value='lol')
        method.empty = MagicMock()
        mira = MagicMock()
        mira.cfg_mira_mood.return_value = 'sad'
        mira.save_config_val = AsyncMock()
        video = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duckevent.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=mira))), \
                patch('gdo.video.method.ipc_duckevent.module_video.instance', return_value=video):
            await method.gdo_execute()
        mira.save_config_val.assert_awaited_once_with('mira_mood', 'idle')
        video.duck_event.assert_called_once_with('lol')
