import base64
import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

from gdo.base.Application import Application
from gdo.base.Render import Mode
from gdo.core.GDT_Secret import GDT_Secret
from gdo.video.DirectStream import DirectStream, active_asset, process_start
from gdo.video.Recording import Recording
from gdo.video.StreamAuth import authorized
from gdo.video.module_video import module_video


class DirectStreamTest(unittest.TestCase):
    def setUp(self):
        Application.mode(Mode.render_cli)

    def test_sidebar_stream_status_requires_fresh_playlist(self):
        from gdo.video.method.stream_status import stream_status
        with tempfile.TemporaryDirectory() as temporary:
            playlist = Path(temporary) / 'index.m3u8'
            playlist.write_text('#EXTM3U\n')
            with patch('gdo.video.method.stream_status.active_asset', return_value=playlist), \
                    patch.object(Application, 'header'), patch.object(Application, 'status') as status:
                self.assertEqual('live', stream_status().gdo_execute().render_txt())
                status.assert_not_called()
                os.utime(playlist, (time.time() - 30, time.time() - 30))
                self.assertEqual('offline', stream_status().gdo_execute().render_txt())
                status.assert_called_with('404 Not Found')

    def test_optional_key_requires_basic_auth_and_tls(self):
        encoded = base64.b64encode('viewer:correct'.encode()).decode()
        self.assertTrue(authorized(None, None, False))
        self.assertTrue(authorized('correct', 'Basic ' + encoded, True))
        self.assertFalse(authorized('correct', 'Basic ' + encoded, False))
        self.assertFalse(authorized('wrong', 'Basic ' + encoded, True))
        self.assertFalse(authorized('correct', 'Basic ', True))
        self.assertFalse(authorized('correct', 'Basic !!!', True))

    def test_key_challenges_only_over_tls(self):
        from gdo.video.StreamAuth import require_stream_access
        with patch('gdo.video.StreamAuth.stream_key', return_value='correct'), \
             patch.object(Application, 'get_client_header', return_value=None), \
             patch.object(Application, 'header') as header, \
             patch.object(Application, 'status') as status, \
             patch.object(Application, 'is_tls', return_value=True):
            self.assertFalse(require_stream_access())
            status.assert_called_with('401 Unauthorized')
            self.assertTrue(any(call.args[0] == 'WWW-Authenticate' for call in header.call_args_list))
        with patch('gdo.video.StreamAuth.stream_key', return_value='correct'), \
             patch.object(Application, 'get_client_header', return_value=None), \
             patch.object(Application, 'header') as header, \
             patch.object(Application, 'status') as status, \
             patch.object(Application, 'is_tls', return_value=False):
            self.assertFalse(require_stream_access())
            status.assert_called_with('403 Forbidden')
            self.assertFalse(any(call.args[0] == 'WWW-Authenticate' for call in header.call_args_list))

    def test_key_is_optional_secret(self):
        fields = {field.get_name(): field for field in module_video().gdo_module_config()}
        key = fields['video_gdo_stream_key']
        self.assertIsInstance(key, GDT_Secret)
        self.assertFalse(key._not_null)

    def test_command_captures_both_audio_sources_once(self):
        command = DirectStream.command(':0.0', 'speaker', 'mic', Path('/tmp/example'))
        self.assertIn('speaker.monitor', command)
        self.assertIn('mic', command)
        self.assertIn('amix=inputs=2', command[command.index('-filter_complex') + 1])
        self.assertIn('/video.stream_asset.html?_asset=', command)
        self.assertIn('/demo/video.stream_asset.html?_asset=', DirectStream.command(':0', 'speaker', 'mic', Path('/tmp/example'), '/demo/'))
        with self.assertRaises(ValueError):
            DirectStream.command('http://example', 'speaker', 'mic', Path('/tmp/example'))
        with self.assertRaises(ValueError):
            DirectStream.command(':0', 'speaker', 'mic', Path('/tmp/example'), '//other-host/')

    def test_assets_require_active_exact_run_and_safe_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'run-test'
            directory.mkdir()
            playlist = directory / 'index.m3u8'
            playlist.write_text('#EXTM3U\n')
            info = {'run': directory.name, 'pid': os.getpid(), 'start': process_start(os.getpid())}
            (root / 'active.json').write_text(json.dumps(info))
            self.assertEqual(playlist, active_asset(root, 'index.m3u8'))
            self.assertIsNone(active_asset(root, '../active.json'))
            self.assertIsNone(active_asset(root, 'segment_1.ts'))
            info['start'] = 'stale'
            (root / 'active.json').write_text(json.dumps(info))
            self.assertIsNone(active_asset(root, 'index.m3u8'))

    def test_stop_only_removes_own_stream_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'run-test'
            directory.mkdir()
            (directory / 'index.m3u8').write_text('x')
            (directory / 'segment_00000001.ts').write_text('x')
            unrelated = root / 'other'
            unrelated.write_text('keep')
            manager = DirectStream(root)
            manager.directory = directory
            manager.process = MagicMock()
            manager.process.poll.return_value = 0
            manager.process.stdin = None
            self.assertTrue(manager.stop())
            self.assertFalse(directory.exists())
            self.assertEqual('keep', unrelated.read_text())

    def test_invalid_start_cleans_its_empty_run(self):
        with tempfile.TemporaryDirectory() as temporary, \
             patch.object(Recording, 'pulse_default', return_value='synthetic'):
            root = Path(temporary) / 'stream'
            manager = DirectStream(root)
            with self.assertRaises(ValueError):
                manager.start('not-a-display', None)
            self.assertEqual([], list(root.iterdir()))

    def test_private_paths_cannot_be_static_files(self):
        from gdo.base.method.file_server import file_server
        with patch('gdo.base.method.file_server.Application.config', return_value={}), \
             patch('gdo.base.method.file_server.module_config_value', return_value=True):
            self.assertTrue(file_server.is_forbidden('files/secret_video_stream/run-test/index.m3u8'))
            self.assertTrue(file_server.is_forbidden('files_tes/secret_video_stream/run-test/segment_00000001.ts'))

    def test_viewer_uses_local_hls_and_presence_signals(self):
        from gdo.video.method.stream import stream
        module = MagicMock()
        module.www_path.return_value = '/gdo/video/node_modules/hls.js/dist/hls.min.js'
        with patch('gdo.video.method.stream.require_stream_access', return_value=True), \
             patch('gdo.video.method.stream.module_video.instance', return_value=module), \
             patch('gdo.video.method.stream.href', side_effect=lambda _module, method, *_args: '/' + method):
            result = stream().gdo_execute().render_html()
        module.www_path.assert_called_once_with('node_modules/hls.js/dist/hls.min.js')
        self.assertIn('Hls.isSupported()', result)
        self.assertIn('"playing"', result)
        self.assertIn('"heartbeat"', result)
        self.assertIn('"pagehide"', result)

    def test_asset_denies_access_before_reading_stream(self):
        from gdo.video.method.stream_asset import stream_asset
        with patch('gdo.video.method.stream_asset.require_stream_access', return_value=False), \
             patch('gdo.video.method.stream_asset.active_asset') as lookup:
            result = stream_asset().gdo_execute()
        self.assertIn('denied', result.render_txt().lower())
        lookup.assert_not_called()


class StreamPresenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_join_heartbeat_quit_and_timeout(self):
        from gdo.video.StreamPresence import StreamPresence
        now = [100.0]
        publish = AsyncMock()
        presence = StreamPresence(publish, clock=lambda: now[0])
        viewer = 'a' * 32
        self.assertFalse(await presence.update('../wrong', 'join'))
        self.assertTrue(await presence.update(viewer, 'join'))
        self.assertTrue(await presence.update(viewer, 'join'))
        self.assertEqual(1, publish.await_count)
        now[0] += 15
        self.assertTrue(await presence.update(viewer, 'heartbeat'))
        now[0] += 19
        await presence.expire()
        self.assertIn(viewer, presence.viewers)
        now[0] += 1
        await presence.expire()
        self.assertNotIn(viewer, presence.viewers)
        self.assertEqual([('gdo_stream_joined', viewer), ('gdo_stream_quit', viewer)],
                         [call.args for call in publish.await_args_list])
        await presence.update(viewer, 'join')
        await presence.update(viewer, 'quit')
        await presence.update(viewer, 'quit')
        self.assertEqual(4, publish.await_count)
        self.assertTrue(await presence.update(viewer, 'heartbeat'))
        self.assertEqual('gdo_stream_joined', publish.await_args.args[0])

    async def test_capacity_and_stream_stop(self):
        from gdo.video.StreamPresence import StreamPresence
        publish = AsyncMock()
        presence = StreamPresence(publish)
        for number in range(presence.MAX_VIEWERS):
            self.assertTrue(await presence.update(f'{number:032x}', 'join'))
        self.assertFalse(await presence.update('f' * 32, 'join'))
        await presence.expire(all_viewers=True)
        self.assertFalse(presence.viewers)
        self.assertEqual(2 * presence.MAX_VIEWERS, publish.await_count)

    async def test_dog_ignores_presence_when_stream_is_off(self):
        from gdo.video.method.ipc_stream_presence import ipc_stream_presence
        Application.mode(Mode.render_cli)
        handler = ipc_stream_presence()
        handler.param_val = MagicMock(side_effect=lambda name: {'viewer': 'a' * 32, 'action': 'join'}[name])
        handler.empty = MagicMock()
        module = MagicMock()
        module.direct_stream.active.return_value = False
        module.stream_presence.update = AsyncMock()
        with patch.object(Application, 'IS_DOG', True), \
             patch('gdo.video.method.ipc_stream_presence.module_video.instance', return_value=module):
            await handler.gdo_execute()
            module.stream_presence.update.assert_not_awaited()
            module.direct_stream.active.return_value = True
            await handler.gdo_execute()
            module.stream_presence.update.assert_awaited_once_with('a' * 32, 'join')

    async def test_owner_start_requires_explicit_request_and_matching_audio_sessions(self):
        from gdo.audio.module_audio import module_audio
        from gdo.video.method.stream_control import stream_control
        Application.mode(Mode.render_cli)
        handler = stream_control()
        self.assertEqual('owner', handler.gdo_user_permission())
        handler.param_value = MagicMock(return_value=True)
        handler.err = MagicMock(return_value='error')
        module, audio = MagicMock(), MagicMock()
        module.connector.is_running.return_value = True
        module.get_config_value.return_value = 'screensharing'
        audio.get_config_val.side_effect = lambda key: {
            'audio_microphone_session_user': 'alice', 'audio_output_session_user': 'bob'}.get(key)
        with patch.object(Application, 'IS_DOG', True), \
             patch('builtins.open', mock_open(read_data=str(os.getpid()))), \
             patch('gdo.video.method.stream_control.module_video.instance', return_value=module), \
             patch.object(module_audio, 'instance', return_value=audio):
            self.assertEqual('error', await handler.gdo_execute())
        module.direct_stream.start.assert_not_called()


