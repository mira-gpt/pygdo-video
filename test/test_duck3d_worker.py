"""Optional synthetic test: no desktop or microphone is captured."""
import importlib.util
import json
import os
import select
import subprocess
import sys
import unittest
from pathlib import Path
import time
from unittest.mock import MagicMock, patch


@unittest.skipUnless(importlib.util.find_spec('panda3d') and importlib.util.find_spec('gltf')
                     and os.environ.get('DISPLAY'), 'optional 3D dependencies and X11 required')
class Duck3DWorkerTest(unittest.TestCase):
    def test_source_control_and_shutdown(self):
        from gdo.video.Duck3DSource import Duck3DSource
        source = Duck3DSource()
        try:
            deadline = time.monotonic() + 10
            while source.snapshot() is None and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertIsNotNone(source.snapshot())
            source.update(mode='quacking', speaking=True)
            source.update(mode='lol')
            source.update(mode='hello')
            source.update(mode='music')
            source.update(mode='drunk')
            source.update(mode='teacher')
            source.update(mode='xd')
            source.update(mode='sorry')
            source.update(mode='trip')
            source.update(mode='nerd')
            source.update(mode='tired')
            source.update(mode='cast')
            source.update(mode='zombie')
            source.update(mode='pirate')
            source.update(mode='ghost')
            source.update(mode='work')
            source.update(mode='bday')
            with self.assertRaises(ValueError):
                source.update(mode='invalid')
        finally:
            source.close()
        self.assertIsNotNone(source.process.poll())

    def test_ghost_is_translucent_and_idle_restores_opacity(self):
        from gdo.video.Duck3DSource import Duck3DSource
        source = Duck3DSource()
        try:
            source.wait_ready(timeout=10)
            source.update(mode='ghost')
            time.sleep(1)
            ghost = source.snapshot().getchannel('A')
            source.update(mode='idle')
            time.sleep(1)
            idle = source.snapshot().getchannel('A')
            self.assertLess(sum(ghost.histogram()[220:]), sum(idle.histogram()[220:]) * .6)
            self.assertGreater(sum(ghost.histogram()[10:]), 1000)
        finally:
            source.close()

    def test_model_has_independent_wing_joints(self):
        import gltf
        from panda3d.core import NodePath
        from direct.actor.Actor import Actor

        model = Path(__file__).resolve().parents[1] / 'assets/duck/mira-duck.glb'
        root = NodePath(gltf.load_model(str(model)))
        actor = Actor(root.find('**/Wing rig'), copy=False)
        self.assertTrue({'WingBase', 'WingTip'} <= {joint.getName() for joint in actor.getJoints()})

    def test_both_output_adapters_receive_live_frames_and_stop(self):
        from gdo.video.DesktopOverlay import DesktopOverlay
        from gdo.video.VideoConnector import VideoConnector

        compositor = VideoConnector()
        compositor.worker = MagicMock()
        compositor.worker.is_alive.return_value = True
        compositor.duck3d(True)
        live = compositor.effects.get('duck')
        try:
            compositor.duck_animation('quacking')
            compositor.duck_animation('lol')
            compositor.speech_start('id', 'Hello')
            deadline = time.monotonic() + 10
            while live.source.snapshot() is None and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertIsNotNone(live.source.snapshot())
            compositor.speech_end('id')
        finally:
            compositor.duck3d(False)
        self.assertIsNotNone(live.source.process.poll())

        overlay = DesktopOverlay(screensharing=True)
        overlay.process = MagicMock()
        overlay.process.poll.return_value = None
        with patch.object(overlay, '_send_payload') as send:
            overlay.duck3d(True)
            source = overlay.duck_source
            try:
                overlay.duck_animation('quacking')
                overlay.duck_animation('lol')
                deadline = time.monotonic() + 10
                while not any(call.args[0].get('effect') == 'duck_frame' for call in send.call_args_list) and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(any(call.args[0].get('effect') == 'duck_frame' for call in send.call_args_list))
            finally:
                overlay.duck(False)
            self.assertIsNotNone(source.process.poll())

    def test_transparent_frame_and_mode_switch(self):
        worker = Path(__file__).resolve().parents[1] / 'Duck3DWorker.py'
        process = subprocess.Popen([sys.executable, str(worker)], stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        frame_size = 256 * 256 * 4

        def frame():
            data = bytearray()
            while len(data) < frame_size:
                self.assertTrue(select.select([process.stdout], [], [], 10)[0], 'renderer timed out')
                chunk = os.read(process.stdout.fileno(), frame_size - len(data))
                self.assertTrue(chunk, 'renderer exited before a complete frame')
                data.extend(chunk)
            return bytes(data)

        try:
            first = frame()
            self.assertEqual(0, min(first[3::4]))
            self.assertEqual(255, max(first[3::4]))
            self.assertGreater(sum(alpha > 0 for alpha in first[3::4]), 5000, 'whole duck, not only beak')
            process.stdin.write((json.dumps({'mode': 'quacking', 'speaking': True}) + '\n').encode())
            changed = frame()
            self.assertNotEqual(first, changed)
            process.stdin.write(b'{"mode":"pirate"}\n')
            pirate_frames = [frame() for _ in range(12)]
            self.assertTrue(any(candidate != first for candidate in pirate_frames))
            process.stdin.write(b'{"mode":"bday"}\n')
            birthday_frames = [frame() for _ in range(20)]
            self.assertTrue(any(candidate != first for candidate in birthday_frames))
            self.assertGreater(len(set(birthday_frames)), 1)
            process.stdin.write(b'{"stop":true}\n')
            # Closing the reader also releases a producer blocked in write.
            process.stdout.close()
            self.assertEqual(0, process.wait(timeout=10))
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            process.stdin.close()
            process.stderr.close()
