"""Render the GLB duck into RGBA frames in a separate process.

Control is newline-delimited JSON on stdin; stdout contains fixed-size RGBA
frames. No desktop, microphone or network access is required.
"""
import json
import math
import sys
import threading
import time
from pathlib import Path


def main():
    import gltf
    from panda3d.core import AmbientLight, CardMaker, DirectionalLight, NodePath, OrthographicLens, Vec4, loadPrcFileData
    from direct.showbase.ShowBase import ShowBase
    from direct.actor.Actor import Actor

    size, fps = 256, 15
    loadPrcFileData('', f'window-type offscreen\nwin-size {size} {size}\nframebuffer-alpha 1\naudio-library-name null\nsync-video false\nnotify-level warning')
    base = ShowBase(windowType='offscreen')
    base.setBackgroundColor(0, 0, 0, 0)
    root = NodePath(gltf.load_model(str(Path(__file__).parent / 'assets/duck/mira-duck.glb')))
    # Only the beak is skinned. Wrapping the entire scene as an Actor would
    # discard its unskinned body, eyes and feet.
    beak = Actor(root.find('**/Duck rig'), copy=False)
    beak.reparentTo(root)
    root.reparentTo(base.render)
    tears = []
    for side in (-1, 1):
        card = CardMaker('cry tear')
        card.setFrame(-.045, .045, -.11, 0)
        tear = root.attachNewNode(card.generate())
        tear.setPos(side * .22, -.81, 1.51)
        tear.setColor(.18, .65, 1, 1)
        tear.setLightOff()
        tear.hide()
        tears.append(tear)
    lens = OrthographicLens()
    lens.setFilmSize(2.7, 2.7)
    base.cam.node().setLens(lens)
    base.camera.setPos(2.8, -6, 2.5)
    base.camera.lookAt(0, 0, 1)
    light = AmbientLight('ambient')
    light.setColor(Vec4(.75, .75, .75, 1))
    base.render.setLight(base.render.attachNewNode(light))
    light = DirectionalLight('key')
    light.setColor(Vec4(.8, .8, .8, 1))
    light_node = base.render.attachNewNode(light)
    light_node.setHpr(30, -45, 0)
    base.render.setLight(light_node)

    lock = threading.Lock()
    state = {'mode': 'idle', 'mode_start': time.monotonic(), 'speaking': False, 'running': True, 'envelope': [], 'step_ms': 50, 'speech_start': 0}

    def receive():
        for line in sys.stdin:
            try:
                request = json.loads(line)
                with lock:
                    if request.get('mode') in ('idle', 'quacking', 'lol', 'shrug', 'sad', 'cry'):
                        state['mode'] = request['mode']
                        state['mode_start'] = time.monotonic()
                    if isinstance(request.get('speaking'), bool):
                        state['speaking'] = request['speaking']
                        state['envelope'] = []
                    levels = request.get('envelope')
                    step = request.get('step_ms')
                    if isinstance(levels, list) and len(levels) <= 2400 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in levels) and isinstance(step, int) and 10 <= step <= 500:
                        state['envelope'], state['step_ms'], state['speech_start'] = levels, step, time.monotonic()
                    if request.get('stop') is True:
                        state['running'] = False
                        return
            except (ValueError, TypeError):
                continue
        with lock:
            state['running'] = False

    threading.Thread(target=receive, daemon=True).start()
    start = time.monotonic()
    try:
        while True:
            with lock:
                mode, speaking, running = state['mode'], state['speaking'], state['running']
                mode_start = state['mode_start']
                envelope, step_ms, speech_start = state['envelope'], state['step_ms'], state['speech_start']
            if not running:
                break
            t = time.monotonic() - start
            root.setR(math.sin(t * (7 if mode == 'lol' else 5 if mode == 'quacking' else 1.4)) * (12 if mode == 'lol' else 8 if mode == 'quacking' else 2))
            root.setZ(abs(math.sin(t * 8)) * .22 if mode == 'lol' else abs(math.sin(t * 5)) * .08 if mode == 'quacking' else .012 * math.sin(t * 1.4))
            root.setP(20 + 2 * math.sin(t * .8) if mode in ('sad', 'cry') else 0)
            root.setSz(.88 + .012 * math.sin(t * (7 if mode == 'cry' else .8)) if mode in ('sad', 'cry') else 1)
            for tear in tears:
                if mode == 'cry':
                    tear.show()
                    tear.setZ(1.51 - .15 * ((time.monotonic() - mode_start) % .8) / .8)
                else:
                    tear.hide()
            if mode == 'shrug':
                elapsed = time.monotonic() - mode_start
                root.setR(4 * math.sin(elapsed * 18) * max(0, 1 - elapsed))
                root.setZ(.40 * math.sin(math.pi * min(elapsed / .65, 1)))
            for sign, name in ((-1, 'Wing L'), (1, 'Wing R')):
                wing = root.find('**/' + name)
                if not wing.isEmpty():
                    wing.setR(sign * (30 + 25 * math.sin(t * 11)) if mode == 'lol' else sign * 55 if mode == 'shrug' else -sign * 25 if mode in ('sad', 'cry') else 0)
            for index, name in enumerate(('Foot', 'Foot.001')):
                foot = root.find('**/' + name)
                if not foot.isEmpty():
                    foot.setZ(.16 + (max(0, math.sin(t * 5 + index * math.pi)) * .08 if mode in ('quacking', 'lol') else 0))
            for eye in ('Eye white', 'Eye white.001', 'Pupil', 'Pupil.001'):
                node = root.find('**/' + eye)
                if not node.isEmpty():
                    node.setSz(1.3 if mode == 'shrug' else .12 if (t + 2) % 4.2 < .12 else .25 if mode == 'cry' else .42 if mode == 'sad' else 1)
            index = int((time.monotonic() - speech_start) * 1000 / step_ms)
            level = envelope[index] if speaking and 0 <= index < len(envelope) else 0
            # The existing animation opens its beak around frame 7.
            beak.pose('Duck rigAction', int(t * 24) % 32 if speaking and not envelope else round(level * 7))
            base.graphicsEngine.renderFrame()
            texture = base.win.getScreenshot()
            data = bytes(texture.getRamImageAs('RGBA'))
            if len(data) != size * size * 4:
                raise RuntimeError('Unexpected duck framebuffer size')
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            time.sleep(1 / fps)
    except BrokenPipeError:
        pass
    finally:
        base.destroy()


if __name__ == '__main__':
    main()
