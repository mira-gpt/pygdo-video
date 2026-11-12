from __future__ import annotations

import os
import asyncio
import re
import time
import random

from gdo.base.GDO_Module import GDO_Module
from gdo.base.GDO import GDO
from gdo.base.GDT import GDT
from gdo.core.GDT_Bool import GDT_Bool
from gdo.core.GDT_Enum import GDT_Enum
from gdo.core.GDT_Path import GDT_Path
from gdo.core.GDT_String import GDT_String
from gdo.date.GDT_Duration import GDT_Duration
from gdo.ui.GDT_Link import GDT_Link
from gdo.ui.GDT_Width import GDT_Width
from gdo.ui.GDT_Height import GDT_Height
from gdo.video.VideoConnector import VideoConnector
from gdo.video.DesktopOverlay import DesktopOverlay
from gdo.core.Connector import Connector
from gdo.core.GDO_Server import GDO_Server
from gdo.video.connector.Video import Video

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gdo.ui.GDT_Page import GDT_Page


class module_video(GDO_Module):
    connector = VideoConnector()

    def gdo_friendencies(self) -> list:
        return ['audio']

    def gdo_classes(self) -> list[type[GDO]]:
        return []

    async def gdo_install(self):
        if not GDO_Server.get_by_connector('video'):
            GDO_Server.blank({'serv_name': 'Video', 'serv_connector': 'video'}).insert()

    def gdo_module_config(self) -> list[GDT]:
        return [
            GDT_Enum('video_mode').choices({
                'off': 'off',
                'virtualwebcam': 'virtualwebcam',
                'screensharing': 'screensharing',
            }).not_null().initial('off').tooltip('tt_video_mode'),
            GDT_String('video_desktop_url').maxlen(2048).tooltip('tt_video_desktop_url'),
            GDT_String('video_bg_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_bg_image_url'),
            GDT_String('video_overlay_image_url').maxlen(2048).initial(
                os.path.join(os.path.dirname(__file__), 'img', 'itmb-logo.png')).tooltip('tt_video_overlay_image_url'),
            GDT_String('video_file_url').maxlen(2048).tooltip('tt_video_file_url'),
            GDT_String('video_webcam_url').maxlen(2048).tooltip('tt_video_webcam_url'),
            GDT_Bool('video_duck_overlay').not_null().initial('0').tooltip('tt_video_duck_overlay'),
            GDT_Bool('video_mic_overlay').not_null().initial('0').tooltip('tt_video_mic_overlay'),
            GDT_Bool('video_duck3d_overlay').not_null().initial('0').tooltip('tt_video_duck3d_overlay'),
            GDT_String('video_duck3d_pythonpath').maxlen(512).tooltip('tt_video_duck3d_pythonpath'),
            GDT_String('video_output_device').not_null().initial('/dev/video2').maxlen(255).tooltip('tt_video_output_device'),
            GDT_Bool('video_output_preview').not_null().initial('0').tooltip('tt_video_output_preview'),
            GDT_Width('video_preview_w').not_null().initial('320').min(1).max(8192).tooltip('tt_video_preview_w'),
            GDT_Height('video_preview_h').not_null().initial('180').min(1).max(8192).tooltip('tt_video_preview_h'),
            GDT_Bool('video_live').not_null().initial('0').tooltip('tt_video_live'),
            GDT_Duration('video_timer_frequency').not_null().min(10).initial('5m').tooltip('tt_video_timer_frequency'),
            GDT_Path('video_commentary_log').maxlen(2048).tooltip('tt_video_commentary_log'),
            GDT_Bool('video_thoughts_overlay').not_null().initial('0').tooltip('tt_video_thoughts_overlay'),
            GDT_Bool('video_thoughts_audio').not_null().initial('0').tooltip('tt_video_thoughts_audio'),
        ]

    def gdo_user_config(self) -> list[GDT]:
        return []

    def gdo_user_settings(self) -> list[GDT]:
        return []

    def gdo_init(self):
        from gdo.video.YouTubeSender import YouTubeSender
        from gdo.video.VideoTimer import VideoTimer
        from gdo.video.Recording import Recording
        self.youtube_sender = YouTubeSender()
        self.video_timer = VideoTimer()
        self.recorder = Recording()
        Connector.register(Video, is_text=False)

    def gdo_subscribe_events(self):
        from gdo.base.Application import Application
        Application.EVENTS.add_timer_async(1, self.video_timer_tick, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(2, self.commentary_tick, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(.25, self.thought_speech_tick, Application.EVENTS.FOREVER)
        Application.EVENTS.add_timer_async(3, self.codex_activity_tick, Application.EVENTS.FOREVER)
        Application.EVENTS.subscribe('audio_speech_start', self.on_speech_start)
        Application.EVENTS.subscribe('audio_speech_end', self.on_speech_end)
        Application.EVENTS.subscribe('audio_speech_envelope', self.on_speech_envelope)
        Application.EVENTS.subscribe('mira_current_song_changed', self.on_current_song_changed)
        Application.EVENTS.subscribe('module_mira_mira_mood_changed', self.on_mira_mood_changed)
        Application.EVENTS.subscribe('module_mira_mira_livemode_changed', self.on_mira_livemode_changed)
        Application.EVENTS.subscribe('module_mira_agent_name_changed', self.on_indicator_name_changed)
        Application.EVENTS.subscribe('module_audio_audio_operator_changed', self.on_indicator_name_changed)
        Application.EVENTS.subscribe('user_joined_channel_live', self.on_live_join_welcome)

    async def video_timer_tick(self):
        from datetime import datetime
        from gdo.base.Application import Application
        from gdo.video.MicTicker import MicTicker
        if Application.IS_DOG:
            message = self.video_timer.tick(datetime.now().astimezone(), time.monotonic(),
                                            self.get_config_value('video_timer_frequency'))
            if message:
                MicTicker.enqueue(message)

    async def codex_activity_tick(self):
        from gdo.base.Application import Application
        from gdo.video.CodexActivity import CodexActivity
        if Application.IS_DOG:
            path = self.get_config_val('video_commentary_log') or ''
            if path and not os.path.isabs(path):
                path = Application.file_path(path)
            CodexActivity.poll(path)

    async def on_current_song_changed(self, artist, title):
        from gdo.base.ModuleLoader import ModuleLoader
        from gdo.base.Trans import Trans
        audio = ModuleLoader.instance().get_module('audio')
        worker = getattr(self, '_commentary_follower', None)
        if (audio and audio.is_enabled() and audio.get_config_value('audio_announce_songs')
                and self.get_config_value('video_thoughts_overlay')
                and self.get_config_value('video_thoughts_audio') and worker):
            language = audio.get_config_val('audio_microphone_language') or 'en'
            worker.announce(Trans.tiso2(language, 'mira_current_song_playing', (artist, title)))

    async def commentary_tick(self):
        from gdo.base.Application import Application
        from gdo.base.ModuleLoader import ModuleLoader
        from gdo.core.method.launch import launch
        try:
            with open(launch.lock_path(), 'r', encoding='ascii') as lock:
                is_this_dog = int(lock.read().strip()) == os.getpid()
        except (OSError, ValueError):
            is_this_dog = False
        if not Application.IS_DOG or not is_this_dog:
            return
        path = self.get_config_val('video_commentary_log') or ''
        if path and not os.path.isabs(path):
            path = Application.file_path(path)
        mira = ModuleLoader.instance().get_module('mira')
        mode = mira.get_config_val('mira_livemode') if mira else None
        worker = getattr(self, '_commentary_follower', None)
        if worker and (worker.path != path or not worker.is_alive()):
            self.cancel_thought_prefetch()
            worker.stop()
            worker.join(timeout=1)
            self._commentary_follower = worker = None
        if path and not worker:
            from gdo.video.CommentaryFollower import CommentaryFollower
            self._commentary_follower = worker = CommentaryFollower(path, mode)
            worker.start()
        if worker:
            worker.set_mode(mode)
            audio = ModuleLoader.instance().get_module('audio')
            enabled = bool(self.get_config_value('video_thoughts_overlay') and
                           self.get_config_value('video_thoughts_audio') and
                           audio and audio.is_enabled())
            language = audio.get_config_val('audio_microphone_language') if enabled else None
            if enabled:
                from gdo.audio.language import VOICES
                enabled = language in VOICES
            from gdo.base.Trans import Trans
            url_phrase = Trans.tiso2(language or 'en', 'mira_audio_some_url') if enabled else 'a link'
            smile_phrase = Trans.tiso2(language or 'en', 'mira_audio_emoji_smile') if enabled else 'smile'
            worker.set_audio(enabled, url_phrase, smile_phrase, language or 'en')
            from gdo.video.CommentaryFollower import LIVE_MODES
            previous_language = getattr(self, '_thought_audio_language', None)
            if previous_language and previous_language != language:
                self.cancel_thought_prefetch()
            self._thought_audio_language = language if enabled else None
            if enabled and mode in LIVE_MODES:
                self.queue_thought_speech(worker, language)
            else:
                self.cancel_thought_prefetch()

    async def thought_speech_tick(self):
        from gdo.video.CommentaryFollower import LIVE_MODES
        worker = getattr(self, '_commentary_follower', None)
        language = getattr(self, '_thought_audio_language', None)
        if worker and worker.audio_enabled and worker.mode in LIVE_MODES and language:
            self.queue_thought_speech(worker, language)

    def cancel_thought_prefetch(self):
        tasks = [task for task in getattr(self, '_thought_speech_tasks', []) if not task.done()]
        for task in tasks:
            task.cancel()
        self._thought_speech_tasks = []

    def queue_thought_speech(self, worker, language):
        from gdo.audio.PlaybackTasks import PlaybackTasks
        from gdo.audio.SpeechPlayback import SpeechPlayback
        from gdo.audio.method.ipc_say import ipc_say
        tasks = [task for task in getattr(self, '_thought_speech_tasks', []) if not task.done()]
        self._thought_speech_tasks = tasks
        if len(tasks) >= 2 or any(not task.done() and task not in tasks for task in PlaybackTasks.tasks):
            return
        if tasks and not SpeechPlayback.is_playing():
            return
        if text := worker.next_speech():
            previous = tasks[-1] if tasks else None
            speech = ipc_say().input('text', text).input('lang', language)
            tasks.append(PlaybackTasks.start(speech.play_prefetched(previous)))

    async def on_live_join_welcome(self, user, channel):
        """Greet actual joins only during a live show, with a global cooldown."""
        from gdo.base.ModuleLoader import ModuleLoader
        from gdo.core.GDT_UserType import GDT_UserType
        mira = ModuleLoader.instance().get_module('mira')
        if not mira or mira.cfg_mira_livemode() != 'show':
            return
        if any(user.is_type(kind) for kind in (GDT_UserType.BOT, GDT_UserType.CHAPPY,
                                                GDT_UserType.SYSTEM, GDT_UserType.DEVICE)):
            return
        from gdo.video.method.welcome import welcome
        if not welcome().env_channel(channel).get_config_channel_value('video_welcome_enabled'):
            return
        language = channel.get_lang_iso()
        if language not in ('de', 'en'):
            return  # Do not misrepresent the spoken language.
        now = time.monotonic()
        if now - getattr(self, '_last_auto_welcome', 0) < 8:
            return
        name = user.get_displayname() or user.get_name()
        name = re.sub(r'[\x00-\x1f\x7f]', ' ', name or '').strip()[:60]
        if not name:
            return
        self._last_auto_welcome = now
        from gdo.audio.PlaybackTasks import PlaybackTasks
        PlaybackTasks.start(self.play_welcome(name, language))

    async def play_welcome(self, nickname, language):
        from gdo.audio.method.ipc_say import ipc_say
        from gdo.base.Logger import Logger
        from gdo.base.Trans import tiso
        try:
            if language not in ('de', 'en'):
                raise ValueError('No supported welcome voice for this channel language')
            nickname = re.sub(r'[\x00-\x1f\x7f]', ' ', nickname or '').strip()[:60]
            if not nickname:
                raise ValueError('Nickname is empty')
            text = tiso(language, f'video_welcome_{random.randint(1, 3)}', (nickname,))
            self.duck_event('hello')
            await ipc_say().input('text', text).input('lang', language).play()
        except (ImportError, ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Duck welcome failed: {error}')

    async def on_mira_livemode_changed(self, module, field):
        mode = field.get_val()
        from gdo.video.CommentaryFollower import LIVE_MODES
        if mode not in LIVE_MODES:
            self.cancel_thought_prefetch()
        if worker := getattr(self, '_commentary_follower', None):
            worker.set_mode(mode)
        self.connector.liveshow(mode == 'show')
        self.connector.live_indicator(mode, self.indicator_name(mode))

    async def on_indicator_name_changed(self, module, field):
        self.sync_liveshow()

    @staticmethod
    def indicator_name(mode):
        from gdo.base.ModuleLoader import ModuleLoader
        try:
            loader = ModuleLoader.instance()
        except AttributeError:
            return None
        if mode == 'cohost':
            mira = loader.get_module('mira')
            name = mira.cfg_agent_name() if mira else None
        elif mode == 'show':
            audio = loader.get_module('audio')
            operator = audio.cfg_audio_operator() if audio else None
            name = operator.get_name() if operator else None
        else:
            name = None
        if not isinstance(name, str):
            return None
        return ''.join(c for c in name if c.isprintable())[:64].strip() or None

    def sync_liveshow(self):
        from gdo.base.ModuleLoader import ModuleLoader
        try:
            mira = ModuleLoader.instance().get_module('mira')
        except AttributeError:
            mira = None
        self.connector.liveshow(mira.cfg_mira_livemode() == 'show' if mira else False)
        mode = mira.cfg_mira_livemode() if mira else 'off'
        self.connector.live_indicator(mode, self.indicator_name(mode))

    def restore_overlays(self):
        from gdo.base.Logger import Logger
        try:
            if self.get_config_value('video_thoughts_overlay'):
                self.connector.thoughts(True)
        except (ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Restoring commentary overlay failed: {error}')
        try:
            if self.get_config_value('video_mic_overlay'):
                self.connector.microphone_meter(True)
        except (ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Restoring microphone overlay failed: {error}')
        try:
            if self.get_config_value('video_duck3d_overlay'):
                self.connector.duck3d(True)
                from gdo.base.ModuleLoader import ModuleLoader
                mira = ModuleLoader.instance().get_module('mira')
                if mira:
                    self.connector.duck_animation(mira.cfg_mira_mood())
        except (ValueError, RuntimeError, OSError, AttributeError) as error:
            Logger.warning(f'Restoring 3D duck overlay failed: {error}')

    async def on_mira_mood_changed(self, module, field):
        task = getattr(self, '_duck_event_task', None)
        if task and not task.done():
            return  # The new base mood is used once the temporary event ends.
        try:
            self.connector.duck_animation(field.get_val())
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass  # A mood change must not start a video source.

    def duck_event(self, key, duration=4.0):
        """Immediately replace an event; restore the latest base mood at its end."""
        connector = self.connector
        connector.duck_animation(key)
        previous = getattr(self, '_duck_event_task', None)
        if previous and not previous.done():
            previous.cancel()
        self._duck_event_task = asyncio.create_task(self._finish_duck_event(connector, duration))
        return self._duck_event_task

    def finish_duck_event(self, task):
        if task is not getattr(self, '_duck_event_task', None):
            return
        task.cancel()
        self._duck_event_task = None
        from gdo.base.ModuleLoader import ModuleLoader
        mira = ModuleLoader.instance().get_module('mira')
        self.connector.duck_animation(mira.cfg_mira_mood() if mira else 'idle')

    async def _finish_duck_event(self, connector, duration):
        from gdo.base.ModuleLoader import ModuleLoader
        from gdo.base.Logger import Logger
        try:
            if duration is None:
                await asyncio.Future()
            else:
                await asyncio.sleep(duration)
            if self.connector is connector:
                mira = ModuleLoader.instance().get_module('mira')
                connector.duck_animation(mira.cfg_mira_mood() if mira else 'idle')
        except (AttributeError, RuntimeError, ValueError, OSError) as error:
            Logger.warning(f'Duck event restore failed: {error}')
        finally:
            if getattr(self, '_duck_event_task', None) is asyncio.current_task():
                self._duck_event_task = None

    async def on_speech_envelope(self, speech_id, levels, step_ms):
        try:
            self.connector.speech_envelope(speech_id, levels, step_ms)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass

    async def on_speech_start(self, speech_id, text):
        try:
            self.connector.speech_start(speech_id, text)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass  # Video is optional; speech must continue.

    async def on_speech_end(self, speech_id):
        try:
            self.connector.speech_end(speech_id)
        except (AttributeError, RuntimeError, ValueError, OSError):
            pass

    def start_compositor(self):
        mode = self.get_config_value('video_mode')
        if self.connector.is_running():
            raise RuntimeError('Video worker is already running; stop it before switching modes')
        if mode == 'off':
            raise ValueError('Video mode is off')
        if mode == 'screensharing':
            worker = DesktopOverlay(screensharing=True)
            worker.recording_active = lambda: bool(getattr(self, 'recorder', None) and self.recorder.active())
            worker.duck3d_pythonpath = self.get_config_val('video_duck3d_pythonpath')
            worker.start(self.get_config_val('video_overlay_image_url'))
            try:
                if (self.get_config_value('video_live') in (True, 1, '1') and
                        VideoConnector.virtual_camera_allowed()):
                    worker.start_virtual_output(self.get_config_val('video_desktop_url'),
                                                self.get_config_val('video_output_device'))
            except Exception:
                worker.stop()
                raise
            self.connector = worker
            self.sync_liveshow()
            self.restore_overlays()
            return
        if mode != 'virtualwebcam':
            raise ValueError('Unknown video mode')
        if (self.get_config_val('video_file_url') or self.get_config_val('video_webcam_url')
                or self.get_config_value('video_duck_overlay')):
            raise ValueError('Video file, webcam and duck layers are not implemented yet')
        worker = VideoConnector()
        worker.recording_active = lambda: bool(getattr(self, 'recorder', None) and self.recorder.active())
        worker.duck3d_pythonpath = self.get_config_val('video_duck3d_pythonpath')
        worker.start(
            self.get_config_val('video_desktop_url'), self.get_config_val('video_bg_image_url'),
            self.get_config_value('video_output_preview'),
            self.get_config_value('video_live') and VideoConnector.virtual_camera_allowed(),
            self.get_config_val('video_output_device'), self.get_config_value('video_preview_w'),
            self.get_config_value('video_preview_h'))
        self.connector = worker
        self.sync_liveshow()
        self.restore_overlays()

    def gdo_load_scripts(self, page: 'GDT_Page'):
        self.add_js('js/pygdo-video.js')
        self.add_css('css/pygdo-video.css')

    def gdo_init_sidebar(self, page: 'GDT_Page'):
        page._left_bar.add_field(GDT_Link().href(self.href('overview')).text('module_video'))