@unittest.skipUnless(os.environ.get('PYGDO_STREAM_SYNTHETIC_TEST') == '1' and shutil.which('ffmpeg'),
                     'synthetic ffmpeg integration test is opt-in')
class DirectStreamSyntheticTest(unittest.TestCase):
    def test_synthetic_hls_is_shared_and_stop_withdraws_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'stream'
            manager = DirectStream(root)

            def command(_display, _sink, _source, directory, _web_root):
                return ['ffmpeg', '-hide_banner', '-loglevel', 'error',
                        '-re', '-f', 'lavfi', '-i', 'testsrc2=size=64x64:rate=5',
                        '-re', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=8000',
                        '-re', '-f', 'lavfi', '-i', 'sine=frequency=660:sample_rate=8000',
                        '-filter_complex', '[1:a][2:a]amix=inputs=2[a]', '-map', '0:v:0', '-map', '[a]',
                        '-c:v', 'libx264', '-preset', 'ultrafast', '-g', '5', '-c:a', 'aac',
                        '-f', 'hls', '-hls_time', '1', '-hls_list_size', '3',
                        '-hls_flags', 'delete_segments+temp_file',
                        '-hls_base_url', '/video.stream_asset.html?_asset=',
                        '-hls_segment_filename', str(directory / 'segment_%08d.ts'), str(directory / 'index.m3u8')]

            with patch.object(Recording, 'pulse_default', return_value='synthetic'), \
                 patch.object(DirectStream, 'command', side_effect=command), \
                 patch('gdo.video.DirectStream.audio_session_command', side_effect=lambda command, _user: command):
                try:
                    manager.start(':0', None)
                    deadline = time.monotonic() + 8
                    playlist = None
                    while time.monotonic() < deadline and manager.active():
                        playlist = active_asset(root, 'index.m3u8')
                        if playlist:
                            break
                        time.sleep(.1)
                    self.assertIsNotNone(playlist)
                    contents = playlist.read_text()
                    self.assertIn('/video.stream_asset.html?_asset=segment_', contents)
                    name = next(line.rsplit('=', 1)[1] for line in contents.splitlines() if line.startswith('/video.stream_asset'))
                    self.assertIsNotNone(active_asset(root, name))
                finally:
                    manager.stop()
            self.assertIsNone(active_asset(root, 'index.m3u8'))
