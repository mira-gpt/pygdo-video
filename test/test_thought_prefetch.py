import asyncio
import unittest
from unittest.mock import MagicMock, patch

from gdo.audio.PlaybackTasks import PlaybackTasks
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.video.module_video import module_video


class ThoughtPrefetchTest(unittest.IsolatedAsyncioTestCase):
    async def test_queue_is_bounded_and_disable_cancels_prefetch(self):
        Application.mode(Mode.render_cli)
        module = module_video()
        worker = MagicMock()
        worker.next_speech.side_effect = ['one', 'two', 'three']
        started = asyncio.Event()

        class FakeSpeech:
            def input(self, *_):
                return self

            async def play_prefetched(self, previous=None):
                started.set()
                await asyncio.Event().wait()

        with patch('gdo.audio.method.ipc_say.ipc_say', FakeSpeech), \
             patch('gdo.audio.SpeechPlayback.SpeechPlayback.is_playing', return_value=False) as playing:
            module.queue_thought_speech(worker, 'en')
            await started.wait()
            module.queue_thought_speech(worker, 'en')
            self.assertEqual(1, worker.next_speech.call_count)
            playing.return_value = True
            module.queue_thought_speech(worker, 'en')
            module.queue_thought_speech(worker, 'en')
            self.assertEqual(2, worker.next_speech.call_count)
            first, second = module._thought_speech_tasks
            module.cancel_thought_prefetch()
            await asyncio.gather(first, second, return_exceptions=True)
            self.assertTrue(second.cancelled())
            self.assertTrue(first.cancelled())
        self.assertFalse([task for task in PlaybackTasks.tasks if not task.done()])
