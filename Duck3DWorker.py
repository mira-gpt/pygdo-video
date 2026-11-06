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

TRANSITION_SECONDS = .7


def transition_weight(elapsed, duration=TRANSITION_SECONDS):
    """Smoothly interpolate between poses, clamped at both ends."""
    amount = max(0.0, min(1.0, elapsed / duration))
    return amount * amount * (3.0 - 2.0 * amount)


def main():
    import gltf
    from panda3d.core import AmbientLight, CardMaker, DirectionalLight, LineSegs, NodePath, OrthographicLens, TransparencyAttrib, Vec4, loadPrcFileData
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
    wing_actor = Actor(root.find('**/Wing rig'), copy=False)
    wing_actor.reparentTo(root)
    wing_base = wing_actor.controlJoint(None, 'modelRoot', 'WingBase')
    wing_tip = wing_actor.controlJoint(None, 'modelRoot', 'WingTip')
    if wing_base.isEmpty() or wing_tip.isEmpty():
        raise RuntimeError('Duck wing joints are missing')
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
    marks = LineSegs('ouch marks')
    marks.setThickness(3)
    marks.setColor(1, .86, .12, 1)
    for side in (-1, 1):
        for z, dz in ((1.15, -.08), (1.42, .02), (1.68, .1)):
            marks.moveTo(side * .73, -.35, z)
            marks.drawTo(side * 1.03, -.35, z + dz)
    pain_marks = root.attachNewNode(marks.create())
    pain_marks.setLightOff()
    pain_marks.setTransparency(TransparencyAttrib.MAlpha)
    pain_marks.hide()
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
                    if request.get('mode') in ('idle', 'quacking', 'lol', 'shrug', 'sad', 'cry', 'ouch', 'hello', 'rolleye', 'high'):
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
    nodes = [(root, 'R'), (root, 'Z'), (root, 'P'), (root, 'Sz')]
    nodes.extend([(wing_base, 'R'), (wing_tip, 'R')])
    for name, prop in [('Wing L', 'R'), ('Foot', 'Z'), ('Foot.001', 'Z'),
                       ('Eye white', 'Sz'), ('Eye white.001', 'Sz'), ('Pupil', 'Sz'), ('Pupil.001', 'Sz')]:
        node = root.find('**/' + name)
        if not node.isEmpty():
            nodes.append((node, prop))
    pupils = [root.find('**/' + name) for name in ('Pupil', 'Pupil.001')]
    pupil_origins = [(node.getX(), node.getZ()) for node in pupils if not node.isEmpty()]
    pupils = [node for node in pupils if not node.isEmpty()]
    for node in pupils:
        nodes.extend([(node, 'X'), (node, 'Z')])
    previous_mode = 'idle'
    outgoing_mode = 'idle'
    transition_stamp = state['mode_start']
    origin = [getattr(node, 'get' + prop)() for node, prop in nodes]
    try:
        while True:
            with lock:
                mode, speaking, running = state['mode'], state['speaking'], state['running']
                mode_start = state['mode_start']
                envelope, step_ms, speech_start = state['envelope'], state['step_ms'], state['speech_start']
            if not running:
                break
            if mode_start != transition_stamp:
                origin = [getattr(node, 'get' + prop)() for node, prop in nodes]
                outgoing_mode, previous_mode = previous_mode, mode
                transition_stamp = mode_start
            blend = transition_weight(time.monotonic() - mode_start)
            t = time.monotonic() - start
            root.setR(math.sin(t * (7 if mode == 'lol' else 5 if mode == 'quacking' else 1.4)) * (12 if mode == 'lol' else 8 if mode == 'quacking' else 2))
            root.setZ(abs(math.sin(t * 8)) * .22 if mode == 'lol' else abs(math.sin(t * 5)) * .08 if mode == 'quacking' else .012 * math.sin(t * 1.4))
            root.setP(20 + 2 * math.sin(t * .8) if mode in ('sad', 'cry') else 0)
            if mode == 'high':
                root.setR(7 * math.sin(t * 1.1))
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
            if mode == 'ouch':
                phase = (time.monotonic() - mode_start) * 7
                root.setR(16 * math.sin(phase))
                root.setZ(.16 * abs(math.sin(phase)))
            if mode == 'hello':
                phase = (time.monotonic() - mode_start) * 18
                root.setR(5 * math.sin(phase / 2))
                root.setZ(.05 * abs(math.sin(phase / 2)))
            if mode == 'ouch' or (outgoing_mode == 'ouch' and blend < 1):
                pain_marks.show()
                pain_marks.setColorScale(1, 1, 1, blend if mode == 'ouch' else 1 - blend)
            else:
                pain_marks.hide()
            left_wing = root.find('**/Wing L')
            if not left_wing.isEmpty():
                left_wing.setR(-(30 + 25 * math.sin(t * 11)) if mode == 'lol' else -55 if mode == 'shrug' else 25 if mode in ('sad', 'cry') else 0)
            if mode == 'hello':
                wave = math.sin((time.monotonic() - mode_start) * 18)
                wing_base.setR(50 + 30 * wave)
                wing_tip.setR(30 * wave)
            else:
                wing_base.setR(30 + 25 * math.sin(t * 11) if mode == 'lol' else 55 if mode == 'shrug' else -25 if mode in ('sad', 'cry') else 0)
                wing_tip.setR(0)
            for index, name in enumerate(('Foot', 'Foot.001')):
                foot = root.find('**/' + name)
                if not foot.isEmpty():
                    if mode == 'ouch':
                        lift = max(0, math.sin((time.monotonic() - mode_start) * 7 + index * math.pi)) * .22
                    else:
                        lift = max(0, math.sin(t * 5 + index * math.pi)) * .08 if mode in ('quacking', 'lol') else 0
                    foot.setZ(.16 + lift)
            for eye in ('Eye white', 'Eye white.001', 'Pupil', 'Pupil.001'):
                node = root.find('**/' + eye)
                if not node.isEmpty():
                    node.setSz(1.3 if mode == 'shrug' else .12 if (t + 2) % 4.2 < .12 else .25 if mode == 'cry' else .42 if mode in ('sad', 'high') else 1)
                    if eye.startswith('Eye white'):
                        if mode == 'high':
                            node.setColorScale(1, .35, .35, 1)
                        else:
                            node.clearColorScale()
            for pupil, (x, z) in zip(pupils, pupil_origins):
                phase = (time.monotonic() - mode_start) * 5
                pupil.setX(x + .035 * math.sin(phase) if mode == 'rolleye' else x)
                pupil.setZ(z + .045 * math.cos(phase) if mode == 'rolleye' else z)
            if blend < 1:
                for (node, prop), start_value in zip(nodes, origin):
                    target_value = getattr(node, 'get' + prop)()
                    getattr(node, 'set' + prop)(start_value + (target_value - start_value) * blend)
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
