from unittest.mock import AsyncMock, MagicMock, patch

from gdotest.TestUtil import GDOTestCase
from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.translate.GTranslate import GTranslateError, Translation
from gdo.video.CommentaryFollower import CommentaryFollower
from gdo.video.CommentaryTicker import CommentaryTicker
from gdo.video.module_video import module_video


class ThoughtTranslationTest(GDOTestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        Application.mode(Mode.render_cli)
        CommentaryTicker.clear()
        self.worker = CommentaryFollower('/unused', 'show')
        self.worker.set_audio(True, language='ar')
        self.worker.set_translation(True, 'en', 'ar')
        self.video = module_video()

    async def asyncTearDown(self):
        self.worker.stop()
        CommentaryTicker.clear()
        await super().asyncTearDown()

    async def test_translates_once_then_publishes_base_and_speech(self):
        provider = MagicMock()
        provider.cfg_google_api_key.return_value = 'test'
        translate = AsyncMock(return_value=Translation('أهلاً', 'en'))
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=provider))), \
             patch('gdo.translate.GTranslate.GTranslate.translate', translate):
            await self.video.translate_thought(self.worker, 'Hello', ('en', 'ar'), self.worker.translation_generation)
        translate.assert_awaited_once_with('Hello', source='en', target='ar', api_key='test')
        self.assertEqual('Hello', CommentaryTicker.snapshot()[0])
        self.assertEqual('أهلاً', self.worker.next_speech())

    def test_enabled_holds_both_outputs_before_translation(self):
        self.worker.accept_commentary('Hello')
        self.assertEqual('', CommentaryTicker.snapshot()[0])
        self.assertIsNone(self.worker.next_speech())
        self.assertEqual(('Hello', ('en', 'ar'), self.worker.translation_generation), self.worker.next_translation())

    def test_disabled_keeps_existing_speech_fallback(self):
        self.worker.set_translation(False)
        self.worker.accept_commentary('Hello ␟ أهلاً')
        self.assertEqual('Hello', CommentaryTicker.snapshot()[0])
        self.assertEqual('أهلاً', self.worker.next_speech())
        self.assertIsNone(self.worker.next_translation())

    async def test_failure_suppresses_both_outputs(self):
        provider = MagicMock()
        with patch('gdo.base.ModuleLoader.ModuleLoader.instance', return_value=MagicMock(get_module=MagicMock(return_value=provider))), \
             patch('gdo.translate.GTranslate.GTranslate.translate', new=AsyncMock(side_effect=GTranslateError('fail'))), \
             patch('gdo.base.Logger.Logger.warning') as warning:
            await self.video.translate_thought(self.worker, 'Hello', ('en', 'ar'), self.worker.translation_generation)
        self.assertEqual('', CommentaryTicker.snapshot()[0])
        self.assertIsNone(self.worker.next_speech())
        warning.assert_called_once()

    async def test_stale_translation_is_not_published(self):
        generation = self.worker.translation_generation
        self.worker.set_translation(True, 'en', 'de')
        self.assertFalse(self.worker.publish_translation('Hello', 'أهلاً', generation))
        self.assertEqual('', CommentaryTicker.snapshot()[0])
        self.assertIsNone(self.worker.next_speech())

    async def test_same_language_avoids_network(self):
        with patch('gdo.translate.GTranslate.GTranslate.translate', new=AsyncMock()) as translate:
            await self.video.translate_thought(self.worker, 'Hello', ('en', 'en'), self.worker.translation_generation)
        translate.assert_not_awaited()
        self.assertEqual('Hello', CommentaryTicker.snapshot()[0])

    def test_optional_configuration_defaults_off(self):
        with patch('gdo.core.GDO_Permission.GDO_Permission.table'):
            config = {field.get_name(): field for field in self.video.gdo_module_config()}
        self.assertFalse(config['video_thoughts_translate'].get_value())
