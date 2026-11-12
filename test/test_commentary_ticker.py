import json
import os
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from gdo.video.CommentaryTicker import CommentaryTicker
from gdo.video.CommentaryFollower import commentary


class CommentaryTickerTest(unittest.TestCase):
    def test_gtk_keeps_thoughts_layer_during_animation(self):
        from gdo.video.LayerStack import PERSISTENT_LAYERS
        self.assertIn('thoughts', PERSISTENT_LAYERS)

    def tearDown(self):
        CommentaryTicker.clear()

    def test_only_assistant_commentary_is_forwarded(self):
        payload = {'type': 'message', 'role': 'assistant', 'phase': 'commentary', 'content': [{'type': 'output_text', 'text': 'Hello\nworld'}]}
        event = {'type': 'response_item', 'payload': payload}
        self.assertEqual('Hello world', commentary(json.dumps(event)))
        payload['phase'] = 'final_answer'
        self.assertEqual('Hello world', commentary(json.dumps(event)))
        for role, phase in [('user', 'commentary'), ('assistant', 'analysis')]:
            payload.update(role=role, phase=phase)
            self.assertIsNone(commentary(json.dumps(event)))
        self.assertIsNone(commentary('not json'))

    def test_fifo_waits_for_matching_renderer_ack(self):
        CommentaryTicker.set('First')
        CommentaryTicker.set('Second')
        text, sequence = CommentaryTicker.snapshot()
        self.assertEqual('First', text)
        self.assertFalse(CommentaryTicker.finish(sequence + 1))
        self.assertEqual(('First', sequence), CommentaryTicker.snapshot())
        self.assertTrue(CommentaryTicker.finish(sequence))
        self.assertEqual('Second', CommentaryTicker.snapshot()[0])
        CommentaryTicker.clear()
        self.assertEqual(('', None), CommentaryTicker.snapshot())

    def test_desktop_renderer_ack_advances_only_matching_message(self):
        from gdo.video.DesktopOverlay import DesktopOverlay
        CommentaryTicker.set('First')
        CommentaryTicker.set('Second')
        _, sequence = CommentaryTicker.snapshot()
        process = MagicMock()
        process.stdout = [json.dumps({'event': 'thoughts_finished', 'sequence': sequence + 1}).encode(),
                          json.dumps({'event': 'thoughts_finished', 'sequence': sequence}).encode()]
        DesktopOverlay()._read_overlay_events(process)
        self.assertEqual('Second', CommentaryTicker.snapshot()[0])

    def test_next_message_slides_in_without_overtaking(self):
        from gdo.video.TickerLayout import next_message_x
        self.assertEqual(300, next_message_x(300, 80, 0, 2, 15))
        self.assertEqual(180, next_message_x(300, 80, 30, 3, 15))
        self.assertEqual(65, next_message_x(300, 80, 30, 10, 15))
        CommentaryTicker.set('First')
        CommentaryTicker.set('Second')
        _, sequence = CommentaryTicker.snapshot()
        self.assertEqual('Second', CommentaryTicker.peek())
        CommentaryTicker.finish(sequence)
        self.assertEqual('Second', CommentaryTicker.snapshot()[0])

    def test_commentary_scrolls_twice_as_fast_as_music(self):
        from gdo.video.MicTicker import ticker_offset
        from gdo.video.TickerLayout import COMMENTARY_SPEED
        self.assertEqual(60, ticker_offset(0, 3, COMMENTARY_SPEED))
        self.assertEqual(30, ticker_offset(0, 3))

    def test_backlog_increases_speed_with_a_cap(self):
        from gdo.video.TickerLayout import commentary_speed
        self.assertEqual(60, commentary_speed(0))
        self.assertEqual(80, commentary_speed(2))
        self.assertEqual(120, commentary_speed(6))
        self.assertEqual(120, commentary_speed(64))

    def test_speed_change_does_not_jump_the_current_message(self):
        from gdo.video.MicTicker import TickerScroll
        scroll = TickerScroll(60)
        for step in range(7):
            offset, _ = scroll.frame(1, step * .5, 1000)
        self.assertEqual(60, offset)
        scroll.speed = 120
        offset, _ = scroll.frame(1, 3.5, 1000)
        self.assertEqual(120, offset)
        scroll.speed = 60
        offset, _ = scroll.frame(1, 4, 1000)
        self.assertEqual(150, offset)

    def test_queue_drops_oldest_pending_when_full(self):
        CommentaryTicker.set('current')
        _, sequence = CommentaryTicker.snapshot()
        for number in range(65):
            CommentaryTicker.set(str(number))
        self.assertEqual('current', CommentaryTicker.snapshot()[0])
        CommentaryTicker.finish(sequence)
        self.assertEqual('1', CommentaryTicker.snapshot()[0])

    def test_mode_switch_clears_commentary(self):
        from gdo.video.CommentaryFollower import CommentaryFollower
        worker = CommentaryFollower('/unused', 'cohost')
        for mode in ('off', 'unknown', None):
            CommentaryTicker.set('old')
            worker.set_mode(mode)
            self.assertEqual(('', None), CommentaryTicker.snapshot())

    def test_speech_is_opt_in_and_cleared_on_mode_change(self):
        from gdo.video.CommentaryFollower import CommentaryFollower
        worker = CommentaryFollower('/unused', 'show')
        worker.set_audio(True)
        worker.speech_queue.append('hello')
        self.assertEqual('hello', worker.next_speech())
        worker.speech_queue.append('old')
        worker.set_mode('off')
        worker.set_mode('show')
        self.assertIsNone(worker.next_speech())
        worker.speech_queue.append('old')
        worker.set_audio(False)
        self.assertIsNone(worker.next_speech())

    def test_new_follower_commentary_is_queued_for_speech_only_when_enabled(self):
        from gdo.video.CommentaryFollower import CommentaryFollower
        event = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'commentary', 'content': [{'type': 'output_text', 'text': 'Hello show'}]}}
        observed = threading.Event()
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8') as log:
            worker = CommentaryFollower(log.name, 'show')
            with patch('gdo.base.Thread.Thread.run'), patch.object(CommentaryTicker, 'set', side_effect=lambda text: observed.set()):
                worker.start()
                try:
                    self.assertTrue(worker.ready.wait(2))
                    log.write(json.dumps(event) + '\n')
                    log.flush()
                    self.assertTrue(observed.wait(2))
                    self.assertIsNone(worker.next_speech())
                    observed.clear()
                    worker.set_audio(True)
                    log.write(json.dumps(event) + '\n')
                    log.flush()
                    self.assertTrue(observed.wait(2))
                    # The ticker callback runs immediately before the speech enqueue.
                    with worker.mode_lock:
                        self.assertEqual(['Hello show'], list(worker.speech_queue))
                finally:
                    worker.stop()
                    worker.join(timeout=2)

    def test_follower_skips_history_and_reads_only_new_live_commentary(self):
        from gdo.video.CommentaryFollower import CommentaryFollower
        observed = threading.Event()
        event = {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'phase': 'commentary', 'content': [{'type': 'output_text', 'text': 'Fresh update'}]}}
        with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8') as log:
            log.write(json.dumps(event) + '\n')
            log.flush()
            worker = CommentaryFollower(log.name, 'cohost')
            with patch('gdo.base.Thread.Thread.run'), patch.object(CommentaryTicker, 'set', side_effect=lambda text: observed.set()) as publish:
                worker.start()
                try:
                    self.assertTrue(worker.ready.wait(2))
                    publish.assert_not_called()
                    log.write(json.dumps(event) + '\n')
                    log.flush()
                    self.assertTrue(observed.wait(2))
                    publish.assert_called_once_with('Fresh update')
                finally:
                    worker.stop()
                    worker.join(2)

    def test_virtual_overlay_hides_commentary_when_off(self):
        from PIL import Image
        from gdo.video.ThoughtsLayer import ThoughtsLayer
        CommentaryTicker.set('Hello viewers')
        with patch('gdo.audio.meter.MicrophoneMeter.snapshot', return_value=('off', 0)), \
             patch('gdo.audio.meter.MicrophoneMeter.transcription_snapshot', return_value='off'):
            off = Image.new('RGB', (640, 360))
            live = Image.new('RGB', (640, 360))
            ThoughtsLayer(live_mode='off').draw(off)
            ThoughtsLayer(live_mode='cohost').draw(live)
        self.assertNotEqual(off.tobytes(), live.tobytes())
        self.assertNotEqual((0, 0, 0), live.getpixel((12, 326)))

    def test_leaving_live_mode_clears_virtual_commentary(self):
        from gdo.video.VideoConnector import VideoConnector
        CommentaryTicker.set('Hello viewers')
        VideoConnector().live_indicator('off')
        self.assertEqual(('', None), CommentaryTicker.snapshot())

    def test_thoughts_is_an_independent_layer(self):
        from gdo.video.VideoConnector import VideoConnector
        video = VideoConnector()
        with patch.object(video, 'is_running', return_value=True):
            video.thoughts(True)
            self.assertIsNotNone(video.effects.get('thoughts'))
            self.assertIsNone(video.effects.get('mic'))
            video.thoughts(False)
            self.assertIsNone(video.effects.get('thoughts'))

    def test_thoughts_command_queues_enable(self):
        from gdo.video.method.thoughts import thoughts
        with patch('gdo.base.Application.Application.get_mode', return_value=None):
            method = thoughts()
        method.param_value = MagicMock(side_effect=lambda name: name == 'enabled')
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch('gdo.base.Application.Application.db', return_value=db), \
             patch('gdo.video.method.thoughts.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_thoughts', ['1', '0'])

    def test_thoughts_command_queues_opt_in_audio(self):
        from gdo.video.method.thoughts import thoughts
        with patch('gdo.base.Application.Application.get_mode', return_value=None):
            method = thoughts()
        method.param_value = MagicMock(return_value=True)
        method.reply = MagicMock()
        db = MagicMock()
        db.is_in_transaction.return_value = False
        with patch('gdo.base.Application.Application.db', return_value=db), \
             patch('gdo.video.method.thoughts.IPC.send_to_dog') as send:
            method.gdo_execute()
        send.assert_called_once_with('video.ipc_thoughts', ['1', '1'])

    def test_only_lock_owner_starts_follower(self):
        import asyncio
        from gdo.base.Application import Application
        from gdo.video.module_video import module_video
        module = module_video()
        module.get_config_val = MagicMock(return_value='/tmp/fixture.jsonl')
        module.get_config_value = MagicMock(return_value=False)
        loader = MagicMock()
        loader.get_module.return_value.get_config_val.return_value = 'show'
        worker = MagicMock()
        with tempfile.NamedTemporaryFile(mode='w+', encoding='ascii') as lock:
            lock.write(str(os.getpid()))
            lock.flush()
            with patch.object(Application, 'IS_DOG', True), \
                 patch('gdo.core.method.launch.launch.lock_path', return_value=lock.name), \
                 patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=loader), \
                 patch('gdo.video.CommentaryFollower.CommentaryFollower', return_value=worker) as create:
                asyncio.run(module.commentary_tick())
                create.assert_called_once_with('/tmp/fixture.jsonl', 'show')
                worker.start.assert_called_once()
                worker.set_mode.assert_called_once_with('show')
