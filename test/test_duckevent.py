import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.method.duckevent import duckevent
from gdo.video.method.duckanim import duckanim
from gdo.video.method.shrug import shrug
from gdo.video.method.cry import cry
from gdo.video.method.ipc_duckevent import ipc_duckevent
from gdo.video.StarWarsIPC import decode_text
from gdo.video.module_video import module_video


class DuckEventTest(unittest.IsolatedAsyncioTestCase):
    def test_duckanim_requires_admin(self):
        self.assertEqual('admin', duckanim().gdo_user_permission())

    def setUp(self):
        Application.mode(Mode.render_cli)
        self.base_override = patch.object(duckanim, 'param_value', return_value=False)
        self.base_override.start()
        self.addCleanup(self.base_override.stop)
        self.mira_notice = patch('gdo.mira.util.send_to_mira')
        self.send_to_mira = self.mira_notice.start()
        self.addCleanup(self.mira_notice.stop)
        self.current_user = patch.object(Application, 'get_current_user', return_value=MagicMock(get_name_sid=MagicMock(return_value='gizmore{bash}')))
        self.current_user.start()
        self.addCleanup(self.current_user.stop)

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

    def test_ouch_animation_is_temporary_event(self):
        method = duckanim()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'ouch', 'text': None}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['ouch'])
        self.send_to_mira.assert_called_once_with('$duck.anim ouch (requested by "gizmore{bash}"; animation request queued for Dog)', interrupt=False)

    def test_duckanim_suppresses_acknowledgement_only_in_dog(self):
        method = duckanim()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'music', 'text': None}[key])
        method.reply = MagicMock(return_value='queued')
        method.empty = MagicMock(return_value='')
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            with patch.object(Application, 'IS_DOG', True):
                self.assertEqual('', method.gdo_execute())
            with patch.object(Application, 'IS_DOG', False):
                self.assertEqual('queued', method.gdo_execute())
        self.assertEqual(2, send.call_count)
        method.empty.assert_called_once_with()
        method.reply.assert_called_once_with('video_duckanim_queued')

    def test_hello_animation_is_temporary_event(self):
        method = duckanim()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'hello', 'text': None}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['hello'])

    def test_teacher_is_temporary_event(self):
        method = duckanim()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'teacher', 'text': None}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['teacher'])

    def test_notification_waits_for_transaction_commit(self):
        method = duckanim()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'hello', 'text': None}[key])
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = True
        with patch.object(Application, 'db', return_value=db), \
                patch.object(Application, 'defer_after_commit') as deferred, \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.gdo_execute()
            self.send_to_mira.assert_not_called()
            send.assert_not_called()
            callback, *args = deferred.call_args.args
            callback(*args)
            send.assert_called_once_with('video.ipc_duckevent', ['hello'])
            self.send_to_mira.assert_called_once_with('$duck.anim hello (requested by "gizmore{bash}"; animation request queued for Dog)', interrupt=False)

    def test_rolleye_supports_optional_speech(self):
        method = duckanim()
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.param_val = MagicMock(side_effect=lambda key: {'key': 'rolleye', 'text': None}[key])
            method.gdo_execute()
            send.assert_called_with('video.ipc_duckevent', ['rolleye'])
            method.param_val = MagicMock(side_effect=lambda key: {'key': 'rolleye', 'text': 'Ach wirklich?', 'lang': 'de'}[key])
            method.gdo_execute()
            name, args = send.call_args.args
            self.assertEqual(name, 'video.ipc_duckanim_speech')
            self.assertEqual(args[0], 'rolleye')
            self.assertEqual(decode_text(args[1]), 'Ach wirklich?')
            self.assertEqual(args[2], 'de')

    def test_plz_and_base_modes_forward_optional_speech(self):
        method = duckanim()
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            for key in ('plz', 'xd', 'sorry', 'nerd', 'cast', 'zombie', 'giveup', 'rich', 'anon', 'king', 'turnaround', 'shiver', 'rambo', 'hippi', 'metal', 'ninja', 'news', 'quacking'):
                method.param_val = MagicMock(side_effect=lambda name: {'key': key, 'text': 'Please!', 'lang': 'en'}[name])
                method.gdo_execute()
                name, args = send.call_args.args
                self.assertEqual('video.ipc_duckanim_speech', name)
                self.assertEqual(key, args[0])
                self.assertEqual('Please!', decode_text(args[1]))
                self.send_to_mira.assert_called_with(f'$duck.anim {key} (requested by "gizmore{{bash}}"; animation request queued for Dog)\nSpeech text: "Please!"', interrupt=False)

    def test_giveup_is_temporary_event_without_speech(self):
        method = duckanim()
        method.reply = MagicMock()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'giveup', 'text': None}[key])
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_duckevent', ['giveup'])

    def test_default_and_explicit_base_routing(self):
        from gdo.video.DuckAnimations import BASE_DEFAULTS
        self.assertFalse(BASE_DEFAULTS['barf'])
        self.assertTrue(BASE_DEFAULTS['cast'])
        self.assertGreater(sum(BASE_DEFAULTS.values()), len(BASE_DEFAULTS) / 2)
        method = duckanim()
        method.reply = MagicMock()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'barf', 'text': None}[key])
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.duckanim.IPC.send_to_dog') as send:
            with patch.object(method, 'param_value', return_value=None):
                method.gdo_execute()
            send.assert_called_with('video.ipc_duckevent', ['barf'])
            with patch.object(method, 'param_value', return_value=True):
                method.gdo_execute()
            send.assert_called_with('video.ipc_duckbase', ['barf', '-', '-'])
            method.param_val = MagicMock(side_effect=lambda key: {'key': 'music', 'text': None}[key])
            with patch.object(method, 'param_value', return_value=False):
                method.gdo_execute()
            send.assert_called_with('video.ipc_duckevent', ['music'])
            method.param_val = MagicMock(side_effect=lambda key: {'key': 'cast', 'text': None}[key])
            with patch.object(method, 'param_value', return_value=None):
                method.gdo_execute()
            send.assert_called_with('video.ipc_duckbase', ['cast', '-', '-'])
            with patch.object(method, 'param_value', return_value=False):
                method.gdo_execute()
            send.assert_called_with('video.ipc_duckevent', ['cast'])

    async def test_base_ipc_stores_key_and_keeps_it_after_speech(self):
        from gdo.video.method.ipc_duckbase import ipc_duckbase
        from gdo.video.StarWarsIPC import encode_text
        method = ipc_duckbase()
        method.param_val = MagicMock(side_effect=lambda key: {'key': 'barf', 'payload': encode_text('Hi'), 'lang': 'en'}[key])
        method.empty = MagicMock()
        video = MagicMock()
        video._duck_event_task = None
        mira = MagicMock()
        mira.save_config_val = AsyncMock()
        speech = MagicMock()
        speech.input.return_value = speech
        speech.play = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duckbase.module_video.instance', return_value=video), \
                patch('gdo.video.method.ipc_duckbase.module_mira.instance', return_value=mira), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await method.play()
        mira.save_config_val.assert_awaited_once_with('mira_mood', 'barf', force=True)
        video.connector.duck_animation.assert_called_once_with('barf')
        speech.play.assert_awaited_once()

    async def test_plz_speech_starts_event_and_speaks(self):
        from gdo.video.method.ipc_duckanim_speech import ipc_duckanim_speech
        from gdo.video.StarWarsIPC import encode_text
        method = ipc_duckanim_speech()
        method.param_val = MagicMock(side_effect=lambda name: {'key': 'plz', 'payload': encode_text('Please!'), 'lang': 'en'}[name])
        video = MagicMock()
        speech = MagicMock()
        speech.input.return_value = speech
        speech.play = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duckanim_speech.module_video.instance', return_value=video), \
                patch('gdo.audio.method.ipc_say.ipc_say', return_value=speech):
            await method.play()
        video.duck_event.assert_called_once_with('plz', duration=None)
        video.finish_duck_event.assert_called_once_with(video.duck_event.return_value)
        speech.input.assert_any_call('text', 'Please!')
        speech.play.assert_awaited_once()

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

    def test_cry_optional_text_routes_correctly(self):
        method = cry()
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch.object(Application, 'db', return_value=db), \
                patch('gdo.video.method.shrug.IPC.send_to_dog') as send:
            method.param_val = MagicMock(return_value=None)
            method.gdo_execute()
            send.assert_called_with('video.ipc_duckevent', ['cry'])
            method.param_val = MagicMock(side_effect=lambda key: {'text': 'Oh nein!', 'lang': 'de'}[key])
            method.gdo_execute()
            name, args = send.call_args.args
            self.assertEqual(name, 'video.ipc_duckcry')
            self.assertEqual(decode_text(args[0]), 'Oh nein!')
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

    async def test_speech_event_does_not_restore_over_newer_event(self):
        module = module_video()
        module.connector = MagicMock()
        old = module.duck_event('plz', duration=None)
        new = module.duck_event('hello', duration=None)
        module.finish_duck_event(old)
        self.assertIs(new, module._duck_event_task)
        self.assertEqual(['plz', 'hello'], [call.args[0] for call in module.connector.duck_animation.call_args_list])
        mira = MagicMock()
        mira.cfg_mira_mood.return_value = 'sad'
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=mira))):
            module.finish_duck_event(new)
        self.assertEqual('sad', module.connector.duck_animation.call_args.args[0])
        await asyncio.sleep(0)

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

    async def test_cry_event_sets_sad_base(self):
        method = ipc_duckevent()
        method.param_val = MagicMock(return_value='cry')
        method.empty = MagicMock()
        mira = MagicMock()
        mira.save_config_val = AsyncMock()
        video = MagicMock()
        with patch.object(Application, 'IS_DOG', True), \
                patch('gdo.video.method.ipc_duckevent.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=mira))), \
                patch('gdo.video.method.ipc_duckevent.module_video.instance', return_value=video):
            await method.gdo_execute()
        mira.save_config_val.assert_awaited_once_with('mira_mood', 'sad')
        video.duck_event.assert_called_once_with('cry')
